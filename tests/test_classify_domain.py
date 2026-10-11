import unittest

from skills.classify_domain.run import PURPOSE_LABEL_KEYS, derive_primary, derive_secondaries


def fit(domain, importance, specificity, role="method"):
    return {"domain": domain, "importance": importance, "specificity": specificity, "role": role, "reason": ""}


FITS = [
    fit("Public Health", 5, 3, "outcome"),
    fit("Emergency Management", 5, 4),
    fit("Heat Health Action Planning", 5, 5, "outcome"),
    fit("Data Protection", 4, 4, "constraint"),
    fit("Occupational Health", 3, 4, "constraint"),
]


class ClassifyDomainTest(unittest.TestCase):
    def test_secondaries_in_document_order(self):
        self.assertEqual(derive_secondaries(FITS, "Heat Health Action Planning"),
                         ["Public Health", "Emergency Management", "Data Protection"])

    def test_primary_fallback_prefers_specific_outcome(self):
        self.assertEqual(derive_primary(FITS), "Heat Health Action Planning")

    def test_purpose_tags_are_not_domains(self):
        for tag in ("business", "business_for_profit", "business_non_profit", "business_other", "non-profit"):
            self.assertIn(tag, PURPOSE_LABEL_KEYS)


if __name__ == "__main__":
    unittest.main()
