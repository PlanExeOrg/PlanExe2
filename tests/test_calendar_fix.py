import unittest
from datetime import date

from planexe_skill.calendar_fix import add_months, fix_text, fix_value, offset_date

START = date(2026, 5, 2)


def fix(s: str, annotate: bool = False) -> str:
    return fix_text(s, START, annotate)[0]


class CalendarFixTest(unittest.TestCase):
    def test_add_months(self):
        self.assertEqual(add_months(START, 72), date(2032, 5, 2))
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(offset_date(START, 3.5), date(2026, 8, 17))

    def test_corrects_paired_dates(self):
        cases = {
            "Month 72 (February 2033)": "Month 72 (May 2032)",
            "month 24, April 2028": "month 24, May 2028",
            "Month 3 (2026-07)": "Month 3 (2026-08)",
            "Month 36 (November 30, 2027)": "Month 36 (May 2, 2029)",
            "Month 18 (Jan 2027)": "Month 18 (Nov 2027)",
            "by Month 6 (November 2026)": "by Month 6 (November 2026)",
            "month 18 = May 15, 2028": "month 18 = November 2, 2027",
            "month 24 gate (April 2028)": "month 24 gate (May 2028)",
            "July 2, 2026 (month 3)": "August 2, 2026 (month 3)",
            "August 2026, month 4": "September 2026, month 4",
            "month 3.5 (mid-July 2026)": "month 3.5 (2026-08-17)",
            "month 18 = May 15, 2028; month 36 = November 15, 2028":
                "month 18 = November 2, 2027; month 36 = May 2, 2029",
        }
        for src, want in cases.items():
            self.assertEqual(fix(src), want, src)

    def test_annotates_bare_offsets(self):
        self.assertEqual(fix("Lock the protocol by Month 3.", True), "Lock the protocol by Month 3 (2026-08-02).")
        self.assertEqual(fix("Months 48–72: verification", True), "Months 48–72 (2030-05-02 to 2032-05-02): verification")
        self.assertEqual(fix("Month 72 (May 2032)", True), "Month 72 (May 2032)")  # already dated: unchanged
        self.assertEqual(fix("gates at months 18, 36, 54, 72.", True),
                         "gates at months 18, 36, 54, 72 (2027-11-02, 2029-05-02, 2030-11-02, 2032-05-02).")
        self.assertEqual(fix("in month 9–12", True), "in month 9–12 (2027-02-02 to 2027-05-02)")
        self.assertEqual(fix("(down-select at month 24, then scale)", True),
                         "(down-select at month 24 = 2028-05-02, then scale)")
        self.assertEqual(fix("Months 48–72 (through February 2033): verify", True),
                         "Months 48–72 (2030-05-02 to 2032-05-02): verify")
        self.assertEqual(fix("gates (Month 0.5, 1, 1.5, 2) met", True),
                         "gates (Month 0.5, 1, 1.5, 2 = 2026-05-17, 2026-06-02, 2026-06-17, 2026-07-02) met")
        self.assertEqual(fix("partner audit at Month 0.5 or 2.", True),
                         "partner audit at Month 0.5 or 2 (2026-05-17, 2026-07-02).")
        self.assertEqual(fix("funding for Month 13+ if needed", True), "funding for Month 13+ if needed")
        for s in ["gates (Month 0.5, 1, 1.5, 2) met", "Month 0.5 or 2.", "Months 48–72: x", "Month 3."]:
            once = fix(s, True)
            self.assertEqual(fix(once, True), once, s)  # idempotent
        once = fix("Month 3", True)
        self.assertEqual(fix(once, True), once)  # idempotent

    def test_leaves_other_text(self):
        for s in ["Months 6-12 (2027)", "in April 2028 we review", "a 3 month review", "Month 999"]:
            self.assertEqual(fix(s), s)

    def test_fix_value_counts(self):
        v, n = fix_value({"a": ["Month 72 (February 2033)", 5], "b": "Month 3 (2026-08)"}, START, annotate=False)
        self.assertEqual(n, 1)
        self.assertEqual(v["a"][0], "Month 72 (May 2032)")



class StartDateTest(unittest.TestCase):
    def test_local_date_wins_over_utc(self):
        import json
        import tempfile
        from pathlib import Path
        from planexe_skill.context import project_start
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            # 00:00 CEST on 2026-10-08 is 22:00 UTC on 2026-10-07; Month 0 is the local date
            (d / "start_time.json").write_text(json.dumps({"server_iso_utc": "2026-10-07T22:00:00Z",
                                                           "server_iso_local": "2026-10-08T00:00:00+02:00"}))
            self.assertEqual(project_start(d), date(2026, 10, 8))
            (d / "start_time.json").write_text(json.dumps({"server_iso_utc": "2026-04-04T10:00:00Z"}))
            self.assertEqual(project_start(d), date(2026, 4, 4))


if __name__ == "__main__":
    unittest.main()
