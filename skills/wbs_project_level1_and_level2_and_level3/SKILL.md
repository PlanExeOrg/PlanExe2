---
name: wbs_project_level1_and_level2_and_level3
description: Extend the level 1+2 WBS tree with the level 3 decomposed tasks; export JSON and a CSV table.
inputs: [wbs_project_level1_and_level2.json, wbs_level3.json]
outputs: [wbs_project_level1_and_level2_and_level3.json, wbs_project_level1_and_level2_and_level3.csv]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/schedule]
---
Deterministic (vendored WBSPopulate + CreateWBSTableCSV).
