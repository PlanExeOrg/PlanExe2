---
name: premise_attack
description: Attack the plan's core premise through five critical lenses (Integrity, Accountability, Spectrum, Cascade, Escalation).
inputs: [plan.txt]
outputs: [premise_attack_raw.json, premise_attack.md]
tier: high
est_llm_calls: 5
parallel_llm: 5
---
Five independent structured calls, one per lens; each lens has its own system prompt in
`prompts/lens_*.md`, the user prompt is plan.txt, and every call uses `schema.json`
(core_thesis, reasons, second_order_effects, evidence, bottom_line). A failed lens is skipped
(as in PlanExe); the stage fails only if all lenses fail.
