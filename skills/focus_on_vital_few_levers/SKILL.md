---
name: focus_on_vital_few_levers
description: Select the ~5 highest-impact levers by rating each as critical, high, or medium.
inputs: [plan.txt, identify_purpose.md, plan_type.md, enriched_levers_raw.json]
outputs: [vital_few_levers_raw.json]
tier: high
fact_check: false
est_llm_calls: 1
---
80/20 principle. One structured call (system prompt `prompts/system.md`, schema `schema.json`): the
user prompt holds the project context (plan.txt, purpose.md, plan_type.md) and every enriched lever as
JSON (lever_id, name, consequences, options, review, description, synergy_text, conflict_text). The
model rates each lever Critical / High / Medium / Low with a justification, plus a summary.

If that call fails, PlanExe's fallback runs: compressed levers (id, name, description, synergy,
conflict) in even batches of <= 4 (no singleton tail), summaries joined.

Selection in code: take lever_ids in order Critical -> High -> Medium -> Low until 5 are picked;
output levers keep the enriched-list order.
