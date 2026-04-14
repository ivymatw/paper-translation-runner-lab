from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from src.paper_paths import (
        DEFAULT_SAMPLE_PAPER_ID,
        clean_md_path,
        default_markitdown_md,
        extracted_md_path,
        infer_paper_id,
        reference_md_path,
    )
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import (
        DEFAULT_SAMPLE_PAPER_ID,
        clean_md_path,
        default_markitdown_md,
        extracted_md_path,
        infer_paper_id,
        reference_md_path,
    )

DEFAULT_EXTRACTED = Path("outputs/work/source_extracted.md")
DEFAULT_MARKITDOWN = default_markitdown_md()
DEFAULT_OUTPUT = Path("outputs/work/source_clean.md")
DEFAULT_REFERENCE = Path("outputs/work/source_reference.md")


@dataclass
class SourceCandidate:
    name: str
    path: Path
    raw_text: str
    normalized_text: str
    score: float


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def unwrap_extracted_markdown(text: str) -> str:
    marker = "## Extracted Content"
    if marker not in text:
        return text.strip()
    _, remainder = text.split(marker, 1)
    return remainder.strip()


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2009", " ")
    text = text.replace("\u200a", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")
    text = text.replace("\u2060", "")
    text = text.replace("\t", " ")
    text = text.replace("\f", "\n\n")
    return text


def looks_like_vertical_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) == 1:
        return True
    if re.fullmatch(r"[\[\].:]+", stripped):
        return True
    return False


def remove_front_matter_noise(lines: list[str]) -> list[str]:
    abstract_index = next((index for index, line in enumerate(lines) if line.strip() == "Abstract"), None)
    if abstract_index is None:
        return lines

    cleaned: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index < abstract_index and looks_like_vertical_noise(stripped):
            continue
        cleaned.append(line)
    return cleaned


def join_split_headings(lines: list[str]) -> list[str]:
    joined: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        if re.fullmatch(r"\d+(?:\.\d+)*", current):
            next_non_empty = index + 1
            while next_non_empty < len(lines) and not lines[next_non_empty].strip():
                next_non_empty += 1
            if next_non_empty < len(lines):
                following = lines[next_non_empty].strip()
                if following and not re.match(r"^(Figure|Table)\s+\d+", following):
                    if is_heading_text(following):
                        joined.append(f"{current} {following}")
                        index = next_non_empty + 1
                        continue
        joined.append(lines[index])
        index += 1
    return joined


