from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

try:
    from src.paper_paths import clean_md_path, segmented_blocks_jsonl_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import clean_md_path, segmented_blocks_jsonl_path

DEFAULT_INPUT = Path("outputs/work/source_clean.md")
DEFAULT_OUTPUT = Path("outputs/work/blocks.clean.jsonl")

EXTRACTED_CONTENT_MARKER = "## Extracted Content"
TITLE_LINE = "# Source Extracted Text"
SOURCE_PREFIX = "Source PDF:"
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\s+\S")
APPENDIX_HEADING_RE = re.compile(r"^[A-Z]\s+[A-Z][A-Za-z0-9].+")
FIGURE_RE = re.compile(r"^Figure\s+\d+:")
TABLE_RE = re.compile(r"^Table\s+\d+:")
REFERENCE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
SECTION_ID_RE = re.compile(r"^(\d+(?:\.\d+)*)\b")
APPENDIX_ID_RE = re.compile(r"^([A-Z])\b")
EQUATION_SYMBOL_RE = re.compile(r"[=+×*/^_<>≤≥∈∑∏λµβγδθ]|\$.*\$")


class SegmentationError(RuntimeError):
    pass


class LineStream:
    def __init__(self, lines: list[str]):
        self.lines = lines
        self.index = 0

    def has_next(self) -> bool:
        return self.index < len(self.lines)

    def peek(self, offset: int = 0) -> str | None:
        pos = self.index + offset
        if 0 <= pos < len(self.lines):
            return self.lines[pos]
        return None

    def take(self) -> str:
        line = self.lines[self.index]
        self.index += 1
        return line

    def line_no(self) -> int:
        return self.index + 1

    def skip_blank_lines(self) -> int:
        skipped = 0
        while self.has_next() and not self.peek().strip():
            self.take()
            skipped += 1
        return skipped


def extract_content(markdown_text: str) -> list[str]:
    text = markdown_text.replace("\r\n", "\n").replace("\r", "\n")
    if EXTRACTED_CONTENT_MARKER in text:
        _, text = text.split(EXTRACTED_CONTENT_MARKER, 1)
    text = text.strip()
    if not text:
        raise SegmentationError("Input markdown is empty after extracting content")
    return [line.rstrip() for line in text.splitlines()]


def normalize_heading_text(line: str) -> str:
    stripped = line.strip()
    match = MARKDOWN_HEADING_RE.match(stripped)
    if match:
        return match.group(2).strip()
    return stripped


def is_markdown_heading(line: str) -> bool:
    return bool(MARKDOWN_HEADING_RE.match(line.strip()))


def is_title_line(line: str, before_abstract: bool) -> bool:
    stripped = line.strip()
    return before_abstract and bool(stripped) and stripped.endswith("?")


def is_heading(line: str, before_abstract: bool) -> bool:
    stripped = line.strip()
    normalized = normalize_heading_text(stripped)
    if not normalized:
        return False
    if stripped in {TITLE_LINE, EXTRACTED_CONTENT_MARKER} or stripped.startswith(SOURCE_PREFIX):
        return False
    if is_markdown_heading(stripped):
        return True
    if normalized in {"Abstract", "References"}:
        return True
    if is_title_line(normalized, before_abstract):
        return True
    if NUMBERED_HEADING_RE.match(normalized):
        return True
    if APPENDIX_HEADING_RE.match(normalized) and len(normalized.split()) >= 2 and len(normalized) > 8:
        return True
    return False


def is_figure_start(line: str) -> bool:
    return bool(FIGURE_RE.match(line.strip()))


def is_table_start(line: str) -> bool:
    return bool(TABLE_RE.match(line.strip()))


def is_code_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("```") or (line.startswith("    ") and len(stripped) > 0)


def is_equation_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if is_figure_start(stripped) or is_table_start(stripped) or is_heading(stripped, before_abstract=False):
        return False
    word_count = len(stripped.split())
    symbol_count = len(EQUATION_SYMBOL_RE.findall(stripped))
    if stripped.startswith("$") and stripped.endswith("$"):
        return True
    if "=" in stripped:
        return word_count <= 12 and len(stripped) <= 80
    if any(sym in stripped for sym in ("∈", "∑", "∏", "≤", "≥", "^", "_")):
        return word_count <= 12
    if symbol_count >= 2 and word_count <= 10 and len(stripped) <= 64:
        return True
    return False


