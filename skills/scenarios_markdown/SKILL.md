---
name: scenarios_markdown
description: Format the selected scenario and rejected alternatives into a readable document.
inputs: [candidate_scenarios.json, selected_scenario.json]
outputs: [scenarios.md]
tier: low
est_llm_calls: 0
---
Deterministic (no LLM). "# Choosing Our Strategic Path": the plan characteristics ("## The Strategic
Context"), the chosen scenario ("## The Path Forward": logic, fit score, why chosen, lever settings,
decisive-factors justification), then the other scenarios ("## Alternative Paths").