def is_heading_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped in {"Abstract", "References"}:
        return True
    if re.fullmatch(r"[A-Z] [A-Za-z].*", stripped):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)* [A-Z][A-Za-z0-9,\-–()/' ]+", stripped):
        return True
    words = stripped.split()
    if 1 <= len(words) <= 8 and sum(word[:1].isupper() for word in words if word) >= max(1, len(words) - 1):
        return True
    return False


def markdown_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped == "Abstract":
        return "## Abstract"
    if stripped == "References":
        return "## References"
    if re.fullmatch(r"\d+ [A-Z].*", stripped):
        return f"## {stripped}"
    if re.fullmatch(r"\d+\.\d+ [A-Z].*", stripped):
        return f"### {stripped}"
    if re.fullmatch(r"\d+\.\d+\.\d+ [A-Z].*", stripped):
        return f"#### {stripped}"
    if re.fullmatch(r"[A-Z] [A-Z].*", stripped):
        return f"## {stripped}"
    return None


def looks_like_table_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^(Figure|Table)\s+\d+", stripped):
        return True
    if "|" in stripped:
        return True
    if re.search(r"\$\d", stripped):
        return True
    if re.fullmatch(r"[\d.]+", stripped):
        return True
    tokens = stripped.split()
    if len(tokens) >= 4:
        numeric_tokens = sum(bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", token.strip("%,()"))) for token in tokens)
        if numeric_tokens >= max(2, len(tokens) // 2):
            return True
    return False


def should_join_without_space(left: str, right: str) -> bool:
    return left.endswith("-") and right[:1].islower()


def should_continue_paragraph(current: str, nxt: str) -> bool:
    if not current or not nxt:
        return False
    if markdown_heading(current) or markdown_heading(nxt):
        return False
    if looks_like_table_line(current) or looks_like_table_line(nxt):
        return False
    if current.endswith(":"):
        return False
    if re.fullmatch(r"[*†‡].*", current):
        return False
    if re.fullmatch(r"\(?[A-Za-z]?\d+[A-Za-z]?\)?", current):
        return False
    return True


def clean_candidate_text(text: str) -> str:
    text = normalize_whitespace(text)
    lines = [re.sub(r"[ ]{2,}", " ", line).strip() for line in text.split("\n")]
    lines = remove_front_matter_noise(lines)
    lines = join_split_headings(lines)

    blocks: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        merged = paragraph[0]
        for part in paragraph[1:]:
            if should_join_without_space(merged, part):
                merged = merged[:-1] + part
            else:
                merged = f"{merged} {part}"
        merged = re.sub(r"\s+([,.;:?!])", r"\1", merged)
        merged = re.sub(r"\( ", "(", merged)
        merged = re.sub(r" \)", ")", merged)
        blocks.append(merged.strip())
        paragraph.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue

        heading = markdown_heading(line)
        if heading:
            flush_paragraph()
            blocks.append(heading)
            continue

        if looks_like_table_line(line):
            flush_paragraph()
            blocks.append(line)
            continue

        if paragraph and should_continue_paragraph(paragraph[-1], line):
            paragraph.append(line)
        else:
            flush_paragraph()
            paragraph.append(line)

    flush_paragraph()

    cleaned = "\n\n".join(block for block in blocks if block.strip())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def score_candidate(text: str) -> float:
    lines = [line for line in normalize_whitespace(text).splitlines()]
    if not lines:
        return float("-inf")
    non_empty = [line.strip() for line in lines if line.strip()]
    if not non_empty:
        return float("-inf")

    score = 0.0
    score += min(len(text) / 1000.0, 80.0)
    score += 10.0 if "Abstract" in text else 0.0
    score += 10.0 if "References" in text else 0.0
    score += 8.0 if "Introduction" in text else 0.0

    single_char_lines = sum(1 for line in non_empty if looks_like_vertical_noise(line))
    weird_characters = sum(text.count(ch) for ch in ("�", "\x00", "cid:"))
    control_like = text.count("\f")
    average_line_length = sum(len(line) for line in non_empty) / max(1, len(non_empty))

    score -= single_char_lines * 1.5
    score -= weird_characters * 4.0
    score -= control_like * 2.0
    score += min(average_line_length / 4.0, 20.0)
    return score


def build_candidate(name: str, path: Path, unwrap_extracted: bool = False) -> SourceCandidate:
    raw_text = read_text(path)
    if unwrap_extracted:
        raw_text = unwrap_extracted_markdown(raw_text)
    normalized_text = clean_candidate_text(raw_text)
    return SourceCandidate(
        name=name,
        path=path,
        raw_text=raw_text,
        normalized_text=normalized_text,
        score=score_candidate(raw_text),
    )


def gather_candidates(extracted_path: Path, markitdown_path: Path | None) -> list[SourceCandidate]:
    candidates: list[SourceCandidate] = []
    if extracted_path.exists():
        candidates.append(build_candidate("source_extracted", extracted_path, unwrap_extracted=True))
    if markitdown_path and markitdown_path.exists():
        candidates.append(build_candidate("markitdown", markitdown_path))
    return candidates


def choose_best_candidate(candidates: list[SourceCandidate]) -> SourceCandidate:
    if not candidates:
        raise FileNotFoundError("No source candidates available for normalization")
    return max(candidates, key=lambda candidate: candidate.score)


def format_reference(chosen: SourceCandidate, candidates: list[SourceCandidate]) -> str:
    lines = [
        "# Source Reference",
        "",
        f"Chosen candidate: {chosen.name}",
        f"Chosen path: {chosen.path}",
        "",
        "## Candidate scores",
        "",
    ]
    for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
        lines.append(f"- {candidate.name}: score={candidate.score:.2f} path={candidate.path}")
    lines.extend([
        "",
        "## Notes",
        "",
        "- Prefer markitdown output when it is clearly cleaner.",
        "- Retain raw extraction as a secondary reference candidate.",
    ])
    return "\n".join(lines).strip() + "\n"


def run(
    extracted_path: Path = DEFAULT_EXTRACTED,
    output_path: Path = DEFAULT_OUTPUT,
    markitdown_path: Path | None = DEFAULT_MARKITDOWN,
    reference_path: Path | None = DEFAULT_REFERENCE,
) -> tuple[Path, Path | None, SourceCandidate, list[SourceCandidate]]:
    candidates = gather_candidates(extracted_path, markitdown_path)
    chosen = choose_best_candidate(candidates)
    if not chosen.normalized_text.strip():
        raise RuntimeError(f"Normalization produced empty output from {chosen.path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(chosen.normalized_text + "\n", encoding="utf-8")

    written_reference: Path | None = None
    if reference_path is not None:
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_text(format_reference(chosen, candidates), encoding="utf-8")
        written_reference = reference_path

    return output_path, written_reference, chosen, candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Construct a clean English source artifact from available candidates.")
    parser.add_argument("--extracted", default=str(DEFAULT_EXTRACTED), help="Path to outputs/work/source_extracted.md")
    parser.add_argument("--markitdown", default=str(DEFAULT_MARKITDOWN), help="Optional markitdown-generated markdown candidate")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to outputs/work/source_clean.md")
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE), help="Path to outputs/work/source_reference.md")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    outputs_dir = Path(args.outputs_dir)
    extracted_path = Path(args.extracted)
    paper_id = args.paper_id or (infer_paper_id(extracted_path.parent.parent) if extracted_path.name == "source_extracted.md" and extracted_path.parent.name == "work" else None)
    if paper_id is None and args.extracted != str(DEFAULT_EXTRACTED):
        paper_id = infer_paper_id(extracted_path)
    output_path_arg = Path(args.output)
    reference_path_arg = Path(args.reference) if args.reference else None
    if args.paper_id and args.output == str(DEFAULT_OUTPUT):
        output_path_arg = clean_md_path(args.paper_id, outputs_dir)
    if args.paper_id and args.reference == str(DEFAULT_REFERENCE):
        reference_path_arg = reference_md_path(args.paper_id, outputs_dir)
    if args.paper_id and args.extracted == str(DEFAULT_EXTRACTED):
        extracted_path = extracted_md_path(args.paper_id, outputs_dir)
    markitdown_path = Path(args.markitdown) if args.markitdown else None
    if args.paper_id and args.markitdown == str(DEFAULT_MARKITDOWN):
        markitdown_path = default_markitdown_md(args.paper_id)
    reference_path = reference_path_arg
    output_path, written_reference, chosen, _ = run(
        extracted_path=extracted_path,
        output_path=output_path_arg,
        markitdown_path=markitdown_path,
        reference_path=reference_path,
    )
    print(f"source_clean={output_path}")
    if written_reference is not None:
        print(f"source_reference={written_reference}")
    print(f"chosen_candidate={chosen.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
