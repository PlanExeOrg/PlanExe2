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
    def __init__(self, files: dict, metadata: dict | None = None):
        self.files = files
        self.metadata = metadata or {}

    def read_text(self, name):
        v = self.files[name]
        return v if isinstance(v, str) else json.dumps(v)

    def read_json(self, name):
        v = self.files[name]
        return json.loads(v) if isinstance(v, str) else v

    def run_metadata(self):
        return self.metadata


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


class SubtitleTest(unittest.TestCase):
    def test_planexe_subtitles_italic(self):
        italic = load("report").italic_subtitle
        self.assertEqual(italic("Persuasive elevator pitch.\n\n# Title"), "*Persuasive elevator pitch.*\n\n# Title")
        self.assertEqual(italic("Reality check: fix before go.\n\n### Summary"), "*Reality check: fix before go.*\n\n### Summary")
        self.assertEqual(italic("Some other first line.\n"), "Some other first line.\n")


class HeadingToSubtitleTest(unittest.TestCase):
    def test_convert(self):
        f = load("report").heading_to_subtitle
        self.assertEqual(f("# Choosing Our Strategic Path\n## The Strategic Context\n", "Choosing Our Strategic Path",
                           "Choosing our strategic path."), "*Choosing our strategic path.*\n\n## The Strategic Context\n")
        self.assertEqual(f("# Other\n", "Choosing Our Strategic Path", "x."), "# Other\n")


class ExpertHeadingsTest(unittest.TestCase):
    def test_strip(self):
        strip = load("report").strip_expert_headings
        md = ("# Project Expert Review & Recommendations\n\n## A Compilation of Professional Feedback for Project "
              "Planning and Execution\n\n\n# 1 Expert: Plant Pathologist")
        self.assertEqual(strip(md), "# 1 Expert: Plant Pathologist")


class WbsCsvTest(unittest.TestCase):
    def test_writer_quotes_separator(self):
        from planexe_skill.shared.schedule.create_wsb_table_csv import CreateWBSTableCSV
        from planexe_skill.shared.schedule.wbs_task import WBSProject, WBSTask
        root = WBSTask("r1", "Program")
        root.task_children.append(WBSTask("t1", "Establish committee; recruit chair"))
        root.task_children.append(WBSTask("t2", "Plain task"))
        c = CreateWBSTableCSV(WBSProject(root))
        c.execute()
        self.assertEqual(c.to_csv_string().splitlines(), [
            "Level 1;Level 2;Task ID", "Program;;r1", ';"Establish committee; recruit chair";t1', ";Plain task;t2"])

    def test_report_rejoins_unquoted_rows(self):
        mod = load("report")
        ctx = StubCtx({"wbs.csv": "Level 1;Level 2;Task ID\nProgram;;r1\n;Establish committee; recruit chair;t1\n"})
        r = mod.Report(ctx)
        r.csv_table("Work Breakdown Structure", "wbs.csv")
        html = r.html_items[-1][1]
        self.assertIn("<td>Establish committee; recruit chair</td>", html)
        self.assertIn("<td>t1</td>", html)
        self.assertNotIn('border="1"', html)


class HeadingEmojiTest(unittest.TestCase):
    def test_strip(self):
        strip = load("report").strip_heading_emoji
        md = ("## Strengths 👍💪🦾\n- Brazil leads 💪\n## Threats ☠️🛑🚨☢︎💩☣︎\n## Missing Information 🧩🤷‍♂️🤷‍♀️\n"
              "## Weaknesses 👎😱🪫⚠️")
        self.assertEqual(strip(md), "## Strengths\n- Brazil leads 💪\n## Threats\n## Missing Information\n## Weaknesses")


class ExpertReviewTest(unittest.TestCase):
    def test_all_experts_and_failed_ones(self):
        mod = load("expert_review")
        experts = [{"title": f"Expert {k}"} for k in "ABC"]
        crit = {"user_primary_actions": ["Do X"], "user_secondary_actions": [], "follow_up_consultation": "",
                "negative_feedback_list": []}
        md = mod.to_markdown(experts, [crit, None, crit])
        self.assertIn("# 1 Expert: Expert A", md)
        self.assertIn("# 3 Expert: Expert C", md)
        self.assertIn("## 3.1 Primary Actions", md)
        tail = md.split("# The following experts did not provide feedback:")[1]
        self.assertIn("# 2 Expert: Expert B", tail)
        self.assertNotIn("did not provide feedback", mod.to_markdown(experts, [crit, crit, crit]))


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
        self.assertIn("Before repair: 2 high / 0 medium. After: 0 high / 0 medium, plus 1 needing a decision", md)
        self.assertIn("12 checked, 1 wrong", md)
        self.assertIn("| Self Audit | consistency lint and repair; arithmetic (3 calculations, 1 wrong) |", md)
        self.assertIn("| Premise Attack | web search (8 searches) |", md)
        self.assertIn("| Team | none |", md)
        self.assertIn("## Arithmetic errors", md)

    def test_banners(self):
        mod = load("report")
        r = mod.Report(self.ctx())
        mod.lint_banner(self.ctx(), r)
        self.assertEqual("", r.top_banner_markdown)  # no repairable high left; decisions have their own section
        failing = self.ctx()
        failing.files["consistency_recheck_raw.json"] = {"contradictions": [
            {"topic": "Price vs cost", "severity": "high", "resolution_type": "repairable", "offending_document": "pitch"}]}
        r = mod.Report(failing)
        mod.lint_banner(failing, r)
        self.assertIn("Consistency lint FAILED: 1 high-severity contradiction remains after repair", r.top_banner_markdown)
        self.assertIn('href="#consistency-check"', r.top_banner_html)

    def test_split_consistency(self):
        md = ("_Consistency: first pass found 2 high._\n\n## Decision Kernel\n\nAny NO means delay, split, downsize or "
              "stop, as described.\n\n| # | Question |\n|---|---|\n| 1 | Q |\n\n## Consistency Check\n\n"
              "Diagnostics (document vs canonical fact):\n\n```text\nHIGH CF-001\n```\n\n### 1. Topic\n\n## Summary\n\nOK.")
        dashboard, check = load("report").split_consistency(md)
        self.assertEqual(dashboard, "| # | Question |\n|---|---|\n| 1 | Q |")
        self.assertTrue(check.startswith("_Consistency: first pass found 2 high._"))
        self.assertNotIn("CF-001", check)
        self.assertIn("### 1. Topic", check)


if __name__ == "__main__":
    unittest.main()
