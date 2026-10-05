---
name: consistency_recheck
description: Lint pass 2 - decision kernel and remaining contradictions over the repaired documents; this is what the report shows.
inputs: [canonical_facts.json, plan.txt, consistency_review_raw.json, consistency_repair_raw.json, repaired_executive_summary.md, repaired_project_plan.md, consolidate_assumptions_short.md, repaired_review_plan.md, repaired_premortem.md, repaired_self_audit.md, repaired_pitch.md]
outputs: [consistency_recheck_raw.json, consistency_recheck.md]
tier: high
fact_check: false
est_llm_calls: 1
uses: [planexe_skill/shared/consistency]
---
Same review as consistency_review (prompt and schema in `planexe_skill/shared/consistency/`), run on the
documents written by consistency_repair. The markdown starts with a line on what pass 1 found and how many
edits were applied. Remaining HIGH contradictions make the report show a FAILED consistency banner.
