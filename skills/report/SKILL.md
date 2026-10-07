---
name: report
description: Assemble all stage outputs into the final report.html (collapsible sections, Gantt) and report.md.
inputs: [plan.txt, consistency_recheck.md, consistency_recheck_raw.json, consistency_review_raw.json, canonical_facts.json, decision_register.md, decision_register_raw.json, arithmetic_check.json, screen_planning_prompt.json, screen_planning_prompt.md, redline_gate.md, premise_attack.md, strategic_decisions.md, scenarios.md, consolidate_assumptions_full.md, team.md, related_resources.md, consolidate_governance.md, swot_analysis.md, repaired_pitch.md, data_collection.md, documents_to_create_and_find.md, wbs_level1_project_title.json, wbs_project_level1_and_level2_and_level3.csv, expert_criticism.md, repaired_project_plan.md, repaired_review_plan.md, repaired_executive_summary.md, schedule_gantt_dhtmlx.html, repaired_questions_and_answers.md, repaired_premortem.md, repaired_self_audit.md, prompt_adherence.md]
outputs: [report.html, report.md]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/markdown_html.py]
---
Deterministic. Three parts (PlanExe2; PlanExe v1 had one flat list of sections):

1. **Key decisions and facts**: Decision Dashboard (decision kernel + consistency summary),
   Decisions Required (`decision_register.md`), Canonical Facts, Executive Summary, Gantt (embedded
   dhtmlx HTML).
   All sections start collapsed, as in PlanExe v1.
2. **Supporting analysis**: Pitch, Project Plan, Strategic Decisions, Scenarios, Assumptions, Governance,
   Related Resources, Data Collection, Documents to Create and Find, SWOT Analysis, Team, Expert
   Criticism, Work Breakdown Structure (CSV table), Review Plan, Questions & Answers, Premortem, Self Audit.
3. **Audit trail**: Validation Status (moved here from Part 1: it describes how the plan was checked),
   Consistency Check, Initial Prompt Vetted (prompt + screening + redline gate + premise
   attack), Prompt Adherence, Metadata.

Why: a Codex comparison of v1 and v2 reports summed up the difference as "v1: generate an unusually
comprehensive expert planning workshop; v2: construct a partially validated model of the project, then
expose what humans still have to decide". The report leads with the open decisions and key facts; the
workshop material is supporting analysis.

Validation Status says what "validated" means: which stages used web search (per-stage counts from
`planexe_report_metadata.json`), the canonical facts by kind, the consistency lint before/after repair, the
deterministic arithmetic check (`arithmetic_check.json`, every remaining error listed), calendar and
schedule; then a per-section table (web searches, linted or not, arithmetic checked/wrong, status:
partly source-checked / consistency-checked / not checked).

Canonical Facts is rendered from `canonical_facts.json` for readers (a legend for the Kind column + the
table); `canonical_facts.md` is worded for the later stages ("All later documents were instructed to use
these values"). The model's reconciliation notes (process notes) go to the Consistency Check in Part 3.
The SWOT section's headings are shown without PlanExe's emoji ("Strengths 👍💪🦾" -> "Strengths");
`swot_analysis.md` keeps them, like PlanExe. The v2 sections open with a one-line subtitle, in the style of PlanExe's "Persuasive elevator pitch.",
"Why this fails." and the Gantt's "Unoptimized waterfall. Parallel work not modelled here.": Decision
Dashboard, Decisions Required, Canonical Facts, Validation Status, Consistency Check, Metadata.
All one-line subtitles are italic, like the Team section's "*Roles Needed & Example People*": PlanExe's
own (pitch, premortem, self audit, Gantt, "Why this fails.") and the v2 ones; the documents keep them as
plain lines, as in PlanExe. Expert Criticism drops PlanExe's two opening headings ("Project Expert Review & Recommendations", "A
Compilation of Professional Feedback ...", both repeating the section title) for the subtitle "Critique and
recommended actions from domain experts."; expert_criticism.md keeps them. Scenarios shows scenarios.md's opening heading "Choosing Our Strategic Path" as the italic subtitle
"Choosing our strategic path.".
A leading heading inside a section that repeats the section title is dropped. Both are done here rather
than in the stages, so existing runs need no regeneration. Title = wbs_level1_project_title.json. Banners at the top: an UNUSABLE screening verdict; "Consistency
lint FAILED" when repairable high-severity contradictions remain after repair (`consistency_recheck`).
Banners link to their section (sections have ids). There is no banner for open decisions: Decisions
Required is the second section, and a banner repeated it.

Reader-facing text only: the Decision Dashboard is the decision-kernel table alone (the repair summary
moves to the Consistency Check; the consistency summary and "see ..." pointers were dropped as
repetition), the Consistency Check omits the compiler-style diagnostics block (same items as its numbered
list; kept in consistency_recheck.md), parts have no intro sentences, the header line names only
the generator, "PlanExe2" (version, repo and commit are in Metadata); a second line appears only for hand-edited
files (the plan date is in the prompt and in Metadata).
The executive summary, project plan, pitch, review plan, Q&A, premortem and self-audit sections use
the repaired copies from consistency_repair.

Markdown is rendered with the stdlib renderer in `planexe_skill/shared/markdown_html.py`
(PlanExe used Python-Markdown; tables are rendered in every section).

Report metadata: the line under the title names the generator (PlanExe2); the final "Metadata" section (titled "Report Metadata" briefly) gives the generator version
(`git describe --tags`, e.g. v2.0.0 or v2.0.0-3-gabc1234), repo and commit, and lists per stage which generator version produced it, when, with which models, plus hand-edited and adopted files.
Source: `planexe_report_metadata.json`, maintained by the runner (read via `ctx.run_metadata()`, not a
declared input). Named "Provenance" / `planexe_provenance.json` until 2026-10-07; that read like a
history of superseded plans.
