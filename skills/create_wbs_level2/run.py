import json
from uuid import uuid4

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured


def run(ctx):
    query = (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'project_plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'WBS Level 1.json':\n{format_json_for_query(ctx.read_json('wbs_level1.json'))}\n\n"
        f"File 'data_collection.md':\n{ctx.read_text('data_collection.md')}"
    )
    preamble = ctx.skill_file("prompts/query_preamble.md")
    # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
    response, result = structured(ctx, "", preamble + query, ctx.skill_json("schema.json"))

    phases = []
    for phase in response.get("major_phase_details") or []:
        subtasks = [{"subtask_wbs_number": str(s.get("subtask_wbs_number", "")),
                     "subtask_title": str(s.get("subtask_title", ""))}
                    for s in (phase.get("subtasks") or [])]
        phases.append({"major_phase_wbs_number": str(phase.get("major_phase_wbs_number", "")),
                       "major_phase_title": str(phase.get("major_phase_title", "")),
                       "subtasks": subtasks})
    if not phases:
        raise ValueError("The model returned no major phases.")

    metadata = planexe_metadata(result)
    metadata.pop("response_byte_count", None)
    raw = {"major_phase_details": phases, "metadata": metadata, "query": query}
    ctx.write_text("wbs_level2_raw.json", json.dumps(raw, indent=2))

    # Cleanup: assign unique ids to each major phase and subtask.
    major_phases_with_subtasks = []
    for phase in phases:
        subtask_list = [{"id": str(uuid4()), "description": s["subtask_title"]} for s in phase["subtasks"]]
        major_phases_with_subtasks.append({
            "id": str(uuid4()),
            "major_phase_title": phase["major_phase_title"],
            "subtasks": subtask_list,
        })
    ctx.write_text("wbs_level2.json", json.dumps(major_phases_with_subtasks, indent=2))
