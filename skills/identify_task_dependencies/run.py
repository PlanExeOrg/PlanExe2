import json

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured


def run(ctx):
    query = (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'project_plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'Work Breakdown Structure.json':\n{format_json_for_query(ctx.read_json('wbs_level2.json'))}\n\n"
        f"File 'data_collection.md':\n{ctx.read_text('data_collection.md')}"
    )
    preamble = ctx.skill_file("prompts/query_preamble.md")
    # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
    response, result = structured(ctx, "", preamble + query, ctx.skill_json("schema.json"))

    details = []
    for item in response.get("task_dependency_details") or []:
        details.append({
            "dependent_task_id": str(item.get("dependent_task_id", "")),
            "depends_on_task_id_list": [str(x) for x in (item.get("depends_on_task_id_list") or [])],
            "depends_on_task_explanation_list": [str(x) for x in (item.get("depends_on_task_explanation_list") or [])],
        })
    metadata = planexe_metadata(result)
    metadata.pop("response_byte_count", None)
    raw = {"task_dependency_details": details, "metadata": metadata, "query": query}
    ctx.write_text("task_dependencies_raw.json", json.dumps(raw, indent=2))
