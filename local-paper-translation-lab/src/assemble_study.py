from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from src.paper_paths import DEFAULT_SAMPLE_PAPER_ID, study_output_md_path, translated_blocks_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import DEFAULT_SAMPLE_PAPER_ID, study_output_md_path, translated_blocks_jsonl_path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
AFFILIATION_START_RE = re.compile(r"\b(?:\d+\.?\s*)?(?:CMU|SMU|University|Institute|Vector|MPI|AREA|Science Park)\b")

try:
    from src.translate import is_likely_truncated_translation, strip_repair_meta_text
except ModuleNotFoundError:  # pragma: no cover
    from translate import is_likely_truncated_translation, strip_repair_meta_text

DEFAULT_INPUT = Path("outputs/work/translated_blocks.gemini.jsonl")
DEFAULT_OUTPUT = study_output_md_path(DEFAULT_SAMPLE_PAPER_ID)

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
BAD_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*\s+[A-Z]?$|\d+(?:\.\d+)+\s+[A-Za-z0-9 .-]{0,20}$)")
ARTIFACT_RE = re.compile(r"\[TRANSLATION_ERROR:[^\]]+\]\s*")


def load_blocks(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]


def normalize_text(text: str) -> str:
    text = ARTIFACT_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_bad_heading(text: str) -> bool:
    t = normalize_text(text)
    if not t:
        return True
    if t.startswith("## References") or t in {"參考文獻", "摘要", "Abstract"}:
        return False
    if BAD_HEADING_RE.match(t):
        return True
    if len(t) < 2:
        return True
    return False


def choose_text(block):
    repaired = normalize_text(strip_repair_meta_text(str(block.get("repaired") or "")))
    translated = normalize_text(strip_repair_meta_text(str(block.get("translated") or "")))
    source = normalize_text(str(block.get("source") or ""))
    block_type = str(block.get("type") or "unknown")
    preferred = repaired or translated
    if block_type == "heading":
        return preferred if CJK_RE.search(preferred) else source
    if block_type in {"equation", "code"}:
        return source
    if CJK_RE.search(preferred):
        if is_likely_truncated_translation(source, preferred, block_type=block_type):
            source_sentences = len(re.findall(r"[.!?;:]", source))
            preferred_sentences = len(re.findall(r"[。！？；：.!?]", preferred))
            if len(preferred) < max(60, int(len(source) * 0.18)):
                return source
            if source_sentences >= 2 and preferred_sentences == 0:
                return source
        return preferred
    return source


def render(block):
    block_type = str(block.get("type") or "unknown")
    txt = choose_text(block)
    if not txt:
        return None
    if block_type == "unknown" and txt.strip() in {"*Equal contribution", "Equal contribution"}:
        return None
    if block_type == "heading":
        if is_bad_heading(txt):
            return None
        if txt in {"參考文獻", "References"}:
            return "## 參考文獻"
        if txt.startswith("### ") or txt.startswith("## ") or txt.startswith("# "):
            return txt
        section = str(block.get("section") or "")
        if section == "title":
            level = 1
        elif section in {"abstract", "references"}:
            level = 2
        else:
            level = 2 if section.count(".") == 0 else 3
        return f"{'#'*level} {txt}"
    if block_type == "figure":
        return f"> [Figure] {txt}"
    if block_type == "table":
        return f"> [Table] {txt}"
    if block_type == "reference":
        return f"- {txt}"
    return txt


def _parse_title_paragraph(source: str, translated: str):
    source = normalize_text(source)
    translated = normalize_text(translated)

    email_source = translated or source
    emails = EMAIL_RE.findall(email_source)

    if translated and "\n" in translated:
        lines = [line.strip(" ,") for line in translated.splitlines() if line.strip(" ,")]
        author_text = ""
        affiliations = []
        tail_emails = []
        saw_numbered_affiliation = False
        for line in lines:
            if EMAIL_RE.search(line):
                tail_emails.extend(EMAIL_RE.findall(line))
                continue
            if re.match(r"^\d+(?:\.)?\s+", line):
                affiliations.append(line)
                saw_numbered_affiliation = True
                continue
            if not author_text:
                author_text = line
            elif saw_numbered_affiliation:
                affiliations.append(line)
        if saw_numbered_affiliation:
            emails = tail_emails or emails
            authors = [author_text] if author_text else ([] if not translated else [translated])
            return authors, affiliations, emails

    source_wo_emails = EMAIL_RE.sub("", source).strip()
    affiliation_match = AFFILIATION_START_RE.search(source_wo_emails)
    if affiliation_match:
        split_at = affiliation_match.start()
        author_text = source_wo_emails[:split_at].strip(" ,")
        affiliation_text = source_wo_emails[split_at:].strip(" ,")
    else:
        author_text = source_wo_emails.strip()
        affiliation_text = ""

    affiliations = []
    if affiliation_text:
        numbered = re.findall(r"\d+(?:\.)?\s+.*?(?=(?:\s+\d+(?:\.)?\s+)|$)", affiliation_text)
        if numbered:
            affiliations = [line.strip(" ,") for line in numbered if line.strip(" ,")]
        else:
            affiliation_text = re.sub(r"\s+(?=(?:CMU|SMU|University|MPI|AREA)\b)", "\n", affiliation_text)
            affiliations = [line.strip(" ,") for line in affiliation_text.splitlines() if line.strip(" ,")]

    authors = [author_text] if author_text else []
    if not authors and translated:
        authors = [translated]
    return authors, affiliations, emails


def _render_front_matter(blocks):
    title = None
    authors = []
    affiliations = []
    emails = []
    body_start = 0

    for idx, block in enumerate(blocks):
        section = str(block.get("section") or "")
        if section != "title":
            body_start = idx
            break
        source = str(block.get("source") or "")
        text = choose_text(block)
        if not text:
            continue
        if str(block.get("type") or "") == "heading":
            title = text
            continue
        parsed_authors, parsed_affiliations, parsed_emails = _parse_title_paragraph(source, text)
        if parsed_authors:
            authors.extend(parsed_authors)
        if parsed_affiliations:
            affiliations.extend(parsed_affiliations)
        if parsed_emails:
            emails.extend(parsed_emails)
    else:
        body_start = len(blocks)

    rendered = []
    if title:
        rendered.append(f"# {title}")
    if authors:
        rendered.append("Authors: " + " ".join(authors))
    if affiliations:
        dedup_affiliations = []
        for line in affiliations:
            if line not in dedup_affiliations:
                dedup_affiliations.append(line)
        rendered.append("Affiliations:\n" + "\n".join(f"- {line}" for line in dedup_affiliations))
    if emails:
        dedup_emails = []
        for email in emails:
            if email not in dedup_emails:
                dedup_emails.append(email)
        rendered.append("Emails: " + " ".join(dedup_emails))
    return rendered, body_start


def build_study_version(blocks):
    rendered, start_index = _render_front_matter(blocks)
    for block in blocks[start_index:]:
        text = render(block)
        if not text:
            continue
        if text == "## 參考文獻":
            break
        rendered.append(text)
    doc = "\n\n".join(rendered).strip() + "\n"
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    args = parser.parse_args()
    input_path = args.input
    output_path = args.output
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if input_path == DEFAULT_INPUT:
            input_path = translated_blocks_jsonl_path(args.paper_id, outputs_dir)
        if output_path == DEFAULT_OUTPUT:
            output_path = study_output_md_path(args.paper_id, outputs_dir)
    blocks = load_blocks(input_path)
    doc = build_study_version(blocks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
