---
name: triage_levers
description: Triage levers into primary, secondary, or remove.
inputs: [plan.txt, identify_purpose.md, plan_type.md, potential_levers.json]
outputs: [triaged_levers_raw.json]
tier: high
fact_check: false
est_llm_calls: 1
---
One batch call: system prompt `prompts/system.md`, schema `schema.json` (one decision per lever_id:
primary / secondary / remove + justification). User prompt = `**Project Context:**` (plan.txt,
purpose.md, plan_type.md sections) + `**Levers to classify (N total):**` (the levers as JSON) +
"Classify every lever as primary, secondary, or remove."

Code: ignore unknown/duplicate lever_ids, default unclassified levers to secondary, drop `remove`,
attach classification + deduplication_justification to the surviving levers. A failed call keeps
every lever as secondary (as in PlanExe). Raw `user_prompt` holds only the project context.
