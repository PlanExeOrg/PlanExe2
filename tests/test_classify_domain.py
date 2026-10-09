import unittest

from skills.classify_domain.run import derive_primary, derive_secondaries


def fit(domain, importance, specificity, role="method"):
    return {"domain": domain, "importance": importance, "specificity": specificity, "role": role, "reason": ""}


FITS = [
    fit("Public Health", 5, 3, "outcome"),
    fit("Emergency Management", 5, 4),
    fit("Heat-Health Action Planning", 5, 5, "outcome"),
    fit("Data Protection", 4, 4, "constraint"),
    fit("Occupational Health", 3, 4, "constraint"),
]


class SecondariesTest(unittest.TestCase):
    def test_picks_first_then_ranked(self):
        self.assertEqual(derive_secondaries(FITS, "Heat-Health Action Planning", [4]),
                         ["Occupational Health", "Emergency Management", "Data Protection"])

    def test_invalid_picks_fall_back_to_ranking(self):
        # out of range, the primary itself, a duplicate: all ignored
        self.assertEqual(derive_secondaries(FITS, "Heat-Health Action Planning", [9, 2, -1]),
                         ["Emergency Management", "Data Protection", "Public Health"])
        self.assertEqual(derive_secondaries(FITS, "Heat-Health Action Planning"),
                         ["Emergency Management", "Data Protection", "Public Health"])

    def test_primary_fallback_prefers_specific_outcome(self):
        self.assertEqual(derive_primary(FITS), "Heat-Health Action Planning")


if __name__ == "__main__":
    unittest.main()
