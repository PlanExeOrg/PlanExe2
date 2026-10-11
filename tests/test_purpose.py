import json
import unittest
from pathlib import Path

from planexe_skill.shared.purpose import ADDENDA, PROFIT_MOTIVES, PURPOSES, addendum, check_purpose
from planexe_skill.skill import load_skills

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
PURPOSE_MODULE = "planexe_skill/shared/purpose.py"
PURPOSE_IMPORT = "planexe_skill.shared.purpose"

# Prompt file name pattern per skill; every purpose-aware skill uses "prompts/{}.md".
PROMPT_PATTERN: dict[str, str] = {}


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

    def test_base_prompt_and_addendum(self):
        def d(purpose, motive=None):
            return {"purpose": purpose} if motive is None else {"purpose": purpose, "profit_motive": motive}
        for motive in (None, "for_profit", "non_profit", "other"):
            self.assertEqual(check_purpose(d("business", motive), "x"), "business")
        self.assertIsNone(addendum(d("business", "for_profit")))
        self.assertIsNone(addendum(d("business")))
        self.assertEqual(addendum(d("business", "non_profit")), "business_non_profit")
        self.assertEqual(addendum(d("business", "other")), "business_other")
        self.assertIsNone(addendum(d("personal", "other")))
        self.assertIsNone(addendum(d("other", "non_profit")))
        with self.assertRaises(ValueError):
            check_purpose(d("public_good"), "x")

    def test_purpose_users_declare_it(self):
        # `uses:` feeds the dirtiness hash, and the prompt-file test below relies on it.
        self.assertEqual(skills_declaring_purpose(), skills_importing_purpose())

    def test_every_variant_has_a_prompt(self):
        skills = skills_declaring_purpose()
        self.assertGreaterEqual(len(skills), 6)
        for skill in sorted(skills):
            pattern = PROMPT_PATTERN.get(skill, "prompts/{}.md")
            for name in list(PURPOSES) + [f"{a}_addendum" for a in ADDENDA]:
                with self.subTest(skill=skill, prompt=name):
                    self.assertTrue((SKILLS / skill / pattern.format(name)).is_file())

    def test_classify_domain_drops_every_purpose_label(self):
        from skills.classify_domain.run import PURPOSE_LABEL_KEYS
        self.assertTrue(set(PURPOSES) | set(ADDENDA) | {"business_for_profit"} <= PURPOSE_LABEL_KEYS)

    def test_profit_motive_markdown(self):
        from skills.identify_purpose.run import to_markdown

        def md(motive):
            return to_markdown({"purpose": "business", "profit_motive": motive, "purpose_detailed": "d", "topic": "t"})
        for motive in ("for_profit", "non_profit", "other"):  # downstream sees plain "business", as in PlanExe
            self.assertTrue(md(motive).startswith("**Purpose:** business\n"), motive)

    def test_swot_killer_app_is_decided_per_plan(self):
        text = (SKILLS / "swot_analysis" / "prompts" / "business.md").read_text()
        self.assertNotIn("Include “killer application”", text)
        self.assertIn("Decide from the plan itself whether a “killer application” is relevant", text)


if __name__ == "__main__":
    unittest.main()
