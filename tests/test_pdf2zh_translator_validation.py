import unittest

from pdf2zh.translator import validate_translation_output


class Pdf2ZhTranslatorValidationTests(unittest.TestCase):
    def test_allows_english_terms_already_present_in_source(self):
        source = (
            "Nina Panickssery. 2023. Steering llama 2 via contrastive activation addition. "
            "arXiv preprint arXiv:2312.06681."
        )
        translated = (
            "Nina Panickssery。2023。Steering llama 2 via contrastive activation addition。"
            "arXiv 預印本。"
        )

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_pdf_linebreak_fragments_from_source(self):
        source = "Can you answer questions about topics extracted from prompt?"
        translated = "你可以回答關於 topics ex- tracted from prompt 的問題嗎？"

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_reference_entries_with_source_english_names(self):
        source = (
            "OpenAI. 2024. Gpt-4o. Nina Panickssery, Nick Gabrieli, Julian Schulz. "
            "Steering llama 2 via contrastive activation addition."
        )
        translated = (
            "OpenAI. 2024. Gpt-4o. Nina Panickssery, Nick Gabrieli, Julian Schulz. "
            "透過對比激活添加操控 llama 2。"
        )

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_placeholder_with_internal_spaces(self):
        source = "Equation {v0} shows the result."
        translated = "方程式 { v0 } 顯示結果。"

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_reference_placeholders_replaced_by_explicit_reference_text(self):
        source = (
            "Yejin Bang et al. 2024. Measuring political bias. "
            "In Proceedingsofthe62ndAnnualMeetingoftheAs- {v0} {v1} {v2}, pages 11142–11159."
        )
        translated = (
            "Yejin Bang et al. 2024. 測量政治偏見。"
            "In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics, "
            "pages 11142–11159."
        )

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_placeholder_reordering_when_set_matches(self):
        source = "24{v4}24 ... cosine {v5}0.95 at layers 12{v6} ... ({v7}0.95)."
        translated = "24{v4}24……第12層{v6}處的相似度達到{v5}0.95……（{v7}0.95）。"

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_allows_chat_role_placeholder_to_be_dropped_in_refusal(self):
        source = "User{v13} Explain Tiananmen Square 1989."
        translated = "很抱歉，我無法翻譯此內容。"

        ok, reason = validate_translation_output(source, translated)

        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_still_flags_truly_dangling_placeholder(self):
        source = "Equation {v0} shows the result."
        translated = "方程式 {v 顯示結果。"

        ok, reason = validate_translation_output(source, translated)

        self.assertFalse(ok)
        self.assertEqual(reason, "dangling_placeholder")

    def test_still_flags_unexpected_english_leakage(self):
        source = "這是一段完全中文的來源文本。"
        translated = "這是一段翻譯，但 unexpectedly retains large english fragments for no reason。"

        ok, reason = validate_translation_output(source, translated)

        self.assertFalse(ok)
        self.assertTrue(reason.startswith("suspicious_english:"))


if __name__ == "__main__":
    unittest.main()
