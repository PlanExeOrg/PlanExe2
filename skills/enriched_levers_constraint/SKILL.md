---
name: enriched_levers_constraint
description: Guardrail: verify enriched levers still respect the user's constraints.
inputs: [extract_constraints_raw.json, enriched_levers_raw.json]
outputs: [enriched_levers_constraint.json]
tier: high
est_llm_calls: 1
uses: [planexe_skill/shared/constraint_checker.py]
---
One structured call via `planexe_skill/shared/constraint_checker.py` (PlanExe's ConstraintChecker).
User prompt = `## Constraints` (only the `constraints` list of extract_constraints_raw.json, as JSON)
+ `## Stage Output (enriched_levers)` (the file `enriched_levers_raw.json` verbatim). Each constraint is judged
satisfied / violated / unclear (negative constraints: synonyms of banned concepts count as
violations); overall_status is pass/fail. Output = response + metadata + system_prompt + user_prompt.