def is_metadata_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.fullmatch(r"[*†‡].*", stripped):
        return True
    if stripped in {"*Equal contribution", "Equal contribution"}:
        return True
    return False


def classify_line(line: str, *, before_abstract: bool, in_references: bool, at_document_start: bool) -> str:
    stripped = line.strip()
    normalized = normalize_heading_text(stripped)
    if is_heading(stripped, before_abstract) or (at_document_start and is_title_line(normalized, before_abstract)):
        return "heading"
    if is_figure_start(stripped):
        return "figure"
    if is_table_start(stripped):
        return "table"
    if in_references:
        return "reference"
    if is_code_line(line):
        return "code"
    if is_equation_line(stripped):
        return "equation"
    if is_metadata_noise_line(stripped):
        return "unknown"
    if len(stripped) <= 2 and not stripped.isalpha():
        return "unknown"
    return "paragraph"


def should_continue_caption(lines: list[str], next_line: str, *, before_abstract: bool, in_references: bool) -> bool:
    stripped = next_line.strip()
    if not stripped:
        return False
    if is_heading(stripped, before_abstract) or is_figure_start(stripped) or is_table_start(stripped):
        return False
    if in_references:
        return False
    if len(lines) >= 1 and lines[-1].strip().endswith((".", "!", "?")):
        return False
    return True


def should_continue_caption_after_blank(lines: list[str], next_line: str, *, before_abstract: bool, in_references: bool) -> bool:
    stripped = next_line.strip()
    if not should_continue_caption(lines, next_line, before_abstract=before_abstract, in_references=in_references):
        return False
    if stripped[:1].islower():
        return True
    if any(marker in stripped for marker in ("Upper Right:", "Lower Right:", "Left:", "Right:")):
        return True
    return False


def should_continue_paragraph(current_lines: list[str], next_line: str, *, before_abstract: bool, in_references: bool) -> bool:
    stripped = next_line.strip()
    if not stripped:
        return False
    next_type = classify_line(
        next_line,
        before_abstract=before_abstract,
        in_references=in_references,
        at_document_start=False,
    )
    if next_type not in {"paragraph", "unknown"}:
        return False
    if not current_lines:
        return True
    previous = current_lines[-1].strip()
    if previous.endswith(('.', '!', '?', ':')):
        return False
    if previous.startswith(("Figure ", "Table ")):
        return False
    if is_metadata_noise_line(previous):
        return False
    if len(stripped) <= 3 and not stripped.isalpha():
        return False
    return True


def should_start_new_reference(current_lines: list[str], next_line: str) -> bool:
    if not current_lines:
        return False
    current_text = " ".join(part.strip() for part in current_lines if part.strip())
    if not current_text.endswith("."):
        return False
    stripped = next_line.strip()
    if not stripped or not stripped[0].isupper():
        return False
    return bool(REFERENCE_YEAR_RE.search(stripped))


def heading_section_value(text: str) -> str:
    stripped = normalize_heading_text(text)
    if stripped in {"Abstract", "References"}:
        return stripped.lower()
    match = SECTION_ID_RE.match(stripped)
    if match:
        return match.group(1)
    match = APPENDIX_ID_RE.match(stripped)
    if match and len(stripped.split()) >= 2:
        return match.group(1)
    if stripped.endswith("?"):
        return "title"
    return stripped


def make_block(block_id: int, block_type: str, source: str, *, section: str | None, line_start: int, line_end: int) -> dict[str, object]:
    return {
        "block_id": f"b{block_id:06d}",
        "type": block_type,
        "section": section,
        "source": source,
        "translated": None,
        "meta": {
            "line_start": line_start,
            "line_end": line_end,
        },
    }


def collect_special_block(stream: LineStream, block_type: str, *, before_abstract: bool, in_references: bool) -> tuple[list[str], int, int]:
    start_line = stream.line_no()
    lines = [stream.take().strip()]
    end_line = start_line

    while stream.has_next():
        skipped = stream.skip_blank_lines()
        next_line = stream.peek()
        if next_line is None:
            break
        can_continue = False
        if block_type in {"figure", "table"}:
            if skipped:
                can_continue = should_continue_caption_after_blank(lines, next_line, before_abstract=before_abstract, in_references=in_references)
            else:
                can_continue = should_continue_caption(lines, next_line, before_abstract=before_abstract, in_references=in_references)
        elif block_type == "equation":
            can_continue = is_equation_line(next_line)
        elif block_type == "code":
            can_continue = is_code_line(next_line)
        if not can_continue:
            if skipped:
                stream.index -= skipped
            break
        end_line = stream.line_no()
        lines.append(stream.take().strip())

    return lines, start_line, end_line


