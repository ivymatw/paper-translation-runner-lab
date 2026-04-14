from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.repair import detect_suspicious_blocks, repair_blocks, run


class FakeRepairClient:
    def repair(self, *, source: str, draft: str, block_type: str, section: str) -> str:
        return f"修復：{source}"


class FlakyRepairClient:
    def __init__(self) -> None:
        self.calls = 0

    def repair(self, *, source: str, draft: str, block_type: str, section: str) -> str:
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("temporary unavailable")
        return f"修復：{source}"


class RepairTests(unittest.TestCase):
    def test_detect_suspicious_blocks_flags_translation_error_and_protected_residue(self) -> None:
        blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "1", "source": "Alpha.", "translated": "[TRANSLATION_ERROR:b1__c000]\nAlpha."},
            {"block_id": "b2", "type": "paragraph", "section": "1", "source": "Beta.", "translated": "這裡殘留 §PROTECTED_0§ placeholder。"},
            {"block_id": "b3", "type": "paragraph", "section": "1", "source": "Gamma.", "translated": "這是一段正常中文。"},
        ]
        flagged = detect_suspicious_blocks(blocks)
        self.assertEqual([block["block_id"] for block in flagged], ["b1", "b2"])

    def test_repair_blocks_only_repairs_flagged_blocks(self) -> None:
        blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "1", "source": "Alpha.", "translated": "[TRANSLATION_ERROR:b1__c000]\nAlpha."},
            {"block_id": "b2", "type": "paragraph", "section": "1", "source": "Beta.", "translated": "這是一段正常中文。"},
        ]
        repaired = repair_blocks(blocks, FakeRepairClient())
        self.assertEqual(repaired[0]["translated"], "修復：Alpha.")
        self.assertEqual(repaired[1]["translated"], "這是一段正常中文。")

    def test_detect_suspicious_blocks_flags_truncated_paragraph(self) -> None:
        source = (
            "LLMs are trained to obey benign user requests but refuse prompts that are deemed unsafe or harmful through RLHF "
            "and preference alignment. Following the literature, we categorize several kinds of refusal with examples."
        )
        blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "2.1", "source": source, "translated": "大型語言模型經過訓練，旨在遵守良性使用者請求，但拒絕回應被視為不安全或有害的提示，此訓練透過 RLHF 和偏好對齊 ("},
            {"block_id": "b2", "type": "paragraph", "section": "2.1", "source": source, "translated": "這是一段較完整的中文翻譯，保留了原文主要內容並有完整句號。"},
        ]
        flagged = detect_suspicious_blocks(blocks)
        self.assertEqual([block["block_id"] for block in flagged], ["b1"])

    def test_detect_suspicious_blocks_does_not_flag_citation_heavy_but_complete_translation(self) -> None:
        source = (
            "Censorship has historically been enforced through direct control of media, education, and public discourse "
            "(Cox, 1979). In the digital age, this often manifests as platform moderation, information suppression, "
            "or content manipulation by governing authorities (Shadmehr and Bernhardt, 2015; Chaabane et al., 2014)."
        )
        translated = (
            "審查制度歷史上是透過直接控制媒體、教育和公共論述來實施的 (Cox, 1979)。在數位時代，這通常表現為政府當局對平台進行審核、"
            "資訊壓制或內容操縱 (Shadmehr and Bernhardt, 2015; Chaabane et al., 2014)。"
        )
        blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "1", "source": source, "translated": translated},
        ]
        flagged = detect_suspicious_blocks(blocks)
        self.assertEqual(flagged, [])

    def test_repair_blocks_retries_temporary_failures(self) -> None:
        blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "1", "source": "Alpha.", "translated": "[TRANSLATION_ERROR:b1__c000]\nAlpha."},
        ]
        repaired = repair_blocks(blocks, FlakyRepairClient())
        self.assertEqual(repaired[0]["translated"], "修復：Alpha.")

    def test_run_writes_repaired_jsonl(self) -> None:
        sample_blocks = [
            {"block_id": "b1", "type": "paragraph", "section": "1", "source": "Alpha.", "translated": "[TRANSLATION_ERROR:b1__c000]\nAlpha."},
            {"block_id": "b2", "type": "paragraph", "section": "1", "source": "Beta.", "translated": "這是一段正常中文。"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "translated_blocks.gemini.jsonl"
            output_path = Path(tmpdir) / "translated_blocks.repaired.gemini.jsonl"
            with input_path.open("w", encoding="utf-8") as handle:
                for block in sample_blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")

            result = run(input_path, output_path, client=FakeRepairClient())
            self.assertEqual(result, output_path)
            parsed = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(parsed[0]["translated"], "修復：Alpha.")
            self.assertEqual(parsed[1]["translated"], "這是一段正常中文。")


if __name__ == "__main__":
    unittest.main()
