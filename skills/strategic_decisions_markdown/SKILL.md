---
name: strategic_decisions_markdown
description: Summarize the lever exploration pipeline into a readable strategic-decisions document.
inputs: [enriched_levers_raw.json, vital_few_levers_raw.json]
outputs: [strategic_decisions.md]
tier: low
est_llm_calls: 0
---
Deterministic (no LLM). "## Primary Decisions": the vital-levers summary, then each vital lever as
"### Decision N: <name>" (lever id, core decision = description, why it matters = consequences,
numbered strategic choices, trade-off = review, synergy, conflict, importance + justification).
"## Secondary Decisions": the remaining enriched levers in the same layout, numbering continued.
