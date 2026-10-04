---
name: distill_assumptions
description: Condense verbose assumptions into concise, strategically important ones.
inputs: [plan.txt, identify_purpose.md, strategic_decisions.md, scenarios.md, make_assumptions.json]
outputs: [distill_assumptions_raw.json, distill_assumptions.md]
tier: low
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (assumption_list: [str]).
User prompt concatenates plan.txt, purpose.md, strategic_decisions.md, scenarios.md and
`assumptions.json` (make_assumptions.json as compact JSON). Each distilled assumption is one short
sentence (<= 17 words) keeping the key numbers. Markdown is a bullet list.
