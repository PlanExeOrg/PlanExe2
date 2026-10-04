---
name: redline_gate
description: Safety gate. Decide ALLOW / ALLOW_WITH_SAFETY_FRAMING / REFUSE for the prompt, treating it as real-world intent.
inputs: [plan.txt]
outputs: [redline_gate_raw.json, redline_gate.md]
tier: high
est_llm_calls: 1
---
One structured call: system prompt `prompts/system.md` (PlanExe's SYSTEM_PROMPT_25, "the balanced
analyst"), user prompt = plan.txt, schema `schema.json`. Markdown shows the verdict, rationale and
a violation-details table when present.
