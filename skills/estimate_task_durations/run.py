import json

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured
from planexe_skill.shared.schedule.wbs_task import WBSProject

CHUNK_SIZE = 3


def format_query(plan_json: dict, wbs_level2_json: list, task_ids: list[str]) -> str:
    task_id_strings = "\n".join(f'"{task_id}"' for task_id in task_ids)
    return f"""
The project plan:
{format_json_for_query(plan_json)}

The Work Breakdown Structure (WBS):
{format_json_for_query(wbs_level2_json)}

Only estimate these {len(task_ids)} tasks:
{task_id_strings}
"""


def to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return -1


def run(ctx):
    project_plan_dict = ctx.read_json("project_plan_raw.json")
    wbs_project = WBSProject.from_dict(ctx.read_json("wbs_project_level1_and_level2.json"))
    major_phases_with_subtasks = [child.to_dict() for child in wbs_project.root_task.task_children]

    # Don't include the uuid of the root task. It's the child tasks that are of interest to estimate.
    task_ids = []
    for task in wbs_project.root_task.task_children:
        task_ids.extend(task.task_ids())
    chunks = [task_ids[i:i + CHUNK_SIZE] for i in range(0, len(task_ids), CHUNK_SIZE)]
    ctx.log(f"There are {len(task_ids)} tasks to be estimated, in {len(chunks)} chunks.")

    preamble = ctx.skill_file("prompts/query_preamble.md")
    schema = ctx.skill_json("schema.json")

    def estimate(indexed):
        index, chunk = indexed
        query = format_query(project_plan_dict, major_phases_with_subtasks, chunk)
        try:
            # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
            response, result = structured(ctx, "", preamble + query, schema,
                                          label=f"chunk {index} of {len(chunks)}")
        except Exception as e:
            raise ValueError(f"Task durations chunk {index} LLM interaction failed.") from e
        details = []
        for item in response.get("task_details") or []:
            details.append({
                "task_id": str(item.get("task_id", "")),
                "delay_risks": str(item.get("delay_risks") or ""),
                "mitigation_strategy": str(item.get("mitigation_strategy") or ""),
                "days_min": to_int(item.get("days_min")),
                "days_max": to_int(item.get("days_max")),
                "days_realistic": to_int(item.get("days_realistic")),
            })
        metadata = planexe_metadata(result)
        metadata.pop("response_byte_count", None)
        raw = {"task_details": details, "metadata": metadata, "query": query}
        ctx.write_text(f"task_durations_{index}_raw.json", json.dumps(raw, indent=2))
        return details

    results = ctx.map(estimate, list(enumerate(chunks, start=1)))
    accumulated = [d for details in results for d in details]
    ctx.write_text("task_durations.json", json.dumps(accumulated, indent=2))
