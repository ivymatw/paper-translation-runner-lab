from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

try:
    from src.paper_paths import clean_md_path, repaired_en_full_llm_md_path, repaired_en_hybrid_md_path, repaired_en_md_path
except ModuleNotFoundError:  # pragma: no cover - script execution path
    from paper_paths import clean_md_path, repaired_en_full_llm_md_path, repaired_en_hybrid_md_path, repaired_en_md_path

try:
    from src.translate import GeminiTranslationClient
except ModuleNotFoundError:  # pragma: no cover - script execution path
    from translate import GeminiTranslationClient

DEFAULT_INPUT = Path("outputs/work/source_clean.md")
DEFAULT_OUTPUT = Path("outputs/work/source_repaired.en.md")
DEFAULT_OUTPUT_HYBRID = Path("outputs/work/source_repaired.hybrid.en.md")
DEFAULT_OUTPUT_FULL_LLM = Path("outputs/work/source_repaired.full-llm.en.md")

HEADING_RE = re.compile(r"^#{1,6}\s+")
CAPTION_RE = re.compile(r"^(Figure|Table)\s+\d+", re.IGNORECASE)
URLISH_RE = re.compile(r"^(?:\d+\s*)?https?://\S+$")
EMAILISH_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
METADATA_HINT_RE = re.compile(r"(?:University|Institute|Science Park|@|\d[A-Z]{2,}|Equal contribution)")
BROKEN_TOKEN_RE = re.compile(r"(?:\b[a-z]{1,4}[A-Z]{2,}\w*|\b\w+-$|\b\w*-$)")
LOWERCASE_START_RE = re.compile(r"^[a-z]")


class EnglishRepairError(RuntimeError):
    pass


class EnglishRepairClient:
    def repair(self, *, text: str, block_kind: str, mode: str) -> str:
        raise NotImplementedError


class GeminiEnglishRepairClient(GeminiTranslationClient, EnglishRepairClient):
    def repair(self, *, text: str, block_kind: str, mode: str) -> str:
        prompt = (
            "Conservatively repair academic English that was damaged by PDF extraction.\n"
            f"Repair mode: {mode}\n"
            f"Block kind: {block_kind}\n"
            "Rules:\n"
            "1. Preserve meaning, claims, citations, names, numbers, model names, dataset names, benchmark names, and technical identifiers.\n"
            "2. Fix line-break damage, hyphen splits, obvious extraction seams, and broken sentence continuity when strongly inferable.\n"
            "3. Do not summarize. Do not add new information. Do not stylistically rewrite beyond what is needed to restore readable English.\n"
            "4. If the text is metadata, preserve names/emails/institutions with minimal cleanup.\n"
            "5. Return only the repaired English block.\n"
            "Input:\n"
            f"{text}"
        )
        repaired = self._complete(prompt).strip()
        if not repaired:
            raise EnglishRepairError("Empty English repair output")
        return repaired


def _is_heading(text: str) -> bool:
    return bool(HEADING_RE.match(text.strip()))


def _is_caption(text: str) -> bool:
    return bool(CAPTION_RE.match(text.strip()))


