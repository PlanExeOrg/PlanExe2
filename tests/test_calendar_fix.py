import unittest
from datetime import date

from planexe_skill.calendar_fix import add_months, fix_text, fix_value

START = date(2026, 5, 2)


class CalendarFixTest(unittest.TestCase):
    def test_add_months(self):
        self.assertEqual(add_months(START, 72), date(2032, 5, 2))
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_styles(self):
        cases = {
            "Month 72 (February 2033)": "Month 72 (May 2032)",
            "month 24, April 2028": "month 24, May 2028",
            "Month 3 (2026-07)": "Month 3 (2026-08)",
            "Month 36 (November 30, 2027)": "Month 36 (May 2, 2029)",
            "Month 18 (Jan 2027)": "Month 18 (Nov 2027)",
            "by Month 6 (November 2026)": "by Month 6 (November 2026)",
        }
        for src, want in cases.items():
            self.assertEqual(fix_text(src, START)[0], want, src)

    def test_leaves_ranges_and_unpaired_dates(self):
        for s in ["Months 6-12 (2027)", "Month 6–12 (November 2026)", "in April 2028 we review", "Month 3 of testing"]:
            self.assertEqual(fix_text(s, START)[0], s)

    def test_fix_value_counts(self):
        v, n = fix_value({"a": ["Month 72 (February 2033)", 5], "b": "Month 3 (2026-08)"}, START)
        self.assertEqual(n, 1)
        self.assertEqual(v["a"][0], "Month 72 (May 2032)")


if __name__ == "__main__":
    unittest.main()
