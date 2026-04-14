from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.assemble import assemble_blocks, resolve_input_path, run
from src.assemble_study import build_study_version


class AssemblyTests(unittest.TestCase):
    def test_assemble_blocks_preserves_order_and_formats_sections(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": "Bad repeated output\nBad repeated output\nBad repeated output",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "heading",
                "section": "abstract",
                "source": "Abstract",
                "translated": "Abstract",
                "meta": {},
            },
            {
                "block_id": "b3",
                "type": "paragraph",
                "section": "abstract",
                "source": "English fallback paragraph.",
                "translated": "這是一段繁體中文摘要。",
                "meta": {},
            },
            {
                "block_id": "b4",
                "type": "figure",
                "section": "1",
                "source": "Figure 1: Sample figure.",
                "translated": None,
                "meta": {},
            },
            {
                "block_id": "b5",
                "type": "equation",
                "section": "1",
                "source": "r = f(x)",
                "translated": None,
                "meta": {},
            },
            {
                "block_id": "b6",
                "type": "heading",
                "section": "references",
                "source": "References",
                "translated": "References\nReferences\nPassage:",
                "meta": {},
            },
            {
                "block_id": "b7",
                "type": "reference",
                "section": "references",
                "source": "Author. 2025. Title.",
                "translated": None,
                "meta": {},
            },
        ]

        markdown = assemble_blocks(blocks)

        self.assertIn("# LLM 是優秀的安全代理，還是宣傳引擎？", markdown)
        self.assertIn("## 摘要", markdown)
        self.assertIn("這是一段繁體中文摘要。", markdown)
        self.assertIn("> [Figure] Figure 1: Sample figure.", markdown)
        self.assertIn("$$\nr = f(x)\n$$", markdown)
        self.assertIn("## 參考文獻", markdown)
        self.assertLess(markdown.index("## 摘要"), markdown.index("> [Figure] Figure 1: Sample figure."))
        self.assertLess(markdown.index("> [Figure] Figure 1: Sample figure."), markdown.index("## 參考文獻"))

    def test_resolve_input_path_falls_back_to_qwen_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            work = base / "outputs" / "work"
            work.mkdir(parents=True)
            qwen_path = work / "translated_blocks.qwen.jsonl"
            qwen_path.write_text("{}\n", encoding="utf-8")

            cwd = Path.cwd()
            try:
                import os
                os.chdir(base)
                resolved = resolve_input_path()
            finally:
                os.chdir(cwd)

        self.assertEqual(resolved, Path("outputs/work/translated_blocks.qwen.jsonl"))

    def test_build_study_version_prefers_repaired_text_and_stops_before_references(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": "LLM 是優秀的安全代理，還是宣傳引擎？",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "abstract",
                "source": "English abstract.",
                "translated": "Draft abstract with §PROTECTED_0§ residue.",
                "repaired": "修復後摘要。",
                "meta": {},
            },
            {
                "block_id": "b3",
                "type": "heading",
                "section": "references",
                "source": "References",
                "translated": "參考文獻",
                "meta": {},
            },
            {
                "block_id": "b4",
                "type": "reference",
                "section": "references",
                "source": "Author. 2025. Title.",
                "translated": "Author. 2025. Title.",
                "meta": {},
            },
        ]

        markdown = build_study_version(blocks)
        self.assertIn("修復後摘要。", markdown)
        self.assertNotIn("§PROTECTED_0§", markdown)
        self.assertNotIn("參考文獻", markdown)
        self.assertNotIn("Author. 2025. Title.", markdown)

    def test_build_study_version_falls_back_to_source_when_translation_is_truncated(self) -> None:
        long_source = (
            "LLMs are trained to obey benign user requests but refuse prompts that are deemed unsafe or harmful through RLHF "
            "and preference alignment. Following prior work, we categorize multiple refusal behaviors and provide examples."
        )
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "2.1",
                "source": "2.1 Refusals",
                "translated": "2.1 拒絕",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "2.1",
                "source": long_source,
                "translated": "LLMs 經過訓練，旨在遵守良性使用者請求，但拒絕回應被視為不安全或有害的提示，此訓練透過 RLHF 和偏好對齊 (",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn(long_source, markdown)
        self.assertNotIn("偏好對齊 (", markdown)

    def test_build_study_version_formats_front_matter_and_strips_leakage_prefix(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": "LLMs 是稱職的安全代理人，還是一個宣傳機器？",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "title",
                "source": "Neemesh Yadav1*, Francesco Ortu2,3*",
                "translated": "Neemesh Yadav1*, Francesco Ortu2,3*",
                "meta": {},
            },
            {
                "block_id": "b3",
                "type": "paragraph",
                "section": "title",
                "source": "CMU\nUniversity of Toronto",
                "translated": "CMU\nUniversity of Toronto",
                "meta": {},
            },
            {
                "block_id": "b4",
                "type": "paragraph",
                "section": "title",
                "source": "neemeshy@smu.edu.sg",
                "translated": "neemeshy@smu.edu.sg",
                "meta": {},
            },
            {
                "block_id": "b5",
                "type": "paragraph",
                "section": "1",
                "source": "Body paragraph.",
                "translated": "以下是修復後的繁體中文翻譯：\n\n這是正文。",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn("# LLMs 是稱職的安全代理人，還是一個宣傳機器？", markdown)
        self.assertIn("Authors: Neemesh Yadav1*, Francesco Ortu2,3*", markdown)
        self.assertIn("Affiliations:\n- CMU\n- University of Toronto", markdown)
        self.assertIn("Emails: neemeshy@smu.edu.sg", markdown)

    def test_build_study_version_skips_unknown_metadata_noise_block(self) -> None:
        blocks = [
            {"block_id": "b1", "type": "heading", "section": "1", "source": "1 Introduction", "translated": "1 緒論", "meta": {}},
            {"block_id": "b2", "type": "unknown", "section": "1", "source": "*Equal contribution", "translated": "*Equal contribution", "meta": {}},
            {"block_id": "b3", "type": "paragraph", "section": "1", "source": "Body paragraph.", "translated": "這是正文。", "meta": {}},
        ]
        markdown = build_study_version(blocks)
        self.assertNotIn("*Equal contribution", markdown)
        self.assertIn("這是正文。", markdown)

    def test_build_study_version_front_matter_keeps_numbered_affiliations_together(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Title",
                "translated": "標題",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "title",
                "source": "Author A, 1. SMU 2. University of Trieste 6. Vector Institute a@example.com",
                "translated": "Author A...",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn("- 1. SMU", markdown)
        self.assertIn("- 2. University of Trieste", markdown)
        self.assertIn("- 6. Vector Institute", markdown)

    def test_build_study_version_front_matter_splits_space_numbered_affiliations(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Title",
                "translated": "標題",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "title",
                "source": "Author A, 1 SMU 2 University of Trieste 6 Vector Institute a@example.com",
                "translated": "Author A...",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn("- 1 SMU", markdown)
        self.assertIn("- 2 University of Trieste", markdown)
        self.assertIn("- 6 Vector Institute", markdown)

    def test_build_study_version_parses_mixed_front_matter_line(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": "LLMs 是稱職的安全代理人，還是一個宣傳機器？",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "title",
                "source": "Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6, Bernhard Schölkopf7, Rada Mihalcea8, CMU University of Toronto University of Michigan 1. SMU 2. University of Trieste 6. Vector Institute neemeshy@smu.edu.sg francesco.ortu@phd.units.it",
                "translated": "尼梅什 Yadav1*、法蘭切斯科 Ortu2,3*...",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn("Authors: Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6, Bernhard Schölkopf7, Rada Mihalcea8", markdown)
        self.assertIn("Affiliations:", markdown)
        self.assertIn("Emails: neemeshy@smu.edu.sg francesco.ortu@phd.units.it", markdown)

    def test_build_study_version_prefers_multiline_translated_front_matter(self) -> None:
        blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": "LLMs 是稱職的安全代理人，還是一個宣傳機器？",
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "paragraph",
                "section": "title",
                "source": "Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6, Bernhard Schölkopf7, Rada Mihalcea8, Alberto Cazzaniga3, Zhijing Jin5,6,7 3AREA Science Park 7MPI for Intelligent Systems 4CMU 5University of Toronto 8University of Michigan 1SMU 2University of Trieste 6Vector Institute neemeshy@smu.edu.sg francesco.ortu@phd.units.it jiarui@cmu.edu zjin@cs.toronto.edu",
                "translated": "Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6, Bernhard Schölkopf7, Rada Mihalcea8, Alberto Cazzaniga3, Zhijing Jin5,6,7\n1 SMU\n2 的里雅斯特大學\n3 AREA 科學園區\n4 卡內基美隆大學\n5 多倫多大學\n6 向量研究所\n7 馬克斯普朗克智慧型系統\n8 密西根大學\nneemeshy@smu.edu.sg francesco.ortu@phd.units.it jiarui@cmu.edu zjin@cs.toronto.edu",
                "meta": {},
            },
        ]
        markdown = build_study_version(blocks)
        self.assertIn("Authors: Neemesh Yadav1*, Francesco Ortu2,3*, Jiarui Liu4, Joeun Yook5, 6, Bernhard Schölkopf7, Rada Mihalcea8, Alberto Cazzaniga3, Zhijing Jin5,6,7", markdown)
        self.assertIn("Affiliations:\n- 1 SMU\n- 2 的里雅斯特大學\n- 3 AREA 科學園區", markdown)
        self.assertIn("- 8 密西根大學", markdown)
        self.assertIn("Emails: neemeshy@smu.edu.sg francesco.ortu@phd.units.it jiarui@cmu.edu zjin@cs.toronto.edu", markdown)

    def test_run_writes_markdown_file(self) -> None:
        sample_blocks = [
            {
                "block_id": "b1",
                "type": "heading",
                "section": "title",
                "source": "Are LLMs Good Safety Agents or a Propaganda Engine?",
                "translated": None,
                "meta": {},
            },
            {
                "block_id": "b2",
                "type": "heading",
                "section": "1",
                "source": "1 Introduction",
                "translated": None,
                "meta": {},
            },
            {
                "block_id": "b3",
                "type": "paragraph",
                "section": "1",
                "source": "Intro paragraph.",
                "translated": "這是導論段落。",
                "meta": {},
            },
            {
                "block_id": "b4",
                "type": "heading",
                "section": "references",
                "source": "References",
                "translated": None,
                "meta": {},
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "translated_blocks.qwen.jsonl"
            output_path = Path(tmpdir) / "paper.zh-TW.md"
            with input_path.open("w", encoding="utf-8") as handle:
                for block in sample_blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")

            result = run(input_path, output_path)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("# LLM 是優秀的安全代理，還是宣傳引擎？", content)
            self.assertIn("## 1 導論", content)
            self.assertIn("這是導論段落。", content)
            self.assertIn("## 參考文獻", content)


if __name__ == "__main__":
    unittest.main()
