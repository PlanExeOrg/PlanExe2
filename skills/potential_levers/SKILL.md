---
name: potential_levers
description: Brainstorm actionable levers — knobs the plan can turn to change outcomes.
inputs: [plan.txt, classify_domain.md, identify_purpose.md, plan_type.md, extract_constraints.md]
outputs: [potential_levers_raw.json, potential_levers.json]
tier: high
est_llm_calls: 24
parallel_llm: 6
uses: [planexe_skill/shared/constraint_checker.py]
---
Adaptive loop (max 5 calls) until >= 15 lever names are collected. Each call: system prompt
`prompts/system.md`, schema `schema.json` (strategic_rationale + 5-7 levers with lever_index, name,
consequences, options, review_lever). User prompt = `File 'plan.txt'`, `File 'classify_domain.md'`,
`File 'purpose.md'`, `File 'plan_type.md'` sections; calls 2+ are prefixed with "Generate 5 to 7 MORE
levers ... Do NOT reuse any of these already-generated names: [...]".

Validation as in PlanExe: >= 5 levers, >= 3 options per lever (stringified arrays are parsed),
review_lever >= 10 chars and no square brackets; a failing call is skipped (the run fails only if
every call fails).

After each call every lever is checked individually against the extracted constraints (shared
constraint checker; constraints = `{"constraints_markdown": extract_constraints.md}`, stage name
`lever: <name>`). Levers with a `violated` constraint are dropped and listed in a
"## Constraint Violation History" section appended to later calls. A failing check accepts the lever.

Cleanup: flatten, skip exact duplicate names, assign uuid4 lever_ids, rename review_lever -> review.
potential_levers.json = cleaned list; raw = responses + levers + constraint_checks + metadata + prompts.
