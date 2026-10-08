---
name: arithmetic_check
description: Deterministically re-compute every explicit calculation written in the report's documents ("a x b = c", "a + b = c", ranges, percents) and list the ones whose stated result is wrong.
inputs: [canonical_facts.md, decision_register.md, repaired_executive_summary.md, repaired_pitch.md, repaired_project_plan.md, strategic_decisions.md, scenarios.md, consolidate_assumptions_full.md, consolidate_governance.md, related_resources.md, data_collection.md, documents_to_create_and_find.md, swot_analysis.md, team.md, expert_criticism.md, repaired_review_plan.md, repaired_questions_and_answers.md, repaired_premortem.md, repaired_self_audit.md, premise_attack.md]
outputs: [arithmetic_check.json, arithmetic_check.md]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/arithmetic.py]
---
Not part of the original PlanExe pipeline. No LLM: `planexe_skill/shared/arithmetic.py` finds
statements of the form `expression = value` (also chains, value-first statements, ranges such as
"EUR 30-50", multipliers k/M/B/bn/million, percents, units after numbers) and evaluates them.

It is tuned for precision: anything ambiguous (dates, slash lists like "Months 36/84", numbers glued to
a parenthetical, a product restated in other units) is skipped, and a statement passes if any
reasonable reading matches (rounding of the stated value, with or without multipliers, a power-of-1000
unit shift, the complement of a single percent, "X + p%" as an increase by p%: "EUR 70 + 10% = EUR 77"). Checked against all earlier runs: 189 statements,
4 flagged, all real or misleading (e.g. "EUR 50-100M + 300-500M + 200-300M = EUR 850M-1.4B", which is
EUR 550-900M).

Earlier, `consistency_repair` uses the same checker on the documents it repairs, so mismatches found
there are fixed before this final check. The report's "Validation Status" section shows the counts and
lists every remaining mismatch.
