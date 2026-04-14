from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from src.paper_paths import glossary_json_path, repaired_en_md_path
except ModuleNotFoundError:  # pragma: no cover
    from paper_paths import glossary_json_path, repaired_en_md_path

DEFAULT_INPUT = Path("outputs/work/source_repaired.en.md")
DEFAULT_OUTPUT = Path("outputs/work/glossary.json")

CANONICAL_TRANSLATIONS = {
    "prompt injection attacks": "提示注入攻擊",
    "politically sensitive prompts": "政治敏感提示",
    "political sensitivity": "政治敏感性",
    "safety guardrails": "安全護欄",
    "censorship": "審查",
    "refusal": "拒絕",
    "partial refusal": "部分拒絕",
}

PRESERVE_TERMS = {
    "LLMs",
    "PSP",
    "PIAs",
    "RLHF",
    "LEACE",
    "GPT-4o",
    "Gemini",
    "Qwen",
    "Llama",
    "OLMo",
}

ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b")
PHRASE_WITH_ACRONYM_RE = re.compile(r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,5})\s*\(([A-Z][A-Z0-9-]{1,})\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.M)


def _looks_like_noise_heading(term: str) -> bool:
    stripped = term.strip()
    if not stripped:
        return True
    if re.match(r"^\d+(?:\.\d+)+\s+\S+$", stripped):
        return True
    if re.fullmatch(r"\d+\s+[A-Z]{1,4}", stripped):
        return True
    if re.match(r"^\d+(?:\.\d+)*\s+", stripped):
        numeric_like = re.findall(r"\d+(?:\.\d+)*", stripped)
        if len(numeric_like) > 1:
            return True
    return False


def _entry(term: str, policy: str, translation: str | None = None, source: str = "auto") -> dict[str, object]:
    item = {"term": term, "policy": policy, "source": source}
    if translation:
        item["translation_zh_tw"] = translation
    return item


def build_glossary(text: str) -> dict[str, object]:
    entries: dict[str, dict[str, object]] = {}

    for heading in HEADING_RE.findall(text):
        heading = heading.strip()
        if heading and not _looks_like_noise_heading(heading):
            entries.setdefault(heading, _entry(heading, "preferred_translation", source="heading"))

    for phrase, acronym in PHRASE_WITH_ACRONYM_RE.findall(text):
        phrase = phrase.strip()
        acronym = acronym.strip()
        if acronym in PRESERVE_TERMS or len(acronym) >= 2:
            entries.setdefault(acronym, _entry(acronym, "preserve", source="acronym"))
        if phrase.lower() in CANONICAL_TRANSLATIONS:
            entries.setdefault(
                phrase.lower(),
                _entry(phrase.lower(), "canonical_translation", CANONICAL_TRANSLATIONS[phrase.lower()], source="phrase_with_acronym"),
            )

    for term in sorted(PRESERVE_TERMS):
        if term in text:
            entries.setdefault(term, _entry(term, "preserve", source="preserve_list"))

    lowered = text.lower()
    for term, translation in CANONICAL_TRANSLATIONS.items():
        if term in lowered:
            entries.setdefault(term, _entry(term, "canonical_translation", translation, source="canonical_list"))

    for acronym in ACRONYM_RE.findall(text):
        if acronym in PRESERVE_TERMS:
            entries.setdefault(acronym, _entry(acronym, "preserve", source="acronym_scan"))

    ordered = sorted(entries.values(), key=lambda item: (str(item["term"]).lower(), str(item["policy"])))
    return {"entries": ordered}


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    text = input_path.read_text(encoding="utf-8")
    glossary = build_glossary(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(glossary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build glossary from repaired English source.")
    parser.add_argument("input_md", nargs="?", default=str(DEFAULT_INPUT))
    parser.add_argument("output_json", nargs="?", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--paper-id", default=None, help="Optional paper id used to derive default input/output paths")
    parser.add_argument("--outputs-dir", default="outputs", help="Base outputs directory used with --paper-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_md)
    output_path = Path(args.output_json)
    if args.paper_id:
        outputs_dir = Path(args.outputs_dir)
        if args.input_md == str(DEFAULT_INPUT):
            input_path = repaired_en_md_path(args.paper_id, outputs_dir)
        if args.output_json == str(DEFAULT_OUTPUT):
            output_path = glossary_json_path(args.paper_id, outputs_dir)
    output = run(input_path, output_path)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
