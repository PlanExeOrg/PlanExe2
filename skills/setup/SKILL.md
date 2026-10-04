---
name: setup
description: Turn plan_raw.json (the user's prompt + date) into plan.txt, the text every later stage reads.
inputs: [plan_raw.json]
outputs: [plan.txt]
tier: low
est_llm_calls: 0
---
Deterministic. `plan.txt` = "Plan:\n{plan_prompt}\n\nToday's date:\n{pretty_date}\n\nProject start ASAP".
