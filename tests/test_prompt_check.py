import json
import tempfile
import unittest
from pathlib import Path

from planexe_skill.cli import create_run_dir
from planexe_skill.llm.fake import FakeBackend
from planexe_skill.prompt_check import check_prompt, format_result


class PromptCheckTest(unittest.TestCase):
    def test_check_and_format(self):
        def responder(system, user, schema, tier):
            self.assertEqual(tier, "mid")
            return {"verdict": "USABLE", "verdict_reason": "ok", "ready": False,
                    "dimensions": [{"name": "location", "status": "missing", "note": "no city"}],
                    "questions": [{"question": "Where?", "suggestions": ["Lyon", "Paris"]}]}
        r = check_prompt("make me a restaurant", FakeBackend(responder))
        self.assertEqual(r["word_count"], 4)
        text = format_result(r)
        self.assertIn("✗ location", text)
        self.assertIn("NO, refine first", text)
        self.assertIn("Lyon | Paris", text)

    def test_create_with_start_date(self):
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "r"
            create_run_dir(run, prompt="p", start=datetime.fromisoformat("2030-02-01"))
            self.assertEqual(json.loads((run / "plan_raw.json").read_text())["pretty_date"], "2030-Feb-01")
            self.assertTrue(json.loads((run / "start_time.json").read_text())["server_iso_utc"].startswith("20"))


if __name__ == "__main__":
    unittest.main()
