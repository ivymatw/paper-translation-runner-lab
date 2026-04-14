from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import assemble, extract, glossary, normalize_source, repair, repair_english, segment, translate
from src.assemble_study import build_study_version, load_blocks as load_study_blocks
from src.paper_paths import (
    archival_output_md_path,
    clean_md_path,
    default_markitdown_md,
    extracted_md_path,
    glossary_json_path,
    infer_paper_id,
    layout_clean_md_path,
    layout_regions_jsonl_path,
    paper_output_dir,
    repaired_blocks_jsonl_path,
    repaired_en_md_path,
    segmented_blocks_jsonl_path,
    study_output_md_path,
    translated_blocks_jsonl_path,
)


@dataclass
class PaperRunPaths:
    paper_id: str
    input_pdf: Path
    output_dir: Path
    extracted_md: Path
    clean_md: Path
    source_reference_md: Path
    repaired_en_md: Path
    glossary_json: Path
    segmented_blocks_jsonl: Path
    translated_blocks_jsonl: Path
    repaired_blocks_jsonl: Path
    archival_md: Path
    study_md: Path
    study_visuals_md: Path
    visuals_asset_dir: Path
    layout_regions_jsonl: Path
    layout_clean_md: Path
    run_summary_json: Path


@dataclass
class PaperRunConfig:
    input_pdf: Path
    paper_id: str
    outputs_dir: Path
    markitdown_md: Path | None
    english_repair_mode: str
    with_layout_regions: bool
    render_layout_source: bool
    translation_model: str
    translation_endpoint: str
    translation_backend: str
    translation_timeout: int
    translation_batch_size: int
    translation_char_budget: int


def derive_paths(*, input_pdf: Path, paper_id: str | None = None, outputs_dir: Path = Path("outputs")) -> PaperRunPaths:
    resolved_paper_id = paper_id or infer_paper_id(input_pdf)
    output_dir = paper_output_dir(resolved_paper_id, outputs_dir)
    work_dir = output_dir / "work"
    return PaperRunPaths(
        paper_id=resolved_paper_id,
        input_pdf=input_pdf,
        output_dir=output_dir,
        extracted_md=extracted_md_path(resolved_paper_id, outputs_dir),
        clean_md=clean_md_path(resolved_paper_id, outputs_dir),
        source_reference_md=work_dir / "source_reference.md",
        repaired_en_md=repaired_en_md_path(resolved_paper_id, outputs_dir),
        glossary_json=glossary_json_path(resolved_paper_id, outputs_dir),
        segmented_blocks_jsonl=segmented_blocks_jsonl_path(resolved_paper_id, outputs_dir),
        translated_blocks_jsonl=translated_blocks_jsonl_path(resolved_paper_id, outputs_dir),
        repaired_blocks_jsonl=repaired_blocks_jsonl_path(resolved_paper_id, outputs_dir),
        archival_md=archival_output_md_path(resolved_paper_id, outputs_dir),
        study_md=study_output_md_path(resolved_paper_id, outputs_dir),
        study_visuals_md=output_dir / f"{resolved_paper_id}.study.zh-TW.visuals.md",
        visuals_asset_dir=output_dir / "assets" / f"{resolved_paper_id}.study.zh-TW.visuals",
        layout_regions_jsonl=layout_regions_jsonl_path(resolved_paper_id, outputs_dir),
        layout_clean_md=layout_clean_md_path(resolved_paper_id, outputs_dir),
        run_summary_json=output_dir / "run-summary.json",
    )


def resolve_markitdown_candidate(input_pdf: Path, explicit_markitdown: Path | None = None) -> Path | None:
    if explicit_markitdown is not None:
        return explicit_markitdown if explicit_markitdown.exists() else None
    candidate = input_pdf.with_suffix(".md")
    if candidate.exists():
        return candidate
    fallback = default_markitdown_md(input_pdf.stem)
    if fallback.exists():
        return fallback
    return None


def load_layout_modules():
    layout_regions_module = import_module("src.layout_regions")
    layout_to_source_module = import_module("src.layout_to_source")
    return layout_regions_module, layout_to_source_module


def load_visual_module():
    return import_module("src.attach_pdf_visuals")


def write_study_markdown(*, input_jsonl: Path, output_md: Path) -> Path:
    blocks = load_study_blocks(input_jsonl)
    doc = build_study_version(blocks)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(doc, encoding="utf-8")
    return output_md


