from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.segment import run, segment_text

SAMPLE_CLEAN_SOURCE = REPO_ROOT / "outputs" / "work" / "source_clean.md"
SAMPLE_EXTRACTED_SOURCE = REPO_ROOT / "outputs" / "work" / "source_extracted.md"


class SegmentationTests(unittest.TestCase):
    def test_segment_text_emits_required_block_fields_from_clean_source(self) -> None:
        markdown_text = SAMPLE_CLEAN_SOURCE.read_text(encoding="utf-8")
        blocks = segment_text(markdown_text)

        self.assertGreater(len(blocks), 100)
        for index, block in enumerate(blocks, start=1):
            self.assertEqual(block["block_id"], f"b{index:06d}")
            self.assertIn("type", block)
            self.assertIn("source", block)
            self.assertTrue(str(block["source"]).strip())

    def test_segment_text_preserves_order_and_detects_core_types(self) -> None:
        markdown_text = SAMPLE_CLEAN_SOURCE.read_text(encoding="utf-8")
        blocks = segment_text(markdown_text)

        heading_sources = [block["source"] for block in blocks if block["type"] == "heading"]
        self.assertIn("Are LLMs Good Safety Agents or a Propaganda Engine?", heading_sources)
        self.assertIn("Abstract", heading_sources)
        self.assertIn("1 Introduction", heading_sources)
        self.assertIn("References", heading_sources)
        self.assertTrue(all(not source.startswith("#") for source in heading_sources))

        types = {block["type"] for block in blocks}
        self.assertIn("paragraph", types)
        self.assertIn("figure", types)
        self.assertIn("table", types)
        self.assertIn("reference", types)

        intro_index = heading_sources.index("1 Introduction")
        references_index = heading_sources.index("References")
        self.assertLess(intro_index, references_index)

    def test_run_writes_parseable_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "blocks.clean.jsonl"
            result = run(SAMPLE_CLEAN_SOURCE, output_path)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())

            lines = output_path.read_text(encoding="utf-8").splitlines()
            self.assertGreater(len(lines), 100)
            parsed = [json.loads(line) for line in lines]
            self.assertEqual(len(parsed), len(lines))
            self.assertTrue(all({"block_id", "type", "source"} <= set(block) for block in parsed))

            line_starts = [block["meta"]["line_start"] for block in parsed]
            self.assertEqual(line_starts, sorted(line_starts))

    def test_segmenter_still_supports_legacy_extracted_source_wrapper(self) -> None:
        markdown_text = SAMPLE_EXTRACTED_SOURCE.read_text(encoding="utf-8")
        blocks = segment_text(markdown_text)

        heading_sources = [block["source"] for block in blocks if block["type"] == "heading"]
        self.assertIn("Are LLMs Good Safety Agents or a Propaganda Engine?", heading_sources)
        self.assertIn("Abstract", heading_sources)
        self.assertIn("1 Introduction", heading_sources)

    def test_segment_text_splits_caption_from_following_body_paragraph(self) -> None:
        markdown_text = """# Title

Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts.

queries sensitive to a Chinese context but complies to queries sensitive to a different regional context.
"""
        blocks = segment_text(markdown_text)
        self.assertEqual(blocks[1]["type"], "figure")
        self.assertEqual(blocks[1]["source"], "Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts.")
        self.assertEqual(blocks[2]["type"], "paragraph")
        self.assertEqual(blocks[2]["source"], "queries sensitive to a Chinese context but complies to queries sensitive to a different regional context.")

    def test_segment_text_extends_caption_across_blank_line_when_next_line_is_caption_like(self) -> None:
        markdown_text = """# Title

Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts. Qwen 2.5 refuses to respond to

queries sensitive to a Chinese context but complies to queries sensitive to a different regional context.
"""
        blocks = segment_text(markdown_text)
        self.assertEqual(blocks[1]["type"], "figure")
        self.assertIn("Qwen 2.5 refuses to respond to", blocks[1]["source"])
        self.assertIn("queries sensitive to a Chinese context", blocks[1]["source"])

    def test_segment_text_keeps_caption_continuation_but_excludes_following_body_prose(self) -> None:
        markdown_text = """# Title

RQ1: How does de-politicization of our explicitly political dataset impact the refusal behaviors of models? We hypothesize that removing political information from the explicit dataset should reduce refusal rates.

Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts. Qwen 2.5 refuses to respond to

queries sensitive to a Chinese context but complies to queries sensitive to a different regional context (here, France). Upper Right: Topics extracted from the prompt are used to judge the nature of censorship in a given model. Lower Right: Cognitive Hacking is used as a Prompt Injection Attack (PIA) to elicit Ethical Dilemmas in the form of Partial Refusals.

We then measure refusal rate changes under both methods.
"""
        blocks = segment_text(markdown_text)
        self.assertEqual(blocks[1]["type"], "paragraph")
        self.assertIn("removing political information from the explicit dataset should reduce refusal rates.", blocks[1]["source"])
        self.assertEqual(blocks[2]["type"], "figure")
        self.assertIn("queries sensitive to a Chinese context", blocks[2]["source"])
        self.assertIn("Partial Refusals.", blocks[2]["source"])
        self.assertNotIn("We then measure refusal rate changes under both methods.", blocks[2]["source"])
        self.assertEqual(blocks[3]["type"], "paragraph")
        self.assertEqual(blocks[3]["source"], "We then measure refusal rate changes under both methods.")

    def test_segment_text_keeps_metadata_line_separate_from_following_body_paragraph(self) -> None:
        markdown_text = """# Title

*Equal contribution

This shift raises a critical question with profound ethical implications.
"""
        blocks = segment_text(markdown_text)
        self.assertEqual(blocks[1]["type"], "unknown")
        self.assertEqual(blocks[1]["source"], "*Equal contribution")
        self.assertEqual(blocks[2]["type"], "paragraph")
        self.assertEqual(blocks[2]["source"], "This shift raises a critical question with profound ethical implications.")


if __name__ == "__main__":
    unittest.main()
