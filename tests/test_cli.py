import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from planexe_skill.cli import dated_run_dir, main


class DatedRunDirTest(unittest.TestCase):
    def test_prefix(self):
        day = datetime(2026, 10, 8)
        self.assertEqual(dated_run_dir(Path("runs/cross_border_rail"), day), Path("runs/20261008_cross_border_rail"))
        self.assertEqual(dated_run_dir(Path("runs/20250720_faraday"), day), Path("runs/20250720_faraday"))
        self.assertEqual(dated_run_dir(Path("plan"), day), Path("20261008_plan"))

    def test_create_uses_dated_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "p.txt"
            prompt.write_text("Plan a bakery in Lyon.")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["create", f"{tmp}/bakery", "--prompt-file", str(prompt)]), 0)
                self.assertEqual(main(["create", f"{tmp}/plain", "--prompt-file", str(prompt), "--no-date-prefix"]), 0)
            names = sorted(p.name for p in Path(tmp).iterdir() if p.is_dir())
            self.assertEqual(names, [f"{datetime.now():%Y%m%d}_bakery", "plain"])


if __name__ == "__main__":
    unittest.main()
