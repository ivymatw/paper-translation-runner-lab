from __future__ import annotations

from pathlib import Path

DEFAULT_SAMPLE_PAPER_ID = "2511.23174_Safety_Agents_or_Propaganda_Engine"
DEFAULT_PAPERS_DIR = Path("../papers")
DEFAULT_OUTPUTS_DIR = Path("outputs")


def infer_paper_id(input_pdf: Path) -> str:
    return input_pdf.stem


def paper_output_dir(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return outputs_dir / paper_id


def paper_work_dir(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_output_dir(paper_id, outputs_dir) / "work"


def default_input_pdf(paper_id: str = DEFAULT_SAMPLE_PAPER_ID, papers_dir: Path = DEFAULT_PAPERS_DIR) -> Path:
    return papers_dir / f"{paper_id}.pdf"


def default_markitdown_md(paper_id: str = DEFAULT_SAMPLE_PAPER_ID, papers_dir: Path = DEFAULT_PAPERS_DIR) -> Path:
    return papers_dir / f"{paper_id}.md"


def extracted_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_extracted.md"


def clean_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_clean.md"


def reference_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_reference.md"


def repaired_en_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_repaired.en.md"


def repaired_en_hybrid_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_repaired.hybrid.en.md"


def repaired_en_full_llm_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_repaired.full-llm.en.md"


def glossary_json_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "glossary.json"


def layout_regions_jsonl_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "layout_regions.jsonl"


def layout_clean_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "source_layout_clean.md"


def segmented_blocks_jsonl_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "blocks.clean.jsonl"


def translated_blocks_jsonl_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "translated_blocks.jsonl"


def repaired_blocks_jsonl_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_work_dir(paper_id, outputs_dir) / "translated_blocks.repaired.gemini.jsonl"


def archival_output_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_output_dir(paper_id, outputs_dir) / f"{paper_id}.zh-TW.md"


def study_output_md_path(paper_id: str, outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    return paper_output_dir(paper_id, outputs_dir) / f"{paper_id}.study.zh-TW.md"
