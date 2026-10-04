import json
from uuid import uuid4

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured
from planexe_skill.shared.schedule.wbs_populate import WBSPopulate
from planexe_skill.shared.schedule.wbs_task import WBSProject


def run(ctx):
    project_plan_dict = ctx.read_json("project_plan_raw.json")
    wbs_project = WBSProject.from_dict(ctx.read_json("wbs_project_level1_and_level2.json"))
    data_collection_markdown = ctx.read_text("data_collection.md")
    WBSPopulate.extend_project_with_durations_json(wbs_project, str(ctx.path("task_durations.json")))

    # The tasks without children are the ones to decompose.
    leaves = []

    def visit_task(task):
        if len(task.task_children) == 0:
            leaves.append(task)
        else:
            for child in task.task_children:
                visit_task(child)
    visit_task(wbs_project.root_task)
    task_ids = [task.id for task in leaves]
    ctx.log(f"There are {len(task_ids)} tasks to be decomposed.")

    project_plan_str = format_json_for_query(project_plan_dict)
    wbs_project_str = format_json_for_query(wbs_project.to_dict())
    preamble = ctx.skill_file("prompts/query_preamble.md")
    schema = ctx.skill_json("schema.json")

    def decompose(indexed):
        index, task_id = indexed
        query = (
            f"The project plan:\n{project_plan_str}\n\n"
            f"Data collection:\n{data_collection_markdown}\n\n"
            f"Work breakdown structure:\n{wbs_project_str}\n\n"
            f"Only decompose this task:\n\"{task_id}\""
        )
        try:
            # PlanExe calls sllm.complete(QUERY_PREAMBLE + query) without a system message.
            response, result = structured(ctx, "", preamble + query, schema,
                                          label=f"task {index} of {len(task_ids)}")
        except Exception as e:
            raise ValueError(f"WBS Level 3 task {index} LLM interaction failed.") from e
        subtasks = []
        for s in response.get("subtasks") or []:
            resources = s.get("resources_needed")
            subtasks.append({
                "name": str(s.get("name", "")),
                "description": str(s.get("description", "")),
                "resources_needed": [str(x) for x in resources] if isinstance(resources, list) else [],
            })
        metadata = planexe_metadata(result)
        metadata.pop("response_byte_count", None)
        raw = {"subtasks": subtasks, "metadata": metadata, "query": query}
        ctx.write_text(f"wbs_level3_{index}_raw.json", json.dumps(raw, indent=2))
        # Cleanup: assign unique ids to each subtask.
        return [{"id": str(uuid4()), "name": s["name"], "description": s["description"],
                 "resources_needed": s["resources_needed"], "parent_id": task_id} for s in subtasks]

    results = ctx.map(decompose, list(enumerate(task_ids, start=1)))
    accumulated = [t for tasks in results for t in tasks]
    ctx.write_text("wbs_level3.json", json.dumps(accumulated, indent=2))
