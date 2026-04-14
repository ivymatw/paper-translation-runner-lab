from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.paper_paths import (
    archival_output_md_path,
    clean_md_path,
    default_input_pdf,
    extracted_md_path,
    infer_paper_id,
    layout_regions_jsonl_path,
    study_output_md_path,
)


class PaperPathTests(unittest.TestCase):
    def test_infer_paper_id_from_pdf_path(self) -> None:
        self.assertEqual(infer_paper_id(Path("/tmp/foo/bar/my-paper.pdf")), "my-paper")

    def test_default_input_pdf_uses_paper_id(self) -> None:
        self.assertEqual(default_input_pdf("demo-paper"), Path("../papers/demo-paper.pdf"))

    def test_output_paths_are_namespaced_by_paper_id(self) -> None:
        paper_id = "demo-paper"
        self.assertEqual(extracted_md_path(paper_id), Path("outputs/demo-paper/work/source_extracted.md"))
        self.assertEqual(clean_md_path(paper_id), Path("outputs/demo-paper/work/source_clean.md"))
        self.assertEqual(layout_regions_jsonl_path(paper_id), Path("outputs/demo-paper/work/layout_regions.jsonl"))
        self.assertEqual(archival_output_md_path(paper_id), Path("outputs/demo-paper/demo-paper.zh-TW.md"))
        self.assertEqual(study_output_md_path(paper_id), Path("outputs/demo-paper/demo-paper.study.zh-TW.md"))


if __name__ == "__main__":
    unittest.main()
