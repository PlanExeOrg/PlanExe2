---
name: self_audit
description: Checklist-based diagnostic — find gaps, contradictions, and unsupported claims across all stages.
inputs: [canonical_facts.json, plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, data_collection.md, related_resources.md, swot_analysis.md, team.md, pitch.md, expert_criticism.md, wbs_project_level1_and_level2_and_level3.csv, review_plan.md, questions_and_answers.md, premortem.md]
outputs: [self_audit_raw.json, self_audit.md]
tier: low
est_llm_calls: 20
parallel_llm: 1
uses: [planexe_skill/shared/final_review.py]
---
User prompt = the 11 review documents (see review_plan) + `File 'review-plan.md'` +
`File 'questions-and-answers.md'` + `File 'premortem.md'`.

Item 1 "Violates Known Physics": dedicated call, system prompt `prompts/violates_known_physics.md`,
schema `schema_physics.json` (justification, mitigation, level enum), user prompt = the bare plan.txt
(PlanExe routes the physics check to the initial prompt to avoid false positives).

Items 2-20 (`checklist.json`, PlanExe's BATCH_CHECKLIST_ITEMS): one call per item, system prompt
built from `prompts/checklist_system.md` (expected index, the item's instruction, the checklist as
JSON with status TODO for the current item and IGNORE + "title\nsubtitle" for the others, the answer
skeleton), schema `schema_checklist_answer.json`. The user prompt = query + "# Checklist Answers" with
all previous answers (indented JSON keyed by item index), so the calls are sequential, exactly as in
PlanExe. A failed item fails the stage (as in PlanExe).

Markdown: Summary table (High/Medium/Low counts) then `## N. <title>` with subtitle, level,
justification, mitigation per item.
