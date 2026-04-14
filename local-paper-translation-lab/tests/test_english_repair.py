from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.repair_english import (
    full_llm_repair_text,
    heuristic_repair_text,
    hybrid_repair_text,
    infer_block_kind,
    is_suspicious_english_block,
    run,
)


class FakeEnglishRepairClient:
    def repair(self, *, text: str, block_kind: str, mode: str) -> str:
        prefix = "HYBRID" if mode == "hybrid" else "FULL"
        return f"{prefix}:{block_kind}:{text.replace(chr(10), ' ')}"


class FlakyEnglishRepairClient:
    def __init__(self) -> None:
        self.calls = 0

    def repair(self, *, text: str, block_kind: str, mode: str) -> str:
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("temporary unavailable")
        return f"{mode}:{block_kind}:{text.replace(chr(10), ' ')}"


class EnglishRepairTests(unittest.TestCase):
    def test_heuristic_repair_text_joins_hyphen_split_and_lowercase_continuation(self) -> None:
        source = """## 1 Introduction

These research questions form a logical progression: RQ1 establishes the theoretical foundation for distinguishing censorship from safety and explores the mechanisms underlying politically sen-

sitive refusals, and RQ2 identifies nuanced refusal behaviors that existing taxonomies miss.

Figure 1: A caption.

queries sensitive to a Chinese context but complies elsewhere.
"""
        repaired = heuristic_repair_text(source)
        self.assertIn("politically sensitive refusals", repaired)
        self.assertNotIn("politically sen-\n\nsitive", repaired)
        self.assertIn("Figure 1: A caption.", repaired)

    def test_infer_block_kind_distinguishes_heading_caption_metadata(self) -> None:
        self.assertEqual(infer_block_kind("## 1 Introduction"), "heading")
        self.assertEqual(infer_block_kind("Figure 1: A caption."), "caption")
        self.assertEqual(infer_block_kind("foo@example.com"), "metadata")
        self.assertEqual(infer_block_kind("This is a paragraph."), "paragraph")

    def test_hybrid_repairs_only_suspicious_blocks_after_heuristic_cleanup(self) -> None:
        source = """## Abstract

This is a para-

graph.

foo@example.com
"""
        repaired = hybrid_repair_text(source, FakeEnglishRepairClient())
        self.assertIn("paragraph.", repaired)
        self.assertIn("HYBRID:metadata:foo@example.com", repaired)
        self.assertNotIn("HYBRID:paragraph", repaired)

    def test_heuristic_preclean_keeps_author_metadata_lines_separate(self) -> None:
        source = """Are LLMs Good Safety Agents or a Propaganda Engine?

Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4

4CMU 5University of Toronto 8University of Michigan

1SMU 2University of Trieste 6Vector Institute

neemeshy@smu.edu.sg
"""
        repaired = heuristic_repair_text(source)
        self.assertIn("4CMU 5University of Toronto 8University of Michigan", repaired)
        self.assertIn("1SMU 2University of Trieste 6Vector Institute", repaired)
        self.assertNotIn("Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4 4CMU", repaired)

    def test_heuristic_preclean_splits_affiliations_into_separate_blocks(self) -> None:
        source = """Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6

3AREA Science Park 7MPI for Intelligent Systems

4CMU 5University of Toronto 8University of Michigan

1SMU 2University of Trieste 6Vector Institute

neemeshy@smu.edu.sg
"""
        repaired = heuristic_repair_text(source)
        blocks = [block.strip() for block in repaired.split("\n\n") if block.strip()]
        self.assertIn("3AREA Science Park 7MPI for Intelligent Systems", blocks)
        self.assertIn("4CMU 5University of Toronto 8University of Michigan", blocks)
        self.assertIn("1SMU 2University of Trieste 6Vector Institute", blocks)
        self.assertIn("neemeshy@smu.edu.sg", blocks)

    def test_heuristic_preclean_preserves_caption_body_boundary(self) -> None:
        source = """Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts.

queries sensitive to a Chinese context but complies to queries sensitive to a different regional context.
"""
        repaired = heuristic_repair_text(source)
        blocks = [block.strip() for block in repaired.split("\n\n") if block.strip()]
        self.assertEqual(blocks[0], "Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts.")
        self.assertEqual(blocks[1], "queries sensitive to a Chinese context but complies to queries sensitive to a different regional context.")

    def test_heuristic_repair_isolates_intrusive_footnote_and_merges_surrounding_prose(self) -> None:
        source = """## 1 Introduction

Censorship has historically been enforced through direct control of media, education, and public discourse. As LLMs become widely

*Equal contribution

adopted for information retrieval and generation, they transform from tools for studying censorship into potential agents of censorship themselves.
"""
        repaired = heuristic_repair_text(source)
        blocks = [block.strip() for block in repaired.split("\n\n") if block.strip()]
        self.assertIn(
            "Censorship has historically been enforced through direct control of media, education, and public discourse. As LLMs become widely adopted for information retrieval and generation, they transform from tools for studying censorship into potential agents of censorship themselves.",
            blocks,
        )
        prose_blocks = [block for block in blocks if "As LLMs become widely" in block]
        self.assertEqual(len(prose_blocks), 1)
        self.assertNotIn("*Equal contribution", prose_blocks[0])

    def test_heuristic_repair_pulls_body_continuation_out_of_caption_mixed_line(self) -> None:
        source = """## 1 Introduction

To address this gap, we develop PSP, a comprehensive dataset. Using PSP, we investigate two research questions:

RQ1: How does de-politicization of our explicitly political dataset impact the refusal behaviors of models? We hypothesize that removing political

Figure 1: Left: Difference in responses of Qwen 2.5 32B in different contexts. Qwen 2.5 refuses to respond to

queries sensitive to a Chinese context but complies to queries sensitive to a different regional context (here, France). Upper Right: Topics extracted from the prompt are used to judge the nature of censorship in a given model. Lower Right: Cognitive Hacking is used as a Prompt Injection Attack (PIA) to elicit Ethical Dilemmas in the form of Partial Refusals. information from the explicit dataset should reduce refusal rates, since de-politicization removes the harmful content.
"""
        repaired = heuristic_repair_text(source)
        blocks = [block.strip() for block in repaired.split("\n\n") if block.strip()]
        self.assertIn(
            "RQ1: How does de-politicization of our explicitly political dataset impact the refusal behaviors of models? We hypothesize that removing political information from the explicit dataset should reduce refusal rates, since de-politicization removes the harmful content.",
            blocks,
        )
        figure_blocks = [block for block in blocks if block.startswith("Figure 1:")]
        self.assertEqual(len(figure_blocks), 1)
        self.assertIn("Partial Refusals.", figure_blocks[0])
        self.assertNotIn("information from the explicit dataset should reduce refusal rates", figure_blocks[0])

    def test_full_llm_repairs_all_non_heading_blocks(self) -> None:
        source = """## Abstract

This is a paragraph.

Figure 1: A caption.
"""
        repaired = full_llm_repair_text(source, FakeEnglishRepairClient())
        self.assertIn("## Abstract", repaired)
        self.assertIn("FULL:paragraph:This is a paragraph.", repaired)
        self.assertIn("FULL:caption:Figure 1: A caption.", repaired)

    def test_suspicious_metadata_block_is_flagged(self) -> None:
        self.assertTrue(is_suspicious_english_block("foo@example.com"))
        self.assertFalse(is_suspicious_english_block("## 1 Introduction"))

    def test_full_llm_repair_retries_temporary_failures(self) -> None:
        source = """## Abstract

This is a paragraph.
"""
        repaired = full_llm_repair_text(source, FlakyEnglishRepairClient())
        self.assertIn("full_llm:paragraph:This is a paragraph.", repaired)

    def test_run_writes_repaired_source_file(self) -> None:
        source = """## Abstract

This is a para-

graph.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "source_clean.md"
            output_path = Path(tmpdir) / "source_repaired.en.md"
            input_path.write_text(source, encoding="utf-8")
            result = run(input_path, output_path, mode="heuristic")
            self.assertEqual(result, output_path)
            repaired = output_path.read_text(encoding="utf-8")
            self.assertIn("paragraph.", repaired)


if __name__ == "__main__":
    unittest.main()
