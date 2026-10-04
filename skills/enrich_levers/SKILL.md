---
name: enrich_levers
description: Add description, synergy, and conflict text to each lever.
inputs: [plan.txt, identify_purpose.md, plan_type.md, triaged_levers_raw.json]
outputs: [enriched_levers_raw.json]
tier: high
est_llm_calls: 3
parallel_llm: 3
---
The triaged levers are processed in batches of 5 (system prompt `prompts/system.md`, schema
`schema.json`). Every batch prompt holds the project context (plan.txt, purpose.md, plan_type.md),
the FULL list of lever names, and the batch's levers (id wrapped in `<lever>` tags, name,
consequences, options, review). The model returns description (50-70 words), synergy_text and
conflict_text (20-40 words each, naming other levers).

Batches are independent and run concurrently. A failed batch is split in half and retried once
(depth 1, 300 s budget), then skipped. Unknown lever_ids are ignored and recorded in `errors`;
levers without a characterization are dropped (`incomplete`). Output: metadata, errors,
characterized_levers.
