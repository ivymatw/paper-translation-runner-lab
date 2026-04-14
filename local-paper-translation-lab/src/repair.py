from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

try:
    from src.paper_paths import repaired_blocks_jsonl_path, translated_blocks_jsonl_path
except ModuleNotFoundError:  # pragma: no cover - script execution path
    from paper_paths import repaired_blocks_jsonl_path, translated_blocks_jsonl_path

try:
    from src.translate import GeminiTranslationClient, is_likely_truncated_translation
except ModuleNotFoundError:  # pragma: no cover - script execution path
    from translate import GeminiTranslationClient, is_likely_truncated_translation

DEFAULT_INPUT = Path("outputs/work/translated_blocks.gemini.jsonl")
DEFAULT_OUTPUT = Path("outputs/work/translated_blocks.repaired.gemini.jsonl")

TRANSLATION_ERROR_RE = re.compile(r"\[TRANSLATION_ERROR:[^\]]+\]")
PROTECTED_RE = re.compile(r"§PROTECTED_\d+§")
LATIN_RE = re.compile(r"[A-Za-z]{4,}")


class RepairError(RuntimeError):
    pass


class GeminiRepairClient(GeminiTranslationClient):
    def repair(self, *, source: str, draft: str, block_type: str, section: str) -> str:
        prompt = (
            "Repair the following zh-TW academic translation draft.\n"
            f"Block type: {block_type}\n"
            f"Section: {section or 'unknown'}\n"
            "Goal: produce faithful, readable Traditional Chinese used in Taiwan.\n"
            "Rules:\n"
            "1. Preserve claims, citations, names, numbers, equations, model names, dataset names, and technical identifiers.\n"
            "2. Remove chunk seams, placeholder residue, and obvious translation artifacts when possible.\n"
            "3. Do not summarize. Do not omit content unless it is pure artifact noise.\n"
            "4. Return only the repaired zh-TW text.\n"
            "Source English:\n"
            f"{source}\n\n"
            "Draft zh-TW:\n"
            f"{draft}"
        )
        return self._complete(prompt).strip()


def load_blocks(path: Path) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                blocks.append(json.loads(line))
    return blocks


def write_blocks(blocks: list[dict[str, object]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block, ensure_ascii=False) + "\n")
    return path


def is_suspicious_block(block: dict[str, object]) -> bool:
    block_type = str(block.get("type") or "")
    translated = str(block.get("translated") or "")
    source = str(block.get("source") or "")

    if block_type not in {"heading", "paragraph"}:
        return False
    if not translated.strip():
        return True
    if TRANSLATION_ERROR_RE.search(translated):
        return True
    if PROTECTED_RE.search(translated):
        return True
    if translated.count("\n\n") >= 4:
        return True

    latin_hits = LATIN_RE.findall(translated)
    latin_density = sum(len(hit) for hit in latin_hits) / max(1, len(translated))
    if block_type == "paragraph" and len(latin_hits) >= 10 and latin_density >= 0.18 and len(translated) > 120:
        return True
    if len(translated) > max(len(source) * 4, 1600):
        return True
    if is_likely_truncated_translation(source, translated, block_type=block_type):
        return True
    return False


def detect_suspicious_blocks(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [block for block in blocks if is_suspicious_block(block)]


def repair_blocks(blocks: list[dict[str, object]], client, *, max_retries: int = 3) -> list[dict[str, object]]:
    repaired_blocks = [dict(block) for block in blocks]
    for block in repaired_blocks:
        if not is_suspicious_block(block):
            continue
        source = str(block.get("source") or "")
        draft = str(block.get("translated") or "")
        repaired = ""
        for attempt in range(max_retries):
            try:
                repaired = client.repair(
                    source=source,
                    draft=draft,
                    block_type=str(block.get("type") or "paragraph"),
                    section=str(block.get("section") or ""),
                ).strip()
                break
            except Exception:
                if attempt == max_retries - 1:
                    repaired = ""
                else:
                    time.sleep(2 * (attempt + 1))
        if repaired:
            block["repaired"] = repaired
            block["translated"] = repaired
    return repaired_blocks


def run(input_path: Path, output_path: Path, *, client=None) -> Path:
    blocks = load_blocks(input_path)
    repair_client = client or GeminiRepairClient()
    repaired = repair_blocks(blocks, repair_client)
    return write_blocks(repaired, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair suspicious translated blocks with Gemini.")
    parser.add_argument("input_jsonl", nargs="?", default=str(DEFAULT_INPUT))
    parser.add_argument("output_jsonl", nargs="?", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_jsonl)
    output_path = Path(args.output_jsonl)
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_jsonl == str(DEFAULT_INPUT):
            input_path = translated_blocks_jsonl_path(args.paper_id, outputs_dir)
        if args.output_jsonl == str(DEFAULT_OUTPUT):
            output_path = repaired_blocks_jsonl_path(args.paper_id, outputs_dir)
    output = run(input_path, output_path)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
