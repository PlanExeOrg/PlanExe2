import json

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured
from planexe_skill.shared.schedule.wbs_task import WBSProject

PITCH_KEYS = ("pitch", "why_this_pitch_works", "target_audience", "call_to_action", "risks_and_mitigation",
              "metrics_for_success", "stakeholder_benefits", "ethical_considerations",
              "collaboration_opportunities", "long_term_vision")


def run(ctx):
    wbs_project_json = WBSProject.from_dict(ctx.read_json("wbs_project_level1_and_level2.json")).to_dict()
    query = (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'project_plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'Work Breakdown Structure.json':\n{format_json_for_query(wbs_project_json)}\n\n"
        f"File 'similar_projects.md':\n{ctx.read_text('related_resources.md')}"
    )
    preamble = ctx.skill_file("prompts/query_preamble.md")
    # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
    response, result = structured(ctx, "", preamble + query, ctx.skill_json("schema.json"))

    raw = {k: str(response.get(k) or "") for k in PITCH_KEYS}
    metadata = planexe_metadata(result)
    metadata.pop("response_byte_count", None)
    raw["metadata"] = metadata
    raw["query"] = query
    ctx.write_text("pitch_raw.json", json.dumps(raw, indent=2))
