import json
import unittest
from pathlib import Path

from planexe_skill.shared.purpose import PROFIT_MOTIVES, PROMPT_VARIANTS, PURPOSES, prompt_variant
from planexe_skill.skill import load_skills

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
PURPOSE_MODULE = "planexe_skill/shared/purpose.py"
PURPOSE_IMPORT = "planexe_skill.shared.purpose"

# Prompt file name pattern per skill; every other variant-using skill uses "prompts/{}.md".
PROMPT_PATTERN = {"classify_domain": "prompts/system_{}.md"}


def skills_declaring_purpose() -> set[str]:
    """Skills whose SKILL.md lists planexe_skill/shared/purpose.py under `uses:`."""
    return {name for name, skill in load_skills(SKILLS).items() if PURPOSE_MODULE in skill.uses}


def skills_importing_purpose() -> set[str]:
    """Skills whose run.py imports purpose.py, directly or through a shared module that imports it."""
    shared = [f"planexe_skill.shared.{p.stem}" for p in (ROOT / "planexe_skill" / "shared").glob("*.py")
              if PURPOSE_IMPORT in p.read_text()]
    modules = [PURPOSE_IMPORT] + shared
    return {name for name, skill in load_skills(SKILLS).items()
            if any(m in (skill.dir / "run.py").read_text() for m in modules)}


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

    def test_purpose_users_declare_it(self):
        # `uses:` feeds the dirtiness hash, and the prompt-file test below relies on it.
        self.assertEqual(skills_declaring_purpose(), skills_importing_purpose())

    def test_every_variant_has_a_prompt(self):
        skills = skills_declaring_purpose()
        self.assertGreaterEqual(len(skills), 7)
        for skill in sorted(skills):
            pattern = PROMPT_PATTERN.get(skill, "prompts/{}.md")
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
