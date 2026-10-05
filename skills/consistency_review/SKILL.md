---
name: consistency_review
description: Final cross-report pass. Distill the plan into a one-page decision kernel (the few go/no-go questions) and list contradictions between documents (prices and units, gate thresholds, deadlines vs today, phase criteria).
inputs: [canonical_facts.json, plan.txt, executive_summary.md, project_plan.md, consolidate_assumptions_short.md, review_plan.md, premortem.md, self_audit.md, pitch.md]
outputs: [consistency_review_raw.json, consistency_review.md]
tier: high
fact_check: false
est_llm_calls: 1
uses: [planexe_skill/shared/consistency]
---
Not part of the original PlanExe pipeline (added after the Codex reviews of the battery and
datacenter reports, which found the main remaining weakness to be cross-document consistency:
e.g. EUR 70-80/MWh tenant pricing vs EUR 140-160/MWh electricity, conflicting gate percentages,
deadlines already in the past). One reasoning call reads the core documents and returns:

- `decision_questions`: the 3-6 yes/no questions that decide go / delay / split / downsize / stop,
  each with its threshold, the evidence that answers it, and what a NO means.
- `contradictions`: pairs of statements that cannot both be true, where each was found, why they
  conflict and the suggested resolution, with severity.

This is lint pass 1. `consistency_repair` fixes the documents it names and `consistency_recheck` (lint
pass 2) re-checks the repaired documents; the report shows the recheck. Prompt and schema live in
`planexe_skill/shared/consistency/`.