def segment_text(markdown_text: str) -> list[dict[str, object]]:
    raw_lines = extract_content(markdown_text)
    stream = LineStream(raw_lines)
    blocks: list[dict[str, object]] = []
    block_counter = 1
    current_section: str | None = None
    before_abstract = True
    in_references = False

    while stream.has_next():
        stream.skip_blank_lines()
        if not stream.has_next():
            break

        line_number = stream.line_no()
        line = stream.peek()
        assert line is not None
        block_type = classify_line(
            line,
            before_abstract=before_abstract,
            in_references=in_references,
            at_document_start=block_counter == 1,
        )

        if block_type == "heading":
            heading_text = normalize_heading_text(stream.take())
            section = heading_section_value(heading_text)
            blocks.append(make_block(block_counter, "heading", heading_text, section=section, line_start=line_number, line_end=line_number))
            block_counter += 1
            current_section = section
            if heading_text == "Abstract":
                before_abstract = False
            if heading_text == "References":
                in_references = True
            continue

        if block_type in {"figure", "table", "equation", "code"}:
            lines, start_line, end_line = collect_special_block(
                stream,
                block_type,
                before_abstract=before_abstract,
                in_references=in_references,
            )
            blocks.append(make_block(block_counter, block_type, "\n".join(lines), section=current_section, line_start=start_line, line_end=end_line))
            block_counter += 1
            continue

        if block_type == "reference":
            start_line = line_number
            lines: list[str] = []
            while stream.has_next():
                next_line = stream.peek()
                if next_line is None:
                    break
                if not next_line.strip():
                    stream.skip_blank_lines()
                    next_line = stream.peek()
                    if next_line is None:
                        break
                if is_heading(next_line, before_abstract=False):
                    break
                if lines and should_start_new_reference(lines, next_line):
                    break
                lines.append(stream.take().strip())
            end_line = start_line + max(len(lines) - 1, 0)
            if not lines:
                lines.append(stream.take().strip())
                end_line = start_line
            blocks.append(make_block(block_counter, "reference", " ".join(lines), section=current_section, line_start=start_line, line_end=end_line))
            block_counter += 1
            continue

        start_line = line_number
        lines: list[str] = [stream.take().strip()]
        end_line = start_line
        while stream.has_next():
            skipped = stream.skip_blank_lines()
            next_line = stream.peek()
            if next_line is None:
                break
            if not should_continue_paragraph(lines, next_line, before_abstract=before_abstract, in_references=in_references):
                if skipped:
                    stream.index -= skipped
                break
            end_line = stream.line_no()
            lines.append(stream.take().strip())
        paragraph_text = " ".join(lines)
        paragraph_type = "unknown" if all(len(part.strip()) <= 2 for part in lines) or is_metadata_noise_line(paragraph_text) else "paragraph"
        blocks.append(make_block(block_counter, paragraph_type, paragraph_text, section=current_section, line_start=start_line, line_end=end_line))
        block_counter += 1

    return blocks


def write_blocks(blocks: Iterable[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block, ensure_ascii=False) + "\n")
    return output_path


def run(input_path: Path, output_path: Path) -> Path:
    markdown_text = input_path.read_text(encoding="utf-8")
    blocks = segment_text(markdown_text)
    if not blocks:
        raise SegmentationError(f"No blocks generated from {input_path}")
    return write_blocks(blocks, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Segment clean paper markdown into ordered typed blocks.")
    parser.add_argument("input_md", nargs="?", default=str(DEFAULT_INPUT), help="Path to clean or extracted markdown")
    parser.add_argument("output_jsonl", nargs="?", default=str(DEFAULT_OUTPUT), help="Path to output blocks JSONL")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    input_path = Path(args.input_md)
    output_path = Path(args.output_jsonl)
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_md == str(DEFAULT_INPUT):
            input_path = clean_md_path(args.paper_id, outputs_dir)
        if args.output_jsonl == str(DEFAULT_OUTPUT):
            output_path = segmented_blocks_jsonl_path(args.paper_id, outputs_dir)
    output_path = run(input_path, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
