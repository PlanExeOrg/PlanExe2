---
name: prompt_adherence
description: Score how faithfully the final plan follows the user's original prompt.
inputs: [canonical_facts.json, plan_raw.json, project_plan.md, executive_summary.md, consolidate_assumptions_full.md]
outputs: [prompt_adherence_raw.json, prompt_adherence.md]
tier: low
est_llm_calls: 2
parallel_llm: 1
---
Phase 1: `prompts/extract_directives.md`, schema `schema_directives.json`; user prompt =
"User's original prompt:\n" + plan_prompt (the bare prompt from plan_raw.json, not plan.txt).
Phase 2: `prompts/score_adherence.md`, schema `schema_scores.json`; user prompt = original prompt +
the phase-1 directives (indented JSON) + plan context (`File 'executive_summary.md'`,
`File 'project_plan.md'`, `File 'consolidate_assumptions_full.md'`). Phase 2 depends on phase 1.

Markdown (deterministic): overall weighted adherence % with the math, a summary table sorted by
directive index, and an Issues section for every directive with adherence < 5, sorted by severity
importance x (6 - adherence).
