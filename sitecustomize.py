import logging
import re

try:
    import pymupdf
except Exception:  # pragma: no cover
    pymupdf = None

try:
    import pdf2zh.translator as t
except Exception:  # pragma: no cover
    t = None


def _patch_subset_fonts():
    if pymupdf is None:
        return
    doc_cls = pymupdf.Document
    if getattr(doc_cls.subset_fonts, "_hermes_patched", False):
        return
    original = doc_cls.subset_fonts

    def safe_subset_fonts(self, *args, **kwargs):
        try:
            return original(self, *args, **kwargs)
        except Exception as e:
            logging.warning(
                "subset_fonts failed; continuing without font subsetting: %s", e
            )
            return None

    safe_subset_fonts._hermes_patched = True
    doc_cls.subset_fonts = safe_subset_fonts


def _patch_translator_validation():
    if t is None:
        return
    if getattr(t, "_hermes_patched", False):
        return

    t.PLACEHOLDER_RE = re.compile(r"\{\s*v\s*(\d+)\s*\}", re.I)
    t.LOWERCASE_ENGLISH_RE = re.compile(r"\b[a-z][a-z-]{3,}\b")
    t.REFUSAL_MARKERS_ZH = (
        "很抱歉，我無法",
        "抱歉，我無法",
        "我無法翻譯此內容",
        "我無法提供",
        "我不能幫助",
        "無法協助",
    )

    def normalize_pdf_english_word_breaks(text: str) -> str:
        if not text:
            return ""
        normalized = text
        normalized = re.sub(
            r"\b([A-Za-z]{1,20})-\s*(?:\n|\s)+\s*([A-Za-z]{1,20})\b",
            r"\1\2",
            normalized,
        )
        normalized = re.sub(
            r"\b([A-Za-z]{1,2})\s*\n\s*([a-z]{1,20})\b",
            r"\1\2",
            normalized,
        )
        normalized = re.sub(
            r"\b([A-Za-z]{1,20})\s*\n\s*([a-z]{1,2})\b",
            r"\1\2",
            normalized,
        )
        return normalized

    def extract_placeholders(text: str) -> list[str]:
        return [f"{{v{match}}}" for match in t.PLACEHOLDER_RE.findall(text or "")]

    def has_dangling_placeholder(text: str) -> bool:
        text = text or ""
        masked = t.PLACEHOLDER_RE.sub("", text)
        return bool(re.search(r"\{\s*v", masked, re.I))

    def extract_allowed_source_english_words(source_text: str) -> set[str]:
        source_text = normalize_pdf_english_word_breaks(source_text or "")
        allowed = set(t.ALLOWED_ENGLISH_WORDS)
        allowed.update(word.lower() for word in t.LOWERCASE_ENGLISH_RE.findall(source_text))
        for email in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", source_text):
            allowed.update(word.lower() for word in t.LOWERCASE_ENGLISH_RE.findall(email))
        for url in re.findall(r"https?://\S+", source_text):
            allowed.update(word.lower() for word in t.LOWERCASE_ENGLISH_RE.findall(url))
        for citation in re.findall(r"\[[^\]]+\]", source_text):
            allowed.update(word.lower() for word in t.LOWERCASE_ENGLISH_RE.findall(citation))
        return allowed

    def find_suspicious_english_words(source_text: str, translated_text: str) -> list[str]:
        allowed_words = extract_allowed_source_english_words(source_text)
        translated_text = normalize_pdf_english_word_breaks(translated_text or "")
        return sorted(
            {
                word
                for word in t.LOWERCASE_ENGLISH_RE.findall(translated_text)
                if word.lower() not in allowed_words
            }
        )

    def validate_translation_output(source_text: str, translated_text: str):
        translated_text = (translated_text or "").strip()
        if not translated_text:
            return False, "empty_translation"

        lowered = translated_text.lower()
        for marker in t.LEAK_MARKERS:
            if marker.lower() in lowered:
                return False, f"leak_marker:{marker}"

        if "<think>" in lowered or "</think>" in lowered:
            return False, "think_leak"

        if has_dangling_placeholder(translated_text):
            return False, "dangling_placeholder"

        source_placeholders = extract_placeholders(source_text)
        translated_placeholders = extract_placeholders(translated_text)
        if source_placeholders != translated_placeholders:
            if source_placeholders and sorted(source_placeholders) == sorted(translated_placeholders):
                pass
            elif (
                source_placeholders
                and not translated_placeholders
                and re.search(
                    r"\b(?:In\s+)?[A-Z][A-Za-z]+(?:\s+(?:of|the|for|and|on|Annual|Meeting|Association|Computational|Linguistics|Long|Papers|ACL|Proceedings|Conference|Symposium|Workshop|Journal|Transactions|Preprint|arXiv|Online|Bangkok|Thailand))[A-Za-z\s-]*",
                    translated_text,
                )
            ):
                pass
            elif (
                len(source_placeholders) == 1
                and re.match(r"^(?:User|Assistant)\s*\{\s*v\s*\d+\s*\}", source_text)
                and any(marker in translated_text for marker in t.REFUSAL_MARKERS_ZH)
            ):
                pass
            else:
                return False, "placeholder_mismatch"

        suspicious_words = find_suspicious_english_words(source_text, translated_text)
        if suspicious_words and re.search(r"[\u3400-\u9fff]", translated_text):
            suspicious_text = normalize_pdf_english_word_breaks(translated_text)
            total_words = t.LOWERCASE_ENGLISH_RE.findall(suspicious_text)
            if len(suspicious_words) >= 3 or (
                len(suspicious_words) >= 2 and len(total_words) >= 8
            ):
                return False, f"suspicious_english:{','.join(suspicious_words[:8])}"

        return True, "ok"

    original_translate = t.BaseTranslator.translate

    def patched_translate(self, text, ignore_cache=False):
        if not (self.ignore_cache or ignore_cache):
            cache = self.cache.get(text)
            if cache is not None:
                cache = t.sanitize_llm_translation_output(cache)
                ok, _ = validate_translation_output(text, cache)
                if ok:
                    return cache

        last_reason = "unknown"
        for _ in range(3):
            translation = t.sanitize_llm_translation_output(self.do_translate(text))
            ok, reason = validate_translation_output(text, translation)
            if ok:
                self.cache.set(text, translation)
                return translation
            if reason in {"placeholder_mismatch", "dangling_placeholder"}:
                logging.warning(
                    "Validation failure detail reason=%s source_placeholders=%s translated_placeholders=%s source_snippet=%r translated_snippet=%r",
                    reason,
                    extract_placeholders(text),
                    extract_placeholders(translation),
                    (text or "")[:500],
                    (translation or "")[:500],
                )
            last_reason = reason

        fallback = t.build_fallback_translation(text, last_reason)
        if fallback:
            logging.warning(
                "Falling back to degraded translation output due to validation failure: %s",
                last_reason,
            )
            self.cache.set(text, fallback)
            return fallback

        logging.warning(
            "Falling back to source text due to validation failure with empty fallback: %s",
            last_reason,
        )
        fallback = (text or "").strip()
        self.cache.set(text, fallback)
        return fallback

    t.normalize_pdf_english_word_breaks = normalize_pdf_english_word_breaks
    t.extract_placeholders = extract_placeholders
    t.has_dangling_placeholder = has_dangling_placeholder
    t.extract_allowed_source_english_words = extract_allowed_source_english_words
    t.find_suspicious_english_words = find_suspicious_english_words
    t.validate_translation_output = validate_translation_output
    t.BaseTranslator.translate = patched_translate
    t._hermes_patched = True


_patch_subset_fonts()
_patch_translator_validation()
