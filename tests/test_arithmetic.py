import unittest

from planexe_skill.shared.arithmetic import check_text


def results(line: str) -> list[tuple[str, bool]]:
    return [(f.stated, f.ok) for f in check_text("doc.md", line)]


class ArithmeticTest(unittest.TestCase):
    def test_correct_statements_pass(self):
        ok = [
            "The tranches sum to 4.5 + 6.0 + 6.5 + 5.7 + 4.0 = 26.7B.",
            "Revenue: 50,000,000 kg x USD 1.80/kg = USD 90M.",
            "USD 13.33M/yr = 16.67M m3 x USD 0.80/m3 (estimate)",
            "50,000 m3/d / 24 x 8000 = 16.67M m3",
            "EBITDA = 13.33 - 8.33 = USD 5.00M/yr; DSCR = 5.00 / 7.36 = 0.68x",
            "about 18 trips x EUR 30–50 = EUR 540–900/day",
            "8 taxi trips × EUR 40 = EUR 320/day × 15 alert days = EUR 4.8k",
            "EUR 24 × 150k–400k city = EUR 3.6–9.6M annualized",
            "the share is 3.3 / 30 = 11% of the cap",
            "4x10 + 6x6 + 2x8 = 92",
            "0.04 / (1 - 1.04^-20) = 0.07358 x 100 = 7.36",
            "funded from the envelope: about USD 75M/yr x 25 = about USD 1.9B",
            "(6 × 900 MW = 5.4 GW)",
            "surplus 90 - 60-90 = 0-30M",
            "If the fabricator raises the price >10% (EUR 70 unit cost + 10% = EUR 77)",
            "a 20% discount: EUR 150 - 20% = EUR 120",
        ]
        for line in ok:
            r = results(line)
            self.assertTrue(r, f"nothing checked in: {line}")
            self.assertTrue(all(o for _, o in r), f"{line}: {r}")

    def test_wrong_statements_fail(self):
        bad = [
            ("Contingency (€50M–100M contamination + €300M–500M power + €200M–300M retrofit) = €850M–1.4B", "€850M–1.4B"),
            ("Total: 4.5 + 6.0 + 6.5 = 18.5B", "18.5B"),
            ("Staff: 9 x 45k = 450k", "450k"),
            ("the gate needs 750 units × EUR 67 = EUR 30.25k", "30.25k"),
        ]
        for line, stated in bad:
            self.assertIn((stated, False), results(line), line)

    def test_ambiguous_statements_are_skipped(self):
        skipped = [
            "Quarterly reviews (Months 6/12/18/24 = 2026-10-04, 2027-04-04)",
            "Gates at Months 36/84 = Years 3/7",
            "The documents list 200k + 1.3M (400+300+350+250) + 300k reserve = 1.8M",
            "Month 0.5 = 2026-05-18",
            "50 MLD aggregate x 8000 operating hours = 2,083 m3/h x 8000",
        ]
        for line in skipped:
            self.assertTrue(all(o for _, o in results(line)), f"{line}: {results(line)}")

    def test_line_numbers(self):
        f = check_text("doc.md", "intro\n\n| a | 2 + 2 = 5 |\n")
        self.assertEqual([(x.line, x.ok) for x in f], [(3, False)])


if __name__ == "__main__":
    unittest.main()
