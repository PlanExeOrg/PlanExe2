"""Report part 1 (the model): decision register markdown, validation status, banners."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(skill: str):
    spec = importlib.util.spec_from_file_location(f"skill_{skill}", ROOT / "skills" / skill / "run.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubCtx:
    def __init__(self, files: dict, provenance: dict | None = None):
        self.files = files
        self.provenance = provenance or {}

    def read_text(self, name):
        v = self.files[name]
        return v if isinstance(v, str) else json.dumps(v)

    def read_json(self, name):
        v = self.files[name]
        return json.loads(v) if isinstance(v, str) else v

    def run_provenance(self):
        return self.provenance


DECISION = {"title": "Plant 2 financing", "question": "Who finances plant 2?", "why_open": "Pitch says financed.",
            "severity": "high", "options": [
                {"option": "OEM co-investment", "consequences": "Needs 4 OEMs by Month 18.", "plan_changes": "pitch"},
                {"option": "Defer", "consequences": "100,000 t/yr slips past Year 12.", "plan_changes": "y12_gate"}],
            "default_if_undecided": "Plant 2 deferred.", "owner": "Board", "decide_by": "Month 18",
            "blocks": "100,000 t/yr step"}
RATIFY = {"lever": "Governance vehicle", "chosen": "Existing host body", "main_alternative": "New treaty body",
          "why_it_matters": "Speed vs legitimacy.", "revisit_by": "Month 12"}


class DecisionRegisterTest(unittest.TestCase):
    def test_markdown(self):
        md = load("decision_register").to_markdown({"decisions": [DECISION], "ratify": [RATIFY], "summary": "One open."})
        self.assertIn("## 1. Plant 2 financing", md)
        self.assertIn("| A. OEM co-investment | Needs 4 OEMs by Month 18. | pitch |", md)
        self.assertIn("**If nobody decides:** Plant 2 deferred.", md)
        self.assertIn("## Choices made on your behalf", md)
        self.assertIn("**1 open decision: 1 high severity.**", md)
        two = load("decision_register").to_markdown(
            {"decisions": [DECISION, dict(DECISION, severity="medium")], "ratify": [], "summary": ""})
        self.assertIn("**2 open decisions: 1 high and 1 medium severity.**", two)

    def test_markdown_no_decisions(self):
        md = load("decision_register").to_markdown({"decisions": [], "ratify": [], "summary": ""})
        self.assertIn("No open decisions were found", md)


class RepeatedTitleTest(unittest.TestCase):
    def test_strip(self):
        strip = load("report").strip_repeated_title
        self.assertEqual(strip("Canonical Facts", "## Canonical Facts\n\nSingle source"), "Single source")
        self.assertEqual(strip("Scenarios", "# Choosing Our Path\n\nx"), "# Choosing Our Path\n\nx")
        self.assertEqual(strip("Pitch", "Text first\n## Pitch"), "Text first\n## Pitch")


class ValidationStatusTest(unittest.TestCase):
    def ctx(self):
        contradiction = {"topic": "t", "severity": "high", "resolution_type": "repairable", "offending_document": "pitch"}
        decision = dict(contradiction, resolution_type="needs_decision")
        return StubCtx({
            "consistency_review_raw.json": {"contradictions": [contradiction, contradiction, decision]},
            "consistency_recheck_raw.json": {"contradictions": [decision]},
            "canonical_facts.json": {"facts": [{"kind": "user_constraint"}, {"kind": "estimate"}, {"kind": "estimate"}]},
            "arithmetic_check.json": {"checked": 12, "mismatches": [
                {"section": "Self Audit", "excerpt": "a + b = c", "stated": "9", "computed": "5"}],
                "by_section": {"Self Audit": {"checked": 3, "mismatches": 1}, "Pitch": {"checked": 2, "mismatches": 0}}},
            "decision_register_raw.json": {"decisions": [DECISION]},
        }, {"stages": {"premise_attack": {"web_searches": 8}, "pitch": {"web_searches": 0}}})

    def test_validation_status(self):
        md = load("report").validation_status(self.ctx())
        self.assertIn("Sections that searched: Premise Attack (8) | 8 searches.", md)
        self.assertIn("Before repair: 2 high / 0 medium. After: 0 high / 0 medium, plus 1", md)
        self.assertIn("12 checked, 1 wrong", md)
        self.assertIn("| Self Audit | - | yes | 3 / 1 | Consistency-checked; 1 arithmetic error |", md)
        self.assertIn("| Premise Attack | 8 | - | 0 / 0 | Partly source-checked |", md)
        self.assertIn("| Team | - | - | 0 / 0 | Not checked |", md)
        self.assertIn("## Arithmetic errors", md)

    def test_banners(self):
        mod = load("report")
        r = mod.Report(self.ctx())
        mod.lint_banner(self.ctx(), r)
        self.assertIn("Decisions required: 1 open decision, 1 high-severity", r.top_banner_markdown)
        self.assertIn('href="#decisions-required"', r.top_banner_html)
        self.assertNotIn("FAILED", r.top_banner_markdown)


if __name__ == "__main__":
    unittest.main()
