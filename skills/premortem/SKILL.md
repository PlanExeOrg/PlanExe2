---
name: premortem
description: Imagine the project has already failed — identify how and why it would happen.
inputs: [canonical_facts.json, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, project_plan.md, data_collection.md, related_resources.md, swot_analysis.md, team.md, pitch.md, expert_criticism.md, wbs_project_level1_and_level2_and_level3.csv, review_plan.md, questions_and_answers.md]
outputs: [premortem_raw.json, premortem.md]
tier: low
est_llm_calls: 3
parallel_llm: 1
uses: [planexe_skill/shared/final_review.py]
max_words_per_field: 80
---
User prompt = the 11 review documents (see review_plan) + `File 'review-plan.md'` +
`File 'questions-and-answers.md'`. (The PlanExe node also *requires* consolidate_governance and
documents_to_create_and_find but never reads them.)

Three structured calls with `prompts/system.md`, schema `schema.json` (assumptions_to_kill x3,
failure_modes x3 with optional owner/likelihood_5/impact_5/tripwires/playbook/stop_rule), in one
accumulating chat: call 1 = the query, call 2 = "Generate 3 new assumptions ... Start assumption_id
at A4.", call 3 = "... covers different archetypes. Start assumption_id at A7.". Earlier turns
(compact JSON responses) are embedded in the user message, so the calls are sequential. A failed
follow-up is skipped; a failed first call fails the stage (as in PlanExe).

All assumptions / failure modes are concatenated. Markdown: Assumptions to Kill table, failure-mode
summary table (risk level = likelihood x impact: >=15 CRITICAL, >=9 HIGH, >=4 MEDIUM, else LOW), then
per failure mode: story, early warning signs, tripwires, response playbook, stop rule.

Guard vs PlanExe: a follow-up response that repeats assumption ids from earlier responses (Haiku
sometimes re-emits A1-A3 before the new A4-A6) has those assumptions and their failure modes
dropped; a follow-up left with nothing new is skipped like a failed follow-up. Prompts verbatim.
