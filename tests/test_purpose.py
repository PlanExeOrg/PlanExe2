import json
import unittest
from pathlib import Path

from planexe_skill.shared.documents import PURPOSES

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# Skills that pick a system prompt per purpose, and the file name pattern they use.
PER_PURPOSE_PROMPTS = {
    "swot_analysis": "prompts/{}.md",
    "identify_documents": "prompts/{}.md",
    "filter_documents_to_create": "prompts/{}.md",
    "filter_documents_to_find": "prompts/{}.md",
    "draft_documents_to_create": "prompts/{}.md",
    "draft_documents_to_find": "prompts/{}.md",
    "classify_domain": "prompts/system_{}.md",
}


def schema_purposes() -> list[str]:
    schema = json.loads((SKILLS / "identify_purpose" / "schema.json").read_text())
    return schema["properties"]["purpose"]["enum"]


class PurposeTest(unittest.TestCase):
    def test_documents_purposes_match_schema(self):
        self.assertEqual(sorted(PURPOSES), sorted(schema_purposes()))

    def test_every_purpose_has_a_prompt(self):
        for skill, pattern in PER_PURPOSE_PROMPTS.items():
            for purpose in schema_purposes():
                with self.subTest(skill=skill, purpose=purpose):
                    self.assertTrue((SKILLS / skill / pattern.format(purpose)).is_file())

    def test_classify_domain_drops_every_purpose_label(self):
        from skills.classify_domain.run import PURPOSE_LABEL_KEYS
        self.assertEqual(sorted(PURPOSE_LABEL_KEYS), sorted(schema_purposes()))

    def test_public_good_markdown(self):
        from skills.identify_purpose.run import to_markdown
        md = to_markdown({"purpose": "public_good", "purpose_detailed": "d", "topic": "t"})
        self.assertTrue(md.startswith("**Purpose:** public_good."))

    def test_public_good_swot_has_no_killer_app_instruction(self):
        text = (SKILLS / "swot_analysis" / "prompts" / "public_good.md").read_text()
        self.assertNotIn("Include “killer application”", text)


if __name__ == "__main__":
    unittest.main()
