---
name: consistency_repair
description: Fix the documents named by consistency_review's high/medium diagnostics so they agree with the canonical facts (exact find/replace edits), writing repaired copies.
inputs: [consistency_review_raw.json, canonical_facts.json, plan.txt, consolidate_assumptions_short.md, executive_summary.md, project_plan.md, pitch.md, review_plan.md, premortem.md, self_audit.md, questions_and_answers.md]
outputs: [consistency_repair_raw.json, repaired_executive_summary.md, repaired_project_plan.md, repaired_pitch.md, repaired_review_plan.md, repaired_premortem.md, repaired_self_audit.md, repaired_questions_and_answers.md, consistency_recheck_raw.json, consistency_recheck.md]
tier: mid
calendar_fix: false
fact_check: false
max_words_per_field: 0
est_llm_calls: 12
parallel_llm: 4
uses: [planexe_skill/shared/consistency, planexe_skill/calendar_fix.py, planexe_skill/shared/arithmetic.py]
---
Not part of the original PlanExe pipeline (Codex: "make high-severity lint errors fail the build ...
regenerate offending sections"). For each reader-facing document named in a HIGH or MEDIUM diagnostic
of consistency_review, one call returns exact find/replace edits (verbatim excerpt -> corrected text)
that make it agree with the canonical facts; Python applies them, so everything else stays verbatim and
no document is re-typed. Every repairable document gets a `repaired_*.md` copy (unchanged if nothing
to fix); the original PlanExe files are not modified. The assumptions document is not repaired: it
predates the canonical facts by design. After each repair round the repaired copies are linted again (same review as consistency_review,
`planexe_skill/shared/consistency/`); rounds repeat until no high-severity contradiction remains or 3
rounds have run (Codex: "repeat until zero high-severity contradictions"). The final check is written
to `consistency_recheck.md` / `consistency_recheck_raw.json`, which the report shows. Round 1 also gets the deterministic arithmetic mismatches
(`planexe_skill/shared/arithmetic.py`, diagnostics `AR-nnn`) found in the documents it repairs.
