import json
import unittest
from pathlib import Path

from planexe_skill.shared.purpose import PROMPT_VARIANTS, PURPOSES, prompt_variant

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

    def test_schema_requires_non_profit(self):
        self.assertEqual(schema()["properties"]["non_profit"]["type"], "boolean")
        self.assertIn("non_profit", schema()["required"])

    def test_prompt_variant(self):
        self.assertEqual(prompt_variant({"purpose": "business", "non_profit": False}, "x"), "business")
        self.assertEqual(prompt_variant({"purpose": "business", "non_profit": True}, "x"), "business_non_profit")
        self.assertEqual(prompt_variant({"purpose": "business"}, "x"), "business")
        self.assertEqual(prompt_variant({"purpose": "personal", "non_profit": True}, "x"), "personal")
        self.assertEqual(prompt_variant({"purpose": "other", "non_profit": True}, "x"), "other")
        with self.assertRaises(ValueError):
            prompt_variant({"purpose": "public_good"}, "x")

    def test_every_variant_has_a_prompt(self):
        for skill, pattern in PER_VARIANT_PROMPTS.items():
            for variant in PROMPT_VARIANTS:
                with self.subTest(skill=skill, variant=variant):
                    self.assertTrue((SKILLS / skill / pattern.format(variant)).is_file())

    def test_classify_domain_drops_every_purpose_label(self):
        from skills.classify_domain.run import PURPOSE_LABEL_KEYS
        self.assertTrue(set(PROMPT_VARIANTS) <= PURPOSE_LABEL_KEYS)

    def test_non_profit_markdown(self):
        from skills.identify_purpose.run import to_markdown
        md = to_markdown({"purpose": "business", "non_profit": True, "purpose_detailed": "d", "topic": "t"})
        self.assertTrue(md.startswith("**Purpose:** business, non-profit."))
        md = to_markdown({"purpose": "business", "non_profit": False, "purpose_detailed": "d", "topic": "t"})
        self.assertTrue(md.startswith("**Purpose:** business\n"))

    def test_swot_killer_app_is_decided_per_plan(self):
        for variant in ("business", "business_non_profit"):
            text = (SKILLS / "swot_analysis" / "prompts" / f"{variant}.md").read_text()
            with self.subTest(variant=variant):
                self.assertNotIn("Include “killer application”", text)
                self.assertIn("Decide from the plan itself whether a “killer application” is relevant", text)


if __name__ == "__main__":
    unittest.main()
