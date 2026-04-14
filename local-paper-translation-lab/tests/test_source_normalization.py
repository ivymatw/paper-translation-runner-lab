from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.normalize_source import (
    DEFAULT_EXTRACTED,
    DEFAULT_MARKITDOWN,
    clean_candidate_text,
    gather_candidates,
    run,
)


class SourceNormalizationTests(unittest.TestCase):
    def test_clean_candidate_text_removes_front_matter_noise_and_promotes_headings(self) -> None:
        noisy = """Paper Title

a
n
1
v
Abstract
This is a para-
graph.

1

Introduction
More text here.

2.1

Method
Figure 1: Caption text.
"""
        cleaned = clean_candidate_text(noisy)
        self.assertIn("## Abstract", cleaned)
        self.assertIn("paragraph.", cleaned)
        self.assertIn("## 1 Introduction", cleaned)
        self.assertIn("### 2.1 Method", cleaned)
        self.assertNotIn("\na\n", cleaned)
        self.assertIn("Figure 1: Caption text.", cleaned)

    def test_gather_candidates_prefers_cleaner_markitdown_when_available(self) -> None:
        candidates = gather_candidates(DEFAULT_EXTRACTED, DEFAULT_MARKITDOWN)
        names = {candidate.name for candidate in candidates}
        self.assertIn("source_extracted", names)
        self.assertIn("markitdown", names)
        scores = {candidate.name: candidate.score for candidate in candidates}
        self.assertGreater(scores["markitdown"], scores["source_extracted"])

    def test_run_writes_clean_and_reference_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "source_clean.md"
            reference_path = Path(tmpdir) / "source_reference.md"
            written_output, written_reference, chosen, _ = run(
                extracted_path=DEFAULT_EXTRACTED,
                output_path=output_path,
                markitdown_path=DEFAULT_MARKITDOWN,
                reference_path=reference_path,
            )

            self.assertEqual(written_output, output_path)
            self.assertEqual(written_reference, reference_path)
            self.assertTrue(output_path.exists())
            self.assertTrue(reference_path.exists())

            clean_text = output_path.read_text(encoding="utf-8")
            reference_text = reference_path.read_text(encoding="utf-8")

            self.assertTrue(clean_text.strip())
            self.assertIn("Are LLMs Good Safety Agents or a Propaganda Engine?", clean_text)
            self.assertIn("## Abstract", clean_text)
            self.assertIn("## 1 Introduction", clean_text)
            self.assertIn("## References", clean_text)
            self.assertNotIn("## Extracted Content", clean_text)
            self.assertNotIn("\f", clean_text)
            self.assertNotIn("\nv\n", clean_text)
            self.assertIn(f"Chosen candidate: {chosen.name}", reference_text)
            self.assertIn("markitdown", reference_text)


if __name__ == "__main__":
    unittest.main()
