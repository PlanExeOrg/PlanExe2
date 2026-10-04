from planexe_skill.planexe import format_json_for_query, raw_document, structured


def build_query(ctx) -> str:
    return (
        f"File 'initial-plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'project-plan.json':\n{format_json_for_query(ctx.read_json('project_plan_raw.json'))}"
    )


def to_markdown(r: dict) -> str:
    rows = []
    for item_index, suggestion in enumerate(r["suggestion_list"], start=1):
        rows.append(f"## Suggestion {item_index} - {suggestion['project_name']}\n")
        rows.append(suggestion["project_description"])
        success_metrics = "\n".join(suggestion["success_metrics"])
        rows.append(f"\n### Success Metrics\n\n{success_metrics}")
        risks_and_challenges_faced = "\n".join(suggestion["risks_and_challenges_faced"])
        rows.append(f"\n### Risks and Challenges Faced\n\n{risks_and_challenges_faced}")
        where_to_find_more_information = "\n".join(suggestion["where_to_find_more_information"])
        rows.append(f"\n### Where to Find More Information\n\n{where_to_find_more_information}")
        actionable_steps = "\n".join(suggestion["actionable_steps"])
        rows.append(f"\n### Actionable Steps\n\n{actionable_steps}")
        rows.append(f"\n### Rationale for Suggestion\n\n{suggestion['rationale_for_suggestion']}")
    rows.append(f"\n## Summary\n\n{r['summary']}")
    return "\n".join(rows)


def run(ctx):
    user_prompt = build_query(ctx)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    ctx.write_json("related_resources_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text("related_resources.md", to_markdown(response))
