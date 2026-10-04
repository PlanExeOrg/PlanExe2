---
name: convert_pitch_to_markdown
description: Convert the raw pitch JSON into a polished, scannable markdown document.
inputs: [pitch_raw.json]
outputs: [pitch_to_markdown_raw.json, pitch.md]
tier: low
est_llm_calls: 1
---
One free-text call: system prompt `prompts/system.md`, user prompt = pitch_raw.json compacted
(metadata/query dropped). The markdown is taken from between `[START_MARKDOWN]` and
`[END_MARKDOWN]` (whole response if the delimiters are missing), bullet lists get a blank line
before/after (fix_bullet_lists), and "Persuasive elevator pitch.\n\n" is prepended.
Raw = {response_content, markdown, metadata, system_prompt, user_prompt}.

Prompt tweak (3 lines appended to the verbatim system prompt): map each pitch field to a named
`##` section in a fixed order with `## Call to Action` last, never turn `why_this_pitch_works`
into a section (Haiku rendered it as meta-commentary about the pitch), and prefer bullet lists
over dense paragraphs.
