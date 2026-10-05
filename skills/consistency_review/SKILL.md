---
name: consistency_review
description: Final cross-report pass. Distill the plan into a one-page decision kernel (the few go/no-go questions) and list contradictions between documents (prices and units, gate thresholds, deadlines vs today, phase criteria).
inputs: [plan.txt, executive_summary.md, project_plan.md, consolidate_assumptions_short.md, review_plan.md, premortem.md, self_audit.md, pitch.md]
outputs: [consistency_review_raw.json, consistency_review.md]
tier: high
fact_check: false
est_llm_calls: 1
---
Not part of the original PlanExe pipeline (added after the Codex reviews of the battery and
datacenter reports, which found the main remaining weakness to be cross-document consistency:
e.g. EUR 70-80/MWh tenant pricing vs EUR 140-160/MWh electricity, conflicting gate percentages,
deadlines already in the past). One reasoning call reads the core documents and returns:

- `decision_questions`: the 3-6 yes/no questions that decide go / delay / split / downsize / stop,
  each with its threshold, the evidence that answers it, and what a NO means.
- `contradictions`: pairs of statements that cannot both be true, where each was found, why they
  conflict and the suggested resolution, with severity.

The report renders it as its first section ("Decision Kernel and Consistency Check").
