import json
import unittest
from pathlib import Path

from planexe_skill.shared.purpose import PROFIT_MOTIVES, PROMPT_VARIANTS, PURPOSES, prompt_variant

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# Skills that pick a system prompt per purpose variant, and the file name pattern they use.
PER_VARIANT_PROMPTS = {
    "swot_analysis": "prompts/{}.md",
    "identify_documents": "prompts/{}.md",
    "filter_documents_to_create": "prompts/{}.md",
    "filter_documents_to_find": "prompts/{}.md",
    "draft_documents_to_create": "prompts/{}.md",
    "draft_documents_to_find": "prompts/{}.md",
    "classify_domain": "prompts/system_{}.md",
}


def schema() -> dict:
    return json.loads((SKILLS / "identify_purpose" / "schema.json").read_text())


class PurposeTest(unittest.TestCase):
    def test_purposes_match_schema(self):
        self.assertEqual(sorted(PURPOSES), sorted(schema()["properties"]["purpose"]["enum"]))

    def test_schema_requires_profit_motive(self):
        self.assertEqual(sorted(PROFIT_MOTIVES), sorted(schema()["properties"]["profit_motive"]["enum"]))
        self.assertIn("profit_motive", schema()["required"])

    def test_prompt_variant(self):
        def variant(purpose, motive=None):
            d = {"purpose": purpose} if motive is None else {"purpose": purpose, "profit_motive": motive}
            return prompt_variant(d, "x")
        self.assertEqual(variant("business", "for_profit"), "business_for_profit")
        self.assertEqual(variant("business", "non_profit"), "business_non_profit")
        self.assertEqual(variant("business", "other"), "business_other")
        self.assertEqual(variant("business"), "business_for_profit")
        self.assertEqual(variant("personal", "other"), "personal")
        self.assertEqual(variant("other", "non_profit"), "other")
        with self.assertRaises(ValueError):
            variant("public_good")

    def test_every_variant_has_a_prompt(self):
        for skill, pattern in PER_VARIANT_PROMPTS.items():
            for variant in PROMPT_VARIANTS:
                with self.subTest(skill=skill, variant=variant):
                    self.assertTrue((SKILLS / skill / pattern.format(variant)).is_file())

    def test_classify_domain_drops_every_purpose_label(self):
        from skills.classify_domain.run import PURPOSE_LABEL_KEYS
        self.assertTrue(set(PURPOSES) | set(PROMPT_VARIANTS) <= PURPOSE_LABEL_KEYS)

    def test_profit_motive_markdown(self):
        from skills.identify_purpose.run import to_markdown

        def md(motive):
            return to_markdown({"purpose": "business", "profit_motive": motive, "purpose_detailed": "d", "topic": "t"})
        self.assertTrue(md("non_profit").startswith("**Purpose:** business, non-profit."))
        self.assertTrue(md("other").startswith("**Purpose:** business, neither for profit nor non-profit"))
        self.assertTrue(md("for_profit").startswith("**Purpose:** business\n"))

    def test_swot_killer_app_is_decided_per_plan(self):
        for variant in ("business_for_profit", "business_non_profit", "business_other"):
            text = (SKILLS / "swot_analysis" / "prompts" / f"{variant}.md").read_text()
            with self.subTest(variant=variant):
                self.assertNotIn("Include “killer application”", text)
                self.assertIn("Decide from the plan itself whether a “killer application” is relevant", text)


if __name__ == "__main__":
    unittest.main()