def run_pipeline(config: PaperRunConfig) -> PaperRunPaths:
    paths = derive_paths(input_pdf=config.input_pdf, paper_id=config.paper_id, outputs_dir=config.outputs_dir)

    extraction_error: str | None = None
    try:
        extract.run(config.input_pdf, paths.extracted_md)
        extracted_path = paths.extracted_md
    except Exception as exc:
        extraction_error = f"{type(exc).__name__}: {exc}"
        if config.markitdown_md is None or not config.markitdown_md.exists():
            raise
        extracted_path = Path("__missing_extraction_fallback__.md")

    normalize_source.run(
        extracted_path=extracted_path,
        output_path=paths.clean_md,
        markitdown_path=config.markitdown_md,
        reference_path=paths.source_reference_md,
    )

    if config.with_layout_regions:
        layout_regions_module, layout_to_source_module = load_layout_modules()
        layout_regions_module.run(config.input_pdf, paths.layout_regions_jsonl)
        if config.render_layout_source:
            layout_to_source_module.run(paths.layout_regions_jsonl, paths.layout_clean_md)

    repair_english.run(paths.clean_md, paths.repaired_en_md, mode=config.english_repair_mode)
    glossary.run(paths.repaired_en_md, paths.glossary_json)
    segment.run(paths.clean_md, paths.segmented_blocks_jsonl)
    translate.run(
        paths.segmented_blocks_jsonl,
        paths.translated_blocks_jsonl,
        model=config.translation_model,
        endpoint=config.translation_endpoint,
        timeout=config.translation_timeout,
        batch_size=config.translation_batch_size,
        char_budget=config.translation_char_budget,
        backend=config.translation_backend,
        glossary_path=paths.glossary_json,
    )
    repair.run(paths.translated_blocks_jsonl, paths.repaired_blocks_jsonl)
    assemble.run(paths.repaired_blocks_jsonl, paths.archival_md)
    write_study_markdown(input_jsonl=paths.repaired_blocks_jsonl, output_md=paths.study_md)
    visuals_module = load_visual_module()
    visuals_module.run(
        pdf_path=config.input_pdf,
        input_md=paths.study_md,
        output_md=paths.study_visuals_md,
        asset_dir=paths.visuals_asset_dir,
    )

    summary = {
        "paper_id": paths.paper_id,
        "input_pdf": str(paths.input_pdf),
        "markitdown_md": str(config.markitdown_md) if config.markitdown_md else None,
        "extraction_error": extraction_error,
        "used_markitdown_fallback": extraction_error is not None and config.markitdown_md is not None,
        "english_repair_mode": config.english_repair_mode,
        "with_layout_regions": config.with_layout_regions,
        "render_layout_source": config.render_layout_source,
        "translation_model": config.translation_model,
        "translation_backend": config.translation_backend,
        "paths": {k: str(v) for k, v in asdict(paths).items() if k not in {"paper_id"}},
    }
    paths.run_summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.run_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full paper translation pipeline for one paper.")
    parser.add_argument("input_pdf", type=Path, help="Path to the input paper PDF")
    parser.add_argument("--paper-id", default=None, help="Optional stable paper id for output namespacing")
    parser.add_argument("--outputs-dir", type=Path, default=Path("outputs"), help="Base outputs directory")
    parser.add_argument("--markitdown", type=Path, default=None, help="Optional markitdown-generated markdown candidate")
    parser.add_argument("--english-repair-mode", choices=["heuristic", "hybrid", "full_llm"], default="heuristic")
    parser.add_argument("--with-layout-regions", action="store_true", help="Also emit layout-region hints using PDFMathTranslate's layout parser")
    parser.add_argument("--render-layout-source", action="store_true", help="Render layout regions into an alternate source artifact (only meaningful with --with-layout-regions)")
    parser.add_argument("--translation-model", default=translate.DEFAULT_MODEL, help="Translation model name / alias")
    parser.add_argument("--translation-endpoint", default=translate.DEFAULT_ENDPOINT, help="Translation endpoint")
    parser.add_argument("--translation-backend", default=translate.DEFAULT_BACKEND, choices=["auto", "gemini", "ollama", "openai"], help="Translation backend selector")
    parser.add_argument("--translation-timeout", type=int, default=translate.DEFAULT_TIMEOUT, help="Per-request translation timeout in seconds")
    parser.add_argument("--translation-batch-size", type=int, default=translate.DEFAULT_BATCH_SIZE, help="Maximum translated blocks per request")
    parser.add_argument("--translation-char-budget", type=int, default=translate.DEFAULT_CHAR_BUDGET, help="Maximum source characters per request")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = PaperRunConfig(
        input_pdf=args.input_pdf,
        paper_id=args.paper_id or infer_paper_id(args.input_pdf),
        outputs_dir=args.outputs_dir,
        markitdown_md=resolve_markitdown_candidate(args.input_pdf, args.markitdown),
        english_repair_mode=args.english_repair_mode,
        with_layout_regions=args.with_layout_regions,
        render_layout_source=args.render_layout_source,
        translation_model=args.translation_model,
        translation_endpoint=args.translation_endpoint,
        translation_backend=args.translation_backend,
        translation_timeout=args.translation_timeout,
        translation_batch_size=args.translation_batch_size,
        translation_char_budget=args.translation_char_budget,
    )
    paths = run_pipeline(config)
    print(paths.study_md)
    print(paths.study_visuals_md)
    print(paths.archival_md)
    print(paths.run_summary_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