def _is_metadata(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if EMAILISH_RE.match(stripped):
        return True
    if METADATA_HINT_RE.search(stripped) and not _is_heading(stripped) and not _is_caption(stripped):
        return True
    return False


def _can_merge(current: str, nxt: str) -> bool:
    if not current or not nxt:
        return False
    if _is_heading(current) or _is_heading(nxt):
        return False
    if _is_caption(current) or _is_caption(nxt):
        return False
    if _is_metadata(current) or _is_metadata(nxt):
        return False
    if URLISH_RE.match(current.strip()) or URLISH_RE.match(nxt.strip()):
        return False
    if current.strip().endswith(":"):
        return False
    if LOWERCASE_START_RE.match(nxt.strip()):
        return True
    if current.rstrip().endswith("-"):
        return True
    return False


def _merge_pair(left: str, right: str) -> str:
    left = left.strip()
    right = right.strip()
    if left.endswith("-") and right[:1].islower():
        return left[:-1] + right
    return f"{left} {right}".strip()


def split_blocks(text: str) -> list[str]:
    return [block.strip() for block in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n") if block.strip()]


def split_caption_mixed_body(block: str) -> tuple[str, str] | None:
    text = block.strip()
    if not text:
        return None
    if not any(marker in text for marker in ("Upper Right:", "Lower Right:", "Left:", "Right:")):
        return None
    matches = list(re.finditer(r"(?<=[.!?])\s+(?=[a-z])", text))
    if not matches:
        return None
    split_at = matches[-1].start()
    caption_part = text[:split_at].strip()
    body_part = text[matches[-1].end():].strip()
    if not caption_part or not body_part:
        return None
    return caption_part, body_part


def looks_like_caption_continuation(block: str) -> bool:
    text = block.strip()
    if not text:
        return False
    if text[:1].islower() and any(marker in text for marker in ("Upper Right:", "Lower Right:", "Left:", "Right:")):
        return True
    return False


def infer_block_kind(block: str) -> str:
    if _is_heading(block):
        return "heading"
    if _is_caption(block):
        return "caption"
    if _is_metadata(block):
        return "metadata"
    return "paragraph"


def heuristic_repair_text(text: str) -> str:
    blocks = split_blocks(text)
    repaired: list[str] = []
    idx = 0
    while idx < len(blocks):
        current = blocks[idx].strip()

        if (
            idx + 2 < len(blocks)
            and not _is_heading(current)
            and not _is_caption(current)
            and _is_metadata(blocks[idx + 1].strip())
            and _can_merge(current, blocks[idx + 2].strip())
        ):
            current = _merge_pair(current, blocks[idx + 2].strip())
            current = re.sub(r"\s+([,.;:?!])", r"\1", current)
            repaired.append(current.strip())
            repaired.append(blocks[idx + 1].strip())
            idx += 3
            continue

        if (
            idx + 2 < len(blocks)
            and not _is_heading(current)
            and not _is_caption(current)
            and not current.rstrip().endswith((".", "!", "?", ":"))
            and _is_caption(blocks[idx + 1].strip())
        ):
            mixed = split_caption_mixed_body(blocks[idx + 2].strip())
            if mixed is not None:
                caption_tail, body_tail = mixed
                repaired.append(re.sub(r"\s+([,.;:?!])", r"\1", _merge_pair(current, body_tail)).strip())
                repaired.append(re.sub(r"\s+([,.;:?!])", r"\1", _merge_pair(blocks[idx + 1].strip(), caption_tail)).strip())
                idx += 3
                continue
            if (
                idx + 3 < len(blocks)
                and looks_like_caption_continuation(blocks[idx + 2].strip())
                and not _is_caption(blocks[idx + 2].strip())
                and not _is_metadata(blocks[idx + 3].strip())
            ):
                repaired.append(re.sub(r"\s+([,.;:?!])", r"\1", _merge_pair(current, blocks[idx + 3].strip())).strip())
                repaired.append(re.sub(r"\s+([,.;:?!])", r"\1", _merge_pair(blocks[idx + 1].strip(), blocks[idx + 2].strip())).strip())
                idx += 4
                continue

        while idx + 1 < len(blocks) and _can_merge(current, blocks[idx + 1].strip()):
            current = _merge_pair(current, blocks[idx + 1].strip())
            idx += 1
        current = re.sub(r"\s+([,.;:?!])", r"\1", current)
        repaired.append(current.strip())
        idx += 1
    return "\n\n".join(block for block in repaired if block).strip() + "\n"


def is_suspicious_english_block(block: str) -> bool:
    if not block.strip():
        return False
    if _is_heading(block):
        return False
    if _is_metadata(block):
        return True
    if BROKEN_TOKEN_RE.search(block):
        return True
    if "\n" in block and not _is_caption(block):
        return True
    if block.count("Figure ") + block.count("Table ") > 1:
        return True
    return False


def _repair_with_retry(client: EnglishRepairClient, *, text: str, block_kind: str, mode: str, max_retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.repair(text=text, block_kind=block_kind, mode=mode)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise EnglishRepairError("English repair failed without exception")


def hybrid_repair_text(text: str, client: EnglishRepairClient | None = None) -> str:
    precleaned = heuristic_repair_text(text)
    if client is None:
        return precleaned
    repaired: list[str] = []
    for block in split_blocks(precleaned):
        if is_suspicious_english_block(block):
            repaired.append(_repair_with_retry(client, text=block, block_kind=infer_block_kind(block), mode="hybrid"))
        else:
            repaired.append(block)
    return "\n\n".join(repaired).strip() + "\n"


def full_llm_repair_text(text: str, client: EnglishRepairClient) -> str:
    repaired: list[str] = []
    for block in split_blocks(text):
        kind = infer_block_kind(block)
        if kind == "heading":
            repaired.append(block)
        else:
            repaired.append(_repair_with_retry(client, text=block, block_kind=kind, mode="full_llm"))
    return "\n\n".join(repaired).strip() + "\n"


def _checkpoint_path(output_path: Path) -> Path:
    return output_path.with_suffix(output_path.suffix + ".checkpoint.jsonl")


def _load_checkpoint(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    entries: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        entries[int(obj["index"])] = str(obj["text"])
    return entries


def _append_checkpoint(path: Path, index: int, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"index": index, "text": text}, ensure_ascii=False) + "\n")


def _run_llm_mode(text: str, output_path: Path, *, mode: str, client: EnglishRepairClient) -> Path:
    base_blocks = split_blocks(heuristic_repair_text(text) if mode == "hybrid" else text)
    checkpoint = _load_checkpoint(_checkpoint_path(output_path))
    repaired: list[str] = []
    for idx, block in enumerate(base_blocks):
        if idx in checkpoint:
            repaired.append(checkpoint[idx])
            continue
        kind = infer_block_kind(block)
        if mode == "hybrid" and not is_suspicious_english_block(block):
            final = block
        elif kind == "heading":
            final = block
        else:
            final = _repair_with_retry(client, text=block, block_kind=kind, mode=mode)
        repaired.append(final)
        _append_checkpoint(_checkpoint_path(output_path), idx, final)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(repaired).strip() + "\n", encoding="utf-8")
    return output_path


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    mode: str = "heuristic",
    client: EnglishRepairClient | None = None,
) -> Path:
    text = input_path.read_text(encoding="utf-8")
    if mode == "heuristic":
        repaired = heuristic_repair_text(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(repaired, encoding="utf-8")
        return output_path
    repair_client = client or GeminiEnglishRepairClient()
    if mode == "hybrid":
        return _run_llm_mode(text, output_path, mode="hybrid", client=repair_client)
    if mode == "full_llm":
        return _run_llm_mode(text, output_path, mode="full_llm", client=repair_client)
    raise EnglishRepairError(f"Unknown English repair mode: {mode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair clean English source before translation.")
    parser.add_argument("input_md", nargs="?", default=str(DEFAULT_INPUT))
    parser.add_argument("output_md", nargs="?", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=["heuristic", "hybrid", "full_llm"], default="heuristic")
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_md)
    output_path = Path(args.output_md)
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_md == str(DEFAULT_INPUT):
            input_path = clean_md_path(args.paper_id, outputs_dir)
        if args.output_md == str(DEFAULT_OUTPUT):
            if args.mode == "hybrid":
                output_path = repaired_en_hybrid_md_path(args.paper_id, outputs_dir)
            elif args.mode == "full_llm":
                output_path = repaired_en_full_llm_md_path(args.paper_id, outputs_dir)
            else:
                output_path = repaired_en_md_path(args.paper_id, outputs_dir)
    output = run(input_path, output_path, mode=args.mode)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
