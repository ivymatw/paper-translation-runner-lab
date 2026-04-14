from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.extract import decode_pdf_literal, extract_text, run

SAMPLE_PDF = REPO_ROOT.parent / "papers" / "2511.23174_Safety_Agents_or_Propaganda_Engine.pdf"


class ExtractionTests(unittest.TestCase):
    def test_decode_pdf_literal_handles_common_escapes(self) -> None:
        self.assertEqual(decode_pdf_literal(b"Hello\\040World\\nLine\\0502\\051"), "Hello World\nLine(2)")

    def test_extract_text_from_sample_pdf_is_non_empty(self) -> None:
        text = extract_text(SAMPLE_PDF)
        self.assertGreater(len(text), 5000)
        self.assertIn("Are LLMs Good Safety Agents or a Propaganda Engine?", text)
        self.assertIn("Abstract", text)
        self.assertIn("References", text)

    def test_run_writes_markdown_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "source_extracted.md"
            result = run(SAMPLE_PDF, output_path)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("# Source Extracted Text", content)
            self.assertIn("## Extracted Content", content)
            self.assertGreater(len(content.strip()), 5000)


if __name__ == "__main__":
    unittest.main()
