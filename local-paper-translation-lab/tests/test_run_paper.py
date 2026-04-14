from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import run_paper


class RunPaperTests(unittest.TestCase):
    def test_derive_paths_namespaces_outputs_by_paper_id(self) -> None:
        pdf = Path("/tmp/papers/demo-paper.pdf")
        paths = run_paper.derive_paths(input_pdf=pdf, paper_id="demo-paper", outputs_dir=Path("outputs"))
        self.assertEqual(paths.extracted_md, Path("outputs/demo-paper/work/source_extracted.md"))
        self.assertEqual(paths.translated_blocks_jsonl, Path("outputs/demo-paper/work/translated_blocks.jsonl"))
        self.assertEqual(paths.repaired_blocks_jsonl, Path("outputs/demo-paper/work/translated_blocks.repaired.gemini.jsonl"))
        self.assertEqual(paths.study_md, Path("outputs/demo-paper/demo-paper.study.zh-TW.md"))
        self.assertEqual(paths.study_visuals_md, Path("outputs/demo-paper/demo-paper.study.zh-TW.visuals.md"))
        self.assertEqual(paths.visuals_asset_dir, Path("outputs/demo-paper/assets/demo-paper.study.zh-TW.visuals"))
        self.assertEqual(paths.run_summary_json, Path("outputs/demo-paper/run-summary.json"))

    def test_resolve_markitdown_candidate_prefers_sibling_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = Path(tmpdir) / "demo-paper.pdf"
            md = Path(tmpdir) / "demo-paper.md"
            pdf.write_text("pdf", encoding="utf-8")
            md.write_text("md", encoding="utf-8")
            self.assertEqual(run_paper.resolve_markitdown_candidate(pdf), md)

    def test_run_pipeline_calls_stages_in_order_and_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = Path(tmpdir) / "demo-paper.pdf"
            pdf.write_text("fake pdf", encoding="utf-8")
            outputs_dir = Path(tmpdir) / "outputs"
            config = run_paper.PaperRunConfig(
                input_pdf=pdf,
                paper_id="demo-paper",
                outputs_dir=outputs_dir,
                markitdown_md=None,
                english_repair_mode="heuristic",
                with_layout_regions=False,
                render_layout_source=False,
                translation_model="gemini-2.5-flash",
                translation_endpoint="http://example.invalid",
                translation_backend="gemini",
                translation_timeout=123,
                translation_batch_size=4,
                translation_char_budget=999,
            )
            repaired_blocks = [
                {"block_id": "b1", "type": "heading", "section": "title", "source": "Demo", "translated": "示範"},
                {"block_id": "b2", "type": "heading", "section": "abstract", "source": "Abstract", "translated": "摘要"},
                {"block_id": "b3", "type": "paragraph", "section": "abstract", "source": "Body.", "translated": "正文。"},
            ]

            call_order: list[str] = []

            def _record(name: str):
                def inner(*args, **kwargs):
                    call_order.append(name)
                    return None
                return inner

            class _FakeVisuals:
                @staticmethod
                def run(*args, **kwargs):
                    call_order.append("visuals")
                    output_md = kwargs["output_md"]
                    output_md.parent.mkdir(parents=True, exist_ok=True)
                    output_md.write_text("# visual study\n", encoding="utf-8")
                    return output_md, kwargs["asset_dir"]

            with patch.object(run_paper.extract, "run", side_effect=_record("extract")), \
                patch.object(run_paper.normalize_source, "run", side_effect=_record("normalize")), \
                patch.object(run_paper.repair_english, "run", side_effect=_record("repair_english")), \
                patch.object(run_paper.glossary, "run", side_effect=_record("glossary")), \
                patch.object(run_paper.segment, "run", side_effect=_record("segment")), \
                patch.object(run_paper.translate, "run", side_effect=_record("translate")), \
                patch.object(run_paper.repair, "run", side_effect=_record("repair")), \
                patch.object(run_paper.assemble, "run", side_effect=_record("assemble")), \
                patch.object(run_paper, "load_study_blocks", return_value=repaired_blocks), \
                patch.object(run_paper, "build_study_version", return_value="# 示範\n\n## 摘要\n\n正文。\n"), \
                patch.object(run_paper, "load_visual_module", return_value=_FakeVisuals):
                paths = run_paper.run_pipeline(config)

            self.assertEqual(
                call_order,
                ["extract", "normalize", "repair_english", "glossary", "segment", "translate", "repair", "assemble", "visuals"],
            )
            self.assertTrue(paths.study_md.exists())
            self.assertTrue(paths.study_visuals_md.exists())
            self.assertTrue(paths.run_summary_json.exists())
            summary = json.loads(paths.run_summary_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["paper_id"], "demo-paper")
            self.assertEqual(summary["english_repair_mode"], "heuristic")
            self.assertEqual(summary["translation_backend"], "gemini")
            self.assertIsNone(summary["extraction_error"])
            self.assertFalse(summary["used_markitdown_fallback"])


    def test_run_pipeline_falls_back_to_markitdown_when_extract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = Path(tmpdir) / "demo-paper.pdf"
            md = Path(tmpdir) / "demo-paper.md"
            pdf.write_text("fake pdf", encoding="utf-8")
            md.write_text("# Demo\n\nAbstract\n\nBody\n", encoding="utf-8")
            outputs_dir = Path(tmpdir) / "outputs"
            config = run_paper.PaperRunConfig(
                input_pdf=pdf,
                paper_id="demo-paper",
                outputs_dir=outputs_dir,
                markitdown_md=md,
                english_repair_mode="heuristic",
                with_layout_regions=False,
                render_layout_source=False,
                translation_model="gemini-2.5-flash",
                translation_endpoint="http://example.invalid",
                translation_backend="gemini",
                translation_timeout=123,
                translation_batch_size=4,
                translation_char_budget=999,
            )
            repaired_blocks = [
                {"block_id": "b1", "type": "heading", "section": "title", "source": "Demo", "translated": "示範"},
                {"block_id": "b2", "type": "heading", "section": "abstract", "source": "Abstract", "translated": "摘要"},
            ]

            class _FakeVisuals:
                @staticmethod
                def run(*args, **kwargs):
                    output_md = kwargs["output_md"]
                    output_md.parent.mkdir(parents=True, exist_ok=True)
                    output_md.write_text("# visual study\n", encoding="utf-8")
                    return output_md, kwargs["asset_dir"]

            with patch.object(run_paper.extract, "run", side_effect=RuntimeError("extract stalled")), \
                patch.object(run_paper.normalize_source, "run", return_value=None) as normalize_run, \
                patch.object(run_paper.repair_english, "run", return_value=None), \
                patch.object(run_paper.glossary, "run", return_value=None), \
                patch.object(run_paper.segment, "run", return_value=None), \
                patch.object(run_paper.translate, "run", return_value=None), \
                patch.object(run_paper.repair, "run", return_value=None), \
                patch.object(run_paper.assemble, "run", return_value=None), \
                patch.object(run_paper, "load_study_blocks", return_value=repaired_blocks), \
                patch.object(run_paper, "build_study_version", return_value="# 示範\n"), \
                patch.object(run_paper, "load_visual_module", return_value=_FakeVisuals):
                paths = run_paper.run_pipeline(config)

            self.assertEqual(normalize_run.call_args.kwargs["extracted_path"], Path("__missing_extraction_fallback__.md"))
            summary = json.loads(paths.run_summary_json.read_text(encoding="utf-8"))
            self.assertTrue(summary["used_markitdown_fallback"])
            self.assertIn("extract stalled", summary["extraction_error"])


if __name__ == "__main__":
    unittest.main()
