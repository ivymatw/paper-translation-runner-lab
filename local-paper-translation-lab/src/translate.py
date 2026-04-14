from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterable

MAX_SINGLE_BLOCK_CHARS = 180
MAX_COMPLETION_TOKENS = 384
MAX_RETRIES = 3
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?。！？])\s+')
import time
from urllib import error, request

try:
    from src.paper_paths import glossary_json_path, segmented_blocks_jsonl_path, translated_blocks_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import glossary_json_path, segmented_blocks_jsonl_path, translated_blocks_jsonl_path

DEFAULT_INPUT = Path("outputs/work/blocks.jsonl")
DEFAULT_OUTPUT = Path("outputs/work/translated_blocks.jsonl")
DEFAULT_MODEL = os.environ.get("TRANSLATION_MODEL", "gemini-2.5-flash")
DEFAULT_ENDPOINT = os.environ.get("TRANSLATION_ENDPOINT", os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/generate"))
DEFAULT_TIMEOUT = int(os.environ.get("TRANSLATION_TIMEOUT", os.environ.get("OLLAMA_TIMEOUT", "180")))
DEFAULT_BACKEND = os.environ.get("TRANSLATION_BACKEND", "auto")
DEFAULT_BATCH_SIZE = 8
DEFAULT_CHAR_BUDGET = 5000
DEFAULT_GLOSSARY = Path("outputs/work/glossary.json")

TRANSLATABLE_TYPES = {"heading", "paragraph"}
PROTECTED_TYPES = {"figure", "table", "equation", "code", "reference", "unknown"}
CODE_SPAN_RE = re.compile(r"`[^`]+`")
URL_RE = re.compile(r"https?://\S+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
INLINE_MATH_RE = re.compile(r"\$[^$]+\$")
IDENTIFIER_RE = re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9._-]*|[A-Za-z]+(?:[-_/][A-Za-z0-9.]+)+|[A-Za-z]*\d+[A-Za-z0-9._-]*)\b")
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)
BLOCK_RESPONSE_RE = re.compile(r"<BLOCK\s+([^>]+)>\s*(.*?)\s*</BLOCK\s+\1>", re.S)
TRAILING_INCOMPLETE_RE = re.compile(r"[\(\[\{（［｛]$|\b(?:et|al|vs|Fig|Eq|Sec|Table)\.?$", re.IGNORECASE)


class TranslationError(RuntimeError):
    pass


class TranslationClient:
    supports_multi_chunk_batch = False

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        raise NotImplementedError

    def translate_single(
        self,
        text: str,
        *,
        block_type: str = "paragraph",
        section: str = "",
        chunk_index: int = 0,
        chunk_total: int = 1,
        glossary_entries: list[dict[str, object]] | None = None,
    ) -> str:
        result = self.translate_batch({"single": text})
        return str(result.get("single", "")).strip()


