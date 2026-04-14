from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

try:
    from src.paper_paths import DEFAULT_SAMPLE_PAPER_ID, archival_output_md_path, translated_blocks_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import DEFAULT_SAMPLE_PAPER_ID, archival_output_md_path, translated_blocks_jsonl_path

DEFAULT_INPUT_CANDIDATES = (
    Path("outputs/work/translated_blocks.jsonl"),
    Path("outputs/work/translated_blocks.qwen.jsonl"),
)
DEFAULT_OUTPUT = archival_output_md_path(DEFAULT_SAMPLE_PAPER_ID)

ARTIFACT_MARKERS = (
    "Translate the following academic paper passage",
    "Translate each academic paper block",
    "Rules:",
    "Passage:",
    "<BLOCK ",
    "[TRANSLATION_ERROR:",
)

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
SECTION_NUMBER_RE = re.compile(r"^(?P<prefix>(?:\d+(?:\.\d+)*|[A-Z]))\s+(?P<title>.+)$")
APPENDIX_RE = re.compile(r"^Appendix\s+([A-Z])(?::\s*(.+))?$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"[ \t]+")
BLANKS_RE = re.compile(r"\n{3,}")

KNOWN_TRANSLATIONS = {
    "Are LLMs Good Safety Agents or a Propaganda Engine?": "LLM 是優秀的安全代理，還是宣傳引擎？",
    "Abstract": "摘要",
    "References": "參考文獻",
    "Appendix": "附錄",
    "Introduction": "導論",
    "Problem De nition": "問題定義",
    "Problem Definition": "問題定義",
    "Refusals": "拒答",
    "Refusal versus Censorship": "拒答與審查",
    "Related Work": "相關工作",
    "Existing, Scope-Limited Data Sources": "既有且範圍受限的資料來源",
    "Our Data Construction Method": "我們的資料建構方法",
    "Data Statistics of PSP": "PSP 的資料統計",
    "Data-driven approach": "資料驅動方法",
    "Representation-level approach": "表徵層級方法",
    "Prompt Injection Attacks": "提示注入攻擊",
    "Experimental Setup": "實驗設定",
    "Discussion": "討論",
    "RQ1: Impact of de-politicization": "RQ1：去政治化的影響",
    "RQ2: Prompt injection attacks and partial refusals": "RQ2：提示注入攻擊與部分拒答",
    "Conclusion": "結論",
}


class AssemblyError(RuntimeError):
    pass


def resolve_input_path(explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        if explicit_path.exists():
            return explicit_path
        raise AssemblyError(f"Input file not found: {explicit_path}")

    for candidate in DEFAULT_INPUT_CANDIDATES:
        if candidate.exists():
            return candidate
    joined = ", ".join(str(path) for path in DEFAULT_INPUT_CANDIDATES)
    raise AssemblyError(f"No translated block file found. Checked: {joined}")


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
                raise AssemblyError(f"Invalid JSON on line {line_no} of {input_path}") from exc
            if not {"block_id", "type", "source"} <= set(block):
                raise AssemblyError(f"Missing required block keys on line {line_no} of {input_path}")
            blocks.append(block)
    if not blocks:
        raise AssemblyError(f"No blocks found in {input_path}")
    return blocks


def contains_chinese(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = WHITESPACE_RE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = BLANKS_RE.sub("\n\n", text)
    return text.strip()


def has_duplicate_lines(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    unique = set(lines)
    return len(unique) <= max(1, len(lines) // 2)


def looks_suspicious_translation(source: str, translated: str, block_type: str) -> bool:
    clean_translated = normalize_text(translated)
    clean_source = normalize_text(source)
    if not clean_translated:
        return True
    if any(marker in clean_translated for marker in ARTIFACT_MARKERS):
        return True
    if has_duplicate_lines(clean_translated):
        return True
    if len(clean_translated) > max(len(clean_source) * 4, 1200):
        return True
    if clean_translated.count("§PROTECTED_") >= 2:
        return True
    if block_type == "heading" and clean_source in KNOWN_TRANSLATIONS and not contains_chinese(clean_translated):
        return True
    return False


def translate_heading_text(source: str, translated: str) -> str:
    clean_source = normalize_text(source)
    clean_translated = normalize_text(translated)

    if clean_source in KNOWN_TRANSLATIONS:
        return KNOWN_TRANSLATIONS[clean_source]

    appendix_match = APPENDIX_RE.match(clean_source)
    if appendix_match:
        letter = appendix_match.group(1)
        rest = appendix_match.group(2) or ""
        rest_zh = KNOWN_TRANSLATIONS.get(rest.strip(), rest.strip()) if rest.strip() else ""
        return f"附錄 {letter}" + (f"：{rest_zh}" if rest_zh else "")

    numbered = SECTION_NUMBER_RE.match(clean_source)
    if numbered:
        prefix = numbered.group("prefix")
        tail = numbered.group("title").strip()
        tail_zh = KNOWN_TRANSLATIONS.get(tail)
        if tail_zh:
            separator = " " if prefix[0].isdigit() else ""
            return f"{prefix}{separator}{tail_zh}"

    if contains_chinese(clean_translated) and not looks_suspicious_translation(clean_source, clean_translated, "heading"):
        first_line = clean_translated.splitlines()[0].strip()
        if first_line:
            return first_line

    return clean_source


def choose_block_text(block: dict[str, object]) -> str:
    source = normalize_text(str(block.get("source", "")))
    repaired = normalize_text(str(block.get("repaired") or ""))
    translated = normalize_text(str(block.get("translated") or ""))
    preferred_translation = repaired or translated
    block_type = str(block.get("type", "unknown"))

    if block_type == "heading":
        return translate_heading_text(source, preferred_translation)

    if block_type in {"equation", "code", "reference", "figure", "table", "unknown"}:
        preferred = preferred_translation if preferred_translation and not looks_suspicious_translation(source, preferred_translation, block_type) else source
        return preferred or source

    if preferred_translation and not looks_suspicious_translation(source, preferred_translation, block_type):
        return preferred_translation
    return source


def heading_level(section: str) -> int:
    if section == "title":
        return 1
    if section in {"abstract", "references"}:
        return 2
    if not section:
        return 2
    if section[0].isdigit():
        return min(2 + section.count("."), 6)
    return 2


def render_equation(text: str) -> str:
    content = normalize_text(text)
    if "\n" in content:
        return f"$$\n{content}\n$$"
    return f"$$\n{content}\n$$"


def render_block(block: dict[str, object]) -> str:
    block_type = str(block.get("type", "unknown"))
    section = str(block.get("section", ""))
    text = choose_block_text(block)

    if block_type == "heading":
        level = heading_level(section)
        return f"{'#' * level} {text}"
    if block_type == "equation":
        return render_equation(text)
    if block_type == "code":
        return f"```\n{text}\n```"
    if block_type == "figure":
        return f"> [Figure] {text}"
    if block_type == "table":
        return f"> [Table] {text}"
    if block_type == "reference":
        return f"- {text}"
    return text


def assemble_blocks(blocks: Iterable[dict[str, object]]) -> str:
    rendered: list[str] = []
    for block in blocks:
        chunk = render_block(block).strip()
        if chunk:
            rendered.append(chunk)
    document = "\n\n".join(rendered).strip() + "\n"
    if not document.strip():
        raise AssemblyError("Assembled markdown is empty")
    return document


def write_markdown(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def run(input_path: Path | None = None, output_path: Path = DEFAULT_OUTPUT) -> Path:
    resolved_input = resolve_input_path(input_path)
    blocks = load_blocks(resolved_input)
    markdown = assemble_blocks(blocks)
    return write_markdown(markdown, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble translated paper blocks into final Markdown")
    parser.add_argument("--input", type=Path, default=None, help="Path to translated blocks JSONL")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to output markdown")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resolved_input = args.input
    resolved_output = args.output
    outputs_dir = Path(args.outputs_dir)
    if args.paper_id:
        if resolved_input is None:
            resolved_input = translated_blocks_jsonl_path(args.paper_id, outputs_dir)
        if resolved_output == DEFAULT_OUTPUT:
            resolved_output = archival_output_md_path(args.paper_id, outputs_dir)
    result = run(resolved_input, resolved_output)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
