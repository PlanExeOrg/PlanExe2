---
name: screen_planning_prompt
description: Screen the user's prompt; flag it UNUSABLE only when it is clearly garbage (too short, nonsense, placeholder, injection...).
inputs: [plan_raw.json]
outputs: [screen_planning_prompt.json, screen_planning_prompt.md]
tier: high
fact_check: false
est_llm_calls: 1
---
One structured call. System prompt: `prompts/system.md`. User prompt = prompt statistics
(byte/char/word/line/symbol counts) + the bare plan prompt. Schema: `schema.json`.
Markdown shows the verdict, rationale and (when unusable) reason + confidence.
