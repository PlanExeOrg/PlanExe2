---
name: team_markdown
description: Compile the enriched team members (roles, contracts, backgrounds, equipment) and the team review into team.md.
inputs: [enrich_team_members_environment_info.json, review_team_raw.json]
outputs: [team.md]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/team_markdown_document.py]
---
Deterministic (vendored TeamMarkdownDocumentBuilder).
