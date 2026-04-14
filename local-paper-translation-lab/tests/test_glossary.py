from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.glossary import build_glossary, run


class GlossaryTests(unittest.TestCase):
    def test_build_glossary_extracts_core_terms_and_policies(self) -> None:
        source = """Are LLMs Good Safety Agents or a Propaganda Engine?

## Abstract

Large Language Models (LLMs) are trained to refuse harmful content.
We introduce PSP and study prompt injection attacks (PIAs).
We use RLHF and LEACE in our analysis.
## 1 Introduction
"""
        glossary = build_glossary(source)
        entries = {entry["term"]: entry for entry in glossary["entries"]}
        self.assertIn("LLMs", entries)
        self.assertEqual(entries["LLMs"]["policy"], "preserve")
        self.assertIn("prompt injection attacks", entries)
        self.assertEqual(entries["prompt injection attacks"]["policy"], "canonical_translation")
        self.assertEqual(entries["prompt injection attacks"]["translation_zh_tw"], "提示注入攻擊")
        self.assertIn("PSP", entries)

    def test_build_glossary_ignores_numeric_heading_noise(self) -> None:
        source = """## 37.4 GPT-4o

## 1 Introduction

Large Language Models (LLMs) are discussed here.
"""
        glossary = build_glossary(source)
        terms = {entry["term"] for entry in glossary["entries"]}
        self.assertNotIn("37.4 GPT-4o", terms)
        self.assertIn("1 Introduction", terms)

    def test_build_glossary_ignores_short_noise_headings(self) -> None:
        source = """## 0 RCH

## 7 S

## 3 PSP: Politically Sensitive Prompts
"""
        glossary = build_glossary(source)
        terms = {entry["term"] for entry in glossary["entries"]}
        self.assertNotIn("0 RCH", terms)
        self.assertNotIn("7 S", terms)
        self.assertIn("3 PSP: Politically Sensitive Prompts", terms)

    def test_run_writes_glossary_json(self) -> None:
        source = "Large Language Models (LLMs) and PSP are discussed here."
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "source_repaired.en.md"
            output_path = Path(tmpdir) / "glossary.json"
            input_path.write_text(source, encoding="utf-8")
            result = run(input_path, output_path)
            self.assertEqual(result, output_path)
            parsed = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("entries", parsed)
            self.assertTrue(parsed["entries"])


if __name__ == "__main__":
    unittest.main()