class OllamaTranslationClient(TranslationClient):
    supports_multi_chunk_batch = True
    def __init__(self, model: str = DEFAULT_MODEL, endpoint: str = DEFAULT_ENDPOINT, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        prompt = build_batch_prompt(items)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": MAX_COMPLETION_TOKENS,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(self.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            raise TranslationError(f"Unable to reach local translation model at {self.endpoint}: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranslationError(f"Model endpoint returned non-JSON response: {raw[:400]}") from exc

        text = str(parsed.get("response", "")).strip()
        result = parse_block_mapping(text)
        missing = [block_id for block_id in items if block_id not in result]
        if missing:
            raise TranslationError(f"Model response missing translations for block ids: {', '.join(missing)}")
        return {block_id: str(result[block_id]).strip() for block_id in items}


class OpenAICompatibleTranslationClient(TranslationClient):
    supports_multi_chunk_batch = False
    def __init__(self, model: str = DEFAULT_MODEL, endpoint: str = DEFAULT_ENDPOINT, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def _complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(f"{self.endpoint}/v1/completions", data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            raise TranslationError(f"Unable to reach local translation model at {self.endpoint}: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranslationError(f"Model endpoint returned non-JSON response: {raw[:400]}") from exc

        choices = parsed.get("choices") or []
        if not choices:
            raise TranslationError(f"OpenAI-compatible endpoint returned no choices: {raw[:400]}")
        return str((choices[0] or {}).get("text", "")).strip()

    def translate_single(
        self,
        text: str,
        *,
        block_type: str = "paragraph",
        section: str = "",
        chunk_index: int = 0,
        chunk_total: int = 1,
        glossary_entries: list[dict[str, object]] | None = None,
    ) -> str:
        translated = self._complete(
            build_single_prompt(
                text,
                block_type=block_type,
                section=section,
                chunk_index=chunk_index,
                chunk_total=chunk_total,
                glossary_entries=glossary_entries,
            )
        ).strip()
        if not translated:
            raise TranslationError("Empty translation for single block")
        return translated

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        if len(items) == 1:
            block_id, text = next(iter(items.items()))
            return {block_id: self.translate_single(text)}

        text = self._complete(build_batch_prompt(items)).strip()
        result = parse_block_mapping(text)
        missing = [block_id for block_id in items if block_id not in result]
        if missing:
            raise TranslationError(f"Model response missing translations for block ids: {', '.join(missing)}")
        return {block_id: str(result[block_id]).strip() for block_id in items}

class GeminiTranslationClient(TranslationClient):
    supports_multi_chunk_batch = False
    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT, api_key: str | None = None) -> None:
        self.model = model
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise TranslationError("Missing GEMINI_API_KEY for Gemini translation backend")

    def _complete(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 4096,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = ''
            try:
                detail = exc.read().decode('utf-8', errors='ignore')[:400]
            except Exception:
                pass
            raise TranslationError(f"Gemini HTTP error: {exc.code} {exc.reason} {detail}") from exc
        except error.URLError as exc:
            raise TranslationError(f"Unable to reach Gemini API: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranslationError(f"Gemini returned non-JSON response: {raw[:400]}") from exc

        candidates = parsed.get("candidates") or []
        if not candidates:
            raise TranslationError(f"Gemini returned no candidates: {raw[:400]}")
        parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
        if not parts:
            raise TranslationError(f"Gemini returned no content parts: {raw[:400]}")
        return str(parts[0].get("text", "")).strip()

    def translate_single(
        self,
        text: str,
        *,
        block_type: str = "paragraph",
        section: str = "",
        chunk_index: int = 0,
        chunk_total: int = 1,
        glossary_entries: list[dict[str, object]] | None = None,
    ) -> str:
        translated = self._complete(
            build_single_prompt(
                text,
                block_type=block_type,
                section=section,
                chunk_index=chunk_index,
                chunk_total=chunk_total,
                glossary_entries=glossary_entries,
            )
        ).strip()
        if not translated:
            raise TranslationError("Empty translation for single block")
        return translated

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        if len(items) == 1:
            block_id, text = next(iter(items.items()))
            return {block_id: self.translate_single(text)}

        text = self._complete(build_batch_prompt(items)).strip()
        result = parse_block_mapping(text)
        missing = [block_id for block_id in items if block_id not in result]
        if missing:
            raise TranslationError(f"Model response missing translations for block ids: {', '.join(missing)}")
        return {block_id: str(result[block_id]).strip() for block_id in items}


def build_batch_prompt(items: dict[str, str]) -> str:
    blocks = "\n\n".join(
        f"<BLOCK {block_id}>\n{text}\n</BLOCK {block_id}>"
        for block_id, text in items.items()
    )
    return (
        "Translate each academic paper block into Traditional Chinese used in Taiwan.\n"
        "Rules:\n"
        "1. Translate fully. Do not summarize or omit content.\n"
        "2. Preserve placeholders like §PROTECTED_0§ exactly.\n"
        "3. Preserve author names, institution names when official translation is uncertain, emails, URLs, model names, dataset names, benchmark names, equations, and technical identifiers.\n"
        "4. Keep the same block ids and the same <BLOCK ...> markers.\n"
        "5. Return only the translated blocks with the same markers. Do not use markdown fences.\n"
        "Input blocks:\n"
        f"{blocks}"
    )


REPAIR_META_PREFIX_RE = re.compile(r"^(?:以下是(?:修復後的)?(?:繁體中文)?翻譯：?|Here(?: is|\'s) the (?:repaired )?(?:Traditional Chinese )?translation:?)[\s\n]*", re.IGNORECASE)


def strip_repair_meta_text(text: str) -> str:
    cleaned = text.strip()
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = REPAIR_META_PREFIX_RE.sub("", cleaned).strip()
    return cleaned


def format_glossary_guidance(glossary_entries: list[dict[str, object]] | None) -> str:
    if not glossary_entries:
        return ""
    lines = ["Glossary guidance:"]
    for entry in glossary_entries:
        term = str(entry.get("term") or "").strip()
        policy = str(entry.get("policy") or "").strip()
        translation = str(entry.get("translation_zh_tw") or "").strip()
        if not term or not policy:
            continue
        if policy == "preserve":
            lines.append(f"- {term} => preserve English")
        elif translation:
            lines.append(f"- {term} => {translation}")
        else:
            lines.append(f"- {term} => prefer consistent translation")
    return "\n".join(lines) + "\n"


def build_single_prompt(
    text: str,
    *,
    block_type: str = "paragraph",
    section: str = "",
    chunk_index: int = 0,
    chunk_total: int = 1,
    glossary_entries: list[dict[str, object]] | None = None,
) -> str:
    if block_type == "heading":
        style_hint = "Translate as a concise academic heading in zh-TW. Preserve numbering."
    elif block_type in {"figure_caption", "table_caption", "figure", "table"}:
        style_hint = "Translate as a compact caption. Preserve figure/table numbering and identifiers."
    elif block_type in {"title", "metadata"}:
        style_hint = "Translate minimally. Preserve names, affiliations when uncertain, emails, and identifiers."
    else:
        style_hint = "Translate as fluent but faithful zh-TW academic prose. Preserve terminology and citations."

    chunk_hint = "This passage is complete."
    if chunk_total > 1:
        chunk_hint = (
            f"This is chunk {chunk_index + 1} of {chunk_total} from one original block. "
            "Translate faithfully and keep continuity with adjacent chunks. Do not add a new section break."
        )

    glossary_guidance = format_glossary_guidance(glossary_entries)

    return (
        "Translate the following academic paper passage into Traditional Chinese used in Taiwan.\n"
        f"Block type: {block_type}\n"
        f"Section: {section or 'unknown'}\n"
        f"Chunk note: {chunk_hint}\n"
        f"Style note: {style_hint}\n"
        f"{glossary_guidance}"
        "Rules:\n"
        "1. Translate fully. Do not summarize or omit content.\n"
        "2. Preserve placeholders like §PROTECTED_0§ exactly.\n"
        "3. Preserve author names, institution names when official translation is uncertain, emails, URLs, model names, dataset names, benchmark names, equations, and technical identifiers.\n"
        "4. Return only the translation itself. Do not add explanations, labels, or markdown fences.\n"
        "Passage:\n"
        f"{text}"
    )


def parse_block_mapping(text: str) -> dict[str, str]:
    cleaned = FENCE_RE.sub("", text.strip()).strip()
    matches = BLOCK_RESPONSE_RE.findall(cleaned)
    if not matches:
        raise TranslationError(f"Could not parse model block response: {text[:400]}")
    return {block_id.strip(): content.strip() for block_id, content in matches}


def protect_text(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    counter = 0
    combined_pattern = re.compile(
        "|".join(
            pattern.pattern
            for pattern in (CODE_SPAN_RE, URL_RE, EMAIL_RE, INLINE_MATH_RE)
        )
    )

    def replace_match(match: re.Match[str]) -> str:
        nonlocal counter
        value = match.group(0)
        placeholder = f"§PROTECTED_{counter}§"
        counter += 1
        replacements[placeholder] = value
        return placeholder

    protected = combined_pattern.sub(replace_match, text)
    return protected, replacements


def restore_text(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for placeholder, value in replacements.items():
        restored = restored.replace(placeholder, value)
    return restored


def load_blocks(input_path: Path) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                block = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TranslationError(f"Invalid JSON on line {line_no} of {input_path}") from exc
            if not {"block_id", "type", "source"} <= set(block):
                raise TranslationError(f"Missing required block keys on line {line_no} of {input_path}")
            blocks.append(block)
    if not blocks:
        raise TranslationError(f"No blocks found in {input_path}")
    return blocks


def write_blocks(blocks: Iterable[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block, ensure_ascii=False) + "\n")
    return output_path


def load_glossary(glossary_path: Path | None) -> list[dict[str, object]]:
    if glossary_path is None or not glossary_path.exists():
        return []
    try:
        parsed = json.loads(glossary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TranslationError(f"Invalid glossary JSON: {glossary_path}") from exc
    entries = parsed.get("entries") if isinstance(parsed, dict) else None
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def glossary_subset(glossary_entries: list[dict[str, object]], *, text: str, section: str, limit: int = 8) -> list[dict[str, object]]:
    if not glossary_entries:
        return []
    haystack = f"{section}\n{text}".lower()
    matched: list[dict[str, object]] = []
    for entry in glossary_entries:
        term = str(entry.get("term") or "").strip()
        if term and term.lower() in haystack:
            matched.append(entry)
        if len(matched) >= limit:
            break
    return matched


def split_text_for_translation(text: str, max_chars: int = MAX_SINGLE_BLOCK_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts = SENTENCE_SPLIT_RE.split(text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if not current:
            current = part
        elif len(current) + 1 + len(part) <= max_chars:
            current = current + " " + part
        else:
            chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    if not chunks:
        return [text]
    normalized: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            normalized.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            normalized.append(chunk[start:start + max_chars])
            start += max_chars
    return normalized


def join_translated_parts(parts: list[str], *, block_type: str = "paragraph") -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return ""
    if block_type == "paragraph":
        return " ".join(cleaned)
    return "\n\n".join(cleaned)


def is_likely_truncated_translation(source: str, translated: str, *, block_type: str = "paragraph") -> bool:
    source = str(source or "").strip()
    translated = strip_repair_meta_text(str(translated or "")).strip()
    if block_type not in TRANSLATABLE_TYPES:
        return False
    if not translated:
        return True
    if block_type == "heading":
        return False
    if len(source) < 120:
        return False
    if TRAILING_INCOMPLETE_RE.search(translated):
        return True
    source_sentences = len(re.findall(r"[.!?;:]", source))
    translated_sentences = len(re.findall(r"[。！？；：.!?]", translated))
    if len(source) >= 240 and len(translated) < max(80, int(len(source) * 0.22)):
        return True
    if source_sentences >= 2 and translated_sentences == 0 and len(translated) < 120:
        return True
    if len(source) >= 400 and len(translated) < 120:
        return True
    return False


def translate_blocks(
    blocks: list[dict[str, object]],
    client: TranslationClient,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    char_budget: int = DEFAULT_CHAR_BUDGET,
    glossary_entries: list[dict[str, object]] | None = None,
    on_batch_complete: callable | None = None,
) -> list[dict[str, object]]:
    translated_blocks = [dict(block) for block in blocks]
    pending: list[dict[str, object]] = []

    def flush_batch() -> None:
        if not pending:
            return
        masked_items: dict[str, str] = {}
        replacement_maps: dict[str, dict[str, str]] = {}
        chunk_plans: dict[str, list[str]] = {}
        for block in pending:
            block_id = str(block["block_id"])
            masked, replacements = protect_text(str(block["source"]))
            replacement_maps[block_id] = replacements
            chunks = split_text_for_translation(masked)
            chunk_ids: list[str] = []
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{block_id}__c{idx:03d}"
                masked_items[chunk_id] = chunk
                chunk_ids.append(chunk_id)
            chunk_plans[block_id] = chunk_ids

        translated_map: dict[str, str] = {}
        if getattr(client, 'supports_multi_chunk_batch', False):
            pending_items = dict(masked_items)
            while pending_items:
                batch_result: dict[str, str] | None = None
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        batch_result = client.translate_batch(pending_items)
                        break
                    except Exception as exc:
                        last_error = exc
                        time.sleep(5 * (attempt + 1))
                if batch_result is None:
                    if len(pending_items) == 1:
                        chunk_id, chunk_text = next(iter(pending_items.items()))
                        translated_map[chunk_id] = f"[TRANSLATION_ERROR:{chunk_id}]\n{chunk_text}"
                        pending_items = {}
                    else:
                        items_list = list(pending_items.items())
                        mid = max(1, len(items_list)//2)
                        left = dict(items_list[:mid])
                        right = dict(items_list[mid:])
                        pending_items = left
                        # stash right to process after left
                        for k,v in right.items():
                            masked_items[k] = v
                        continue
                else:
                    translated_map.update({k:str(v).strip() for k,v in batch_result.items()})
                    for k in list(pending_items.keys()):
                        masked_items.pop(k, None)
                    if masked_items:
                        pending_items = dict(masked_items)
                    else:
                        pending_items = {}
        else:
            for block in pending:
                block_id = str(block["block_id"])
                chunk_ids = chunk_plans[block_id]
                block_type = str(block.get("type") or "paragraph")
                section = str(block.get("section") or "")
                local_glossary = glossary_subset(glossary_entries or [], text=str(block.get("source") or ""), section=section)
                for idx, chunk_id in enumerate(chunk_ids):
                    chunk_text = masked_items[chunk_id]
                    for attempt in range(MAX_RETRIES):
                        try:
                            if hasattr(client, "translate_single"):
                                translated = client.translate_single(
                                    chunk_text,
                                    block_type=block_type,
                                    section=section,
                                    chunk_index=idx,
                                    chunk_total=len(chunk_ids),
                                    glossary_entries=local_glossary,
                                )
                            else:
                                single_result = client.translate_batch({chunk_id: chunk_text})
                                translated = single_result.get(chunk_id, "")
                            translated_map[chunk_id] = str(translated).strip()
                            break
                        except Exception:
                            time.sleep(2 * (attempt + 1))
                    else:
                        translated_map[chunk_id] = f"[TRANSLATION_ERROR:{chunk_id}]\n{chunk_text}"
        for block in pending:
            block_id = str(block["block_id"])
            chunk_ids = chunk_plans[block_id]
            translated_parts: list[str] = []
            for chunk_id in chunk_ids:
                translated_text = translated_map.get(chunk_id, "").strip()
                if not translated_text:
                    translated_text = f"[TRANSLATION_ERROR:{chunk_id}]\n{masked_items.get(chunk_id, '')}"
                translated_parts.append(translated_text)
            block_type = str(block.get("type") or "paragraph")
            block["translated"] = restore_text(join_translated_parts(translated_parts, block_type=block_type), replacement_maps[block_id])
        pending.clear()
        if on_batch_complete is not None:
            on_batch_complete(translated_blocks)

    current_chars = 0
    for block in translated_blocks:
        block_type = str(block.get("type"))
        source_text = str(block.get("source", ""))
        if block_type in PROTECTED_TYPES or block_type not in TRANSLATABLE_TYPES:
            block["translated"] = source_text
            continue
        if str(block.get("translated") or "").strip():
            continue

        projected_chars = current_chars + len(source_text)
        if pending and (len(pending) >= batch_size or projected_chars > char_budget):
            flush_batch()
            current_chars = 0

        pending.append(block)
        current_chars += len(source_text)

    flush_batch()

    if len(translated_blocks) != len(blocks):
        raise TranslationError("Translated block count does not match input block count")
    return translated_blocks


def run(
    input_path: Path,
    output_path: Path,
    *,
    client: TranslationClient | None = None,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    char_budget: int = DEFAULT_CHAR_BUDGET,
    backend: str = DEFAULT_BACKEND,
    glossary_path: Path | None = DEFAULT_GLOSSARY,
) -> Path:
    blocks = load_blocks(input_path)
    if output_path.exists():
        existing_blocks = load_blocks(output_path)
        if len(existing_blocks) != len(blocks):
            raise TranslationError("Existing translated block file does not match input block count")
        merged_blocks: list[dict[str, object]] = []
        for source_block, existing_block in zip(blocks, existing_blocks):
            if source_block["block_id"] != existing_block.get("block_id"):
                raise TranslationError("Existing translated block file does not match input block ids")
            merged = dict(source_block)
            existing_translation = existing_block.get("translated")
            if is_likely_truncated_translation(
                str(source_block.get("source") or ""),
                str(existing_translation or ""),
                block_type=str(source_block.get("type") or "paragraph"),
            ):
                existing_translation = None
            merged["translated"] = existing_translation
            merged_blocks.append(merged)
        blocks = merged_blocks
    if client is not None:
        translator = client
    elif backend == 'gemini' or model.startswith('gemini-'):
        translator = GeminiTranslationClient(model=model, timeout=timeout)
    elif backend == 'ollama' or endpoint.rstrip("/").endswith("/api/generate"):
        translator = OllamaTranslationClient(model=model, endpoint=endpoint, timeout=timeout)
    else:
        translator = OpenAICompatibleTranslationClient(model=model, endpoint=endpoint, timeout=timeout)
    glossary_entries = load_glossary(glossary_path)
    translated_blocks = translate_blocks(
        blocks,
        translator,
        batch_size=batch_size,
        char_budget=char_budget,
        glossary_entries=glossary_entries,
        on_batch_complete=lambda current_blocks: write_blocks(current_blocks, output_path),
    )
    return write_blocks(translated_blocks, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate heading and paragraph blocks into Traditional Chinese.")
    parser.add_argument("input_jsonl", nargs="?", default=str(DEFAULT_INPUT), help="Path to segmented blocks JSONL")
    parser.add_argument("output_jsonl", nargs="?", default=str(DEFAULT_OUTPUT), help="Path to translated blocks JSONL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Translation model name / alias")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Translation endpoint: Ollama /api/generate or OpenAI-compatible base URL")
    parser.add_argument("--backend", default=DEFAULT_BACKEND, choices=['auto','gemini','ollama','openai'], help="Translation backend selector")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Maximum translated blocks per request")
    parser.add_argument("--char-budget", type=int, default=DEFAULT_CHAR_BUDGET, help="Maximum source characters per request")
    parser.add_argument("--glossary", default=str(DEFAULT_GLOSSARY), help="Optional glossary JSON path")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    input_path = Path(args.input_jsonl)
    output_path_arg = Path(args.output_jsonl)
    glossary_path = Path(args.glossary) if args.glossary else None
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_jsonl == str(DEFAULT_INPUT):
            input_path = segmented_blocks_jsonl_path(args.paper_id, outputs_dir)
        if args.output_jsonl == str(DEFAULT_OUTPUT):
            output_path_arg = translated_blocks_jsonl_path(args.paper_id, outputs_dir)
        if args.glossary == str(DEFAULT_GLOSSARY):
            glossary_path = glossary_json_path(args.paper_id, outputs_dir)
    output_path = run(
        input_path,
        output_path_arg,
        model=args.model,
        endpoint=args.endpoint,
        timeout=args.timeout,
        batch_size=args.batch_size,
        char_budget=args.char_budget,
        backend=args.backend,
        glossary_path=glossary_path,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
