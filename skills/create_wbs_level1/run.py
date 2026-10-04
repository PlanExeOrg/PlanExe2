from uuid import uuid4

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured


def run(ctx):
    query = format_json_for_query(ctx.read_json("project_plan_raw.json"))
    preamble = ctx.skill_file("prompts/query_preamble.md")
    # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
    response, result = structured(ctx, "", preamble + query, ctx.skill_json("schema.json"))

    metadata = planexe_metadata(result)
    metadata.pop("response_byte_count", None)
    metadata["query"] = query
    raw = dict(response)
    raw["metadata"] = metadata
    ctx.write_json("wbs_level1_raw.json", raw)

    project_title = response["project_title"]
    clean = {
        "id": str(uuid4()),
        "project_title": project_title,
        "final_deliverable": response["final_deliverable"],
    }
    ctx.write_json("wbs_level1.json", clean)
    ctx.write_text("wbs_level1_project_title.json", project_title)
