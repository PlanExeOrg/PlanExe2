---
name: report
description: Assemble all stage outputs into the final report.html (collapsible sections, Gantt) and report.md.
inputs: [plan.txt, consistency_recheck.md, consistency_recheck_raw.json, canonical_facts.md, screen_planning_prompt.json, screen_planning_prompt.md, redline_gate.md, premise_attack.md, strategic_decisions.md, scenarios.md, consolidate_assumptions_full.md, team.md, related_resources.md, consolidate_governance.md, swot_analysis.md, repaired_pitch.md, data_collection.md, documents_to_create_and_find.md, wbs_level1_project_title.json, wbs_project_level1_and_level2_and_level3.csv, expert_criticism.md, repaired_project_plan.md, repaired_review_plan.md, repaired_executive_summary.md, schedule_gantt_dhtmlx.html, repaired_questions_and_answers.md, repaired_premortem.md, repaired_self_audit.md, prompt_adherence.md]
outputs: [report.html, report.md]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/markdown_html.py]
---
Deterministic. Sections, in order: Decision Kernel and Consistency Check (added in PlanExe-skill), Executive Summary, Gantt (embedded dhtmlx HTML), Pitch, Project
Plan, Strategic Decisions, Scenarios, Assumptions, Governance, Related Resources, Data Collection,
Documents to Create and Find, SWOT Analysis, Team, Expert Criticism, Work Breakdown Structure (CSV
table), Review Plan, Questions & Answers, Premortem, Self Audit, Initial Prompt Vetted (prompt +
screening + redline gate + premise attack), Prompt Adherence. Title = wbs_level1_project_title.json.
An UNUSABLE screening verdict adds a warning banner at the top, and so do high-severity contradictions
found by consistency_recheck (the "consistency lint"; FAILED when any remain). The
executive summary, project plan, pitch, review plan, Q&A, premortem and self-audit sections use the
repaired copies from consistency_repair.

Markdown is rendered with the stdlib renderer in `planexe_skill/shared/markdown_html.py`
(PlanExe used Python-Markdown; tables are rendered in every section).
