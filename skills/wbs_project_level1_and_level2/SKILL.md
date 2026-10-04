---
name: wbs_project_level1_and_level2
description: Merge WBS level 1 (project) and level 2 (phases/major tasks) into one WBS project tree.
inputs: [wbs_level1.json, wbs_level2.json]
outputs: [wbs_project_level1_and_level2.json]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/schedule]
---
Deterministic (vendored WBSPopulate).
