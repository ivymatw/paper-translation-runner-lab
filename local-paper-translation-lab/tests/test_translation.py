from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.translate import MAX_RETRIES, GeminiTranslationClient, build_single_prompt, is_likely_truncated_translation, join_translated_parts, protect_text, restore_text, run, split_text_for_translation, translate_blocks


class FakeTranslationClient:
    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        translated: dict[str, str] = {}
        for block_id, text in items.items():
            translated[block_id] = f"繁中：{text}"
        return translated


class FlakyTranslationClient:
    def __init__(self) -> None:
        self.calls = 0

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        self.calls += 1
        if self.calls <= MAX_RETRIES:
            raise Exception('simulated failure')
        return {k: f'繁中：{v}' for k, v in items.items()}


class CountingTranslationClient:
    def __init__(self) -> None:
        self.calls = 0

    def translate_batch(self, items: dict[str, str]) -> dict[str, str]:
        self.calls += 1
        return {k: f'完整翻譯：{v}' for k, v in items.items()}


class TranslationTests(unittest.TestCase):
    def test_gemini_client_requires_api_key(self) -> None:
        import os
        old = os.environ.pop('GEMINI_API_KEY', None)
        try:
            with self.assertRaises(Exception):
                GeminiTranslationClient(model='gemini-2.5-flash', api_key=None)
        finally:
            if old is not None:
                os.environ['GEMINI_API_KEY'] = old

    def test_split_text_for_translation_splits_long_text(self) -> None:
        source = "Sentence one. " + "Sentence two is quite long and informative. " * 30
        chunks = split_text_for_translation(source, max_chars=120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))

    def test_protected_content_round_trips(self) -> None:
        source = "Contact foo@example.com about GPT-4o at https://example.com and use `pip install x`."
        masked, replacements = protect_text(source)
        self.assertIn("§PROTECTED_0§", masked)
        restored = restore_text(f"繁中：{masked}", replacements)
        self.assertIn("foo@example.com", restored)
        self.assertIn("https://example.com", restored)
        self.assertIn("GPT-4o", restored)
        self.assertIn("`pip install x`", restored)

    def test_protect_text_does_not_mask_common_academic_acronyms_or_simple_terms(self) -> None:
        source = "Large Language Models (LLMs) use PSP and PIAs in a data-driven representation-level analysis."
        masked, replacements = protect_text(source)
        self.assertIn("LLMs", masked)
        self.assertIn("PSP", masked)
        self.assertIn("PIAs", masked)
        self.assertIn("data-driven", masked)
        self.assertIn("representation-level", masked)
        self.assertEqual(replacements, {})

    def test_translate_blocks_translates_only_heading_and_paragraph(self) -> None:
        blocks = [
            {"block_id": "b000001", "type": "heading", "section": "1", "source": "1 Introduction", "translated": None, "meta": {}},
            {"block_id": "b000002", "type": "paragraph", "section": "1", "source": "Visit https://example.com with GPT-4o.", "translated": None, "meta": {}},
            {"block_id": "b000003", "type": "equation", "section": "1", "source": "r = f(x)", "translated": None, "meta": {}},
            {"block_id": "b000004", "type": "code", "section": "1", "source": "print('hello')", "translated": None, "meta": {}},
        ]

        translated = translate_blocks(blocks, FakeTranslationClient(), batch_size=2, char_budget=200)

        self.assertEqual(len(translated), len(blocks))
        self.assertEqual(translated[0]["translated"], "繁中：1 Introduction")
        self.assertEqual(translated[1]["translated"], "繁中：Visit https://example.com with GPT-4o.")
        self.assertEqual(translated[2]["translated"], "r = f(x)")
        self.assertEqual(translated[3]["translated"], "print('hello')")

    def test_translate_blocks_falls_back_after_retries(self) -> None:
        blocks = [
            {"block_id": "b000001", "type": "paragraph", "section": "1", "source": "A fairly long paragraph for retry handling.", "translated": None, "meta": {}},
        ]
        translated = translate_blocks(blocks, FlakyTranslationClient(), batch_size=1, char_budget=50)
        self.assertIn('[TRANSLATION_ERROR:', translated[0]['translated'])

    def test_build_single_prompt_includes_block_context(self) -> None:
        prompt = build_single_prompt(
            "Figure 2: A caption.",
            block_type="figure_caption",
            section="3.2",
            chunk_index=0,
            chunk_total=1,
            glossary_entries=[
                {"term": "prompt injection attacks", "policy": "canonical_translation", "translation_zh_tw": "提示注入攻擊"},
                {"term": "LLMs", "policy": "preserve"},
            ],
        )
        self.assertIn("Block type: figure_caption", prompt)
        self.assertIn("Section: 3.2", prompt)
        self.assertIn("Glossary guidance:", prompt)
        self.assertIn("prompt injection attacks => 提示注入攻擊", prompt)
        self.assertIn("LLMs => preserve English", prompt)
        self.assertIn("Passage:", prompt)

    def test_strip_repair_meta_text_removes_leakage_prefixes(self) -> None:
        from src.translate import strip_repair_meta_text
        cleaned = strip_repair_meta_text("以下是修復後的繁體中文翻譯：\n\n這是正文。")
        self.assertEqual(cleaned, "這是正文。")

    def test_join_translated_parts_preserves_single_paragraph_flow(self) -> None:
        joined = join_translated_parts([
            "這是第一句。",
            "這是第二句。",
            "這是第三句。",
        ])
        self.assertEqual(joined, "這是第一句。 這是第二句。 這是第三句。")

    def test_is_likely_truncated_translation_flags_short_incomplete_paragraph(self) -> None:
        source = (
            "LLMs are trained to obey benign user requests but refuse prompts that are deemed unsafe or harmful "
            "through RLHF and preference alignment (Bai et al., 2022a). Following Wen et al. (2025a)’s taxonomy "
            "of abstentions, we categorize model responses into four kinds of refusals, with multiple examples and "
            "detailed distinctions."
        )
        translated = "大型語言模型經過訓練，旨在遵守良性使用者請求，但拒絕回應被視為不安全或有害的提示，此訓練透過 RLHF 和偏好對齊 ("
        self.assertTrue(is_likely_truncated_translation(source, translated, block_type="paragraph"))

    def test_run_retranslates_existing_truncated_output(self) -> None:
        sample_blocks = [
            {
                "block_id": "b000001",
                "type": "paragraph",
                "section": "1",
                "source": (
                    "Censorship has historically been enforced through direct control of media, education, and public discourse. "
                    "In the digital age, this often manifests as platform moderation, information suppression, or content manipulation. "
                    "More recently, large language models have emerged as a subtler mechanism."
                ),
                "translated": None,
                "meta": {"line_start": 1, "line_end": 1},
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "blocks.jsonl"
            output_path = Path(tmpdir) / "translated_blocks.jsonl"
            with input_path.open("w", encoding="utf-8") as handle:
                for block in sample_blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            stale = dict(sample_blocks[0])
            stale["translated"] = "歷史上，審查制度一直透過直接控制媒體、教育和公共論述來執行 ("
            output_path.write_text(json.dumps(stale, ensure_ascii=False) + "\n", encoding="utf-8")

            client = CountingTranslationClient()
            result = run(input_path, output_path, client=client, batch_size=1, char_budget=1000)
            self.assertEqual(result, output_path)
            self.assertGreater(client.calls, 0)
            parsed = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(parsed[0]["translated"].startswith("完整翻譯："))

    def test_run_writes_same_block_count_jsonl(self) -> None:
        sample_blocks = [
            {"block_id": "b000001", "type": "heading", "section": "title", "source": "Abstract", "translated": None, "meta": {"line_start": 1, "line_end": 1}},
            {"block_id": "b000002", "type": "paragraph", "section": "abstract", "source": "Large Language Models are useful.", "translated": None, "meta": {"line_start": 2, "line_end": 2}},
            {"block_id": "b000003", "type": "figure", "section": "abstract", "source": "Figure 1: A diagram.", "translated": None, "meta": {"line_start": 3, "line_end": 3}},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "blocks.jsonl"
            output_path = Path(tmpdir) / "translated_blocks.jsonl"
            with input_path.open("w", encoding="utf-8") as handle:
                for block in sample_blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")

            result = run(input_path, output_path, client=FakeTranslationClient(), batch_size=2, char_budget=200)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.exists())

            lines = output_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), len(sample_blocks))
            parsed = [json.loads(line) for line in lines]
            self.assertEqual(parsed[0]["translated"], "繁中：Abstract")
            self.assertEqual(parsed[1]["translated"], "繁中：Large Language Models are useful.")
            self.assertEqual(parsed[2]["translated"], "Figure 1: A diagram.")


if __name__ == "__main__":
    unittest.main()
