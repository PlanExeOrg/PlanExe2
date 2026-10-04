"""Shared code for the team stages (find_team_members, enrich_team_members_with_*, review_team).

Mirrors PlanExe's worker_plan_internal/team/* and the node wrappers in
worker_plan_internal/plan/nodes/{find_team_members,enrich_team_*,review_team}.py.
"""
from __future__ import annotations

from planexe_skill.planexe import format_json_for_query, raw_document, structured

# The files every team node reads (in addition to its team-specific input).
CONTEXT_INPUTS = [
    "plan.txt",
    "strategic_decisions.md",
    "scenarios.md",
    "consolidate_assumptions_short.md",
    "pre_project_assessment.json",
    "project_plan.md",
    "related_resources.md",
]


def build_query(ctx, team_section: tuple[str, str] | None = None) -> str:
    """The user prompt the PlanExe team nodes assemble. `team_section` = (filename, content) is
    inserted between 'project-plan.md' and 'related-resources.md'."""
    parts = [
        f"File 'initial-plan.txt':\n{ctx.read_text('plan.txt')}",
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}",
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}",
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}",
        f"File 'pre-project-assessment.json':\n{format_json_for_query(ctx.read_json('pre_project_assessment.json'))}",
        f"File 'project-plan.md':\n{ctx.read_text('project_plan.md')}",
    ]
    if team_section is not None:
        parts.append(f"File '{team_section[0]}':\n{team_section[1]}")
    parts.append(f"File 'related-resources.md':\n{ctx.read_text('related_resources.md')}")
    return "\n\n".join(parts)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def enrich(ctx, input_name: str, raw_name: str, clean_name: str, field_map: dict[str, str]) -> None:
    """One structured call enriching every team member, then merge by id (PlanExe's
    cleanup_*_and_merge_with_team_members). `field_map` maps team-member key -> response field."""
    team_member_list = ctx.read_json(input_name)
    user_prompt = build_query(ctx, ("team-members-that-needs-to-be-enriched.json",
                                    format_json_for_query(team_member_list)))
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))

    # Normalize the response like pydantic's model_dump: ids coerced to int, only schema keys kept.
    items = []
    for item in response.get("team_members") or []:
        if not isinstance(item, dict):
            continue
        d = {"id": _as_int(item.get("id"))}
        for field in field_map.values():
            d[field] = item.get(field)
        items.append(d)
    response = {"team_members": items}

    id_to_enriched = {item["id"]: item for item in items}
    result_list = list(team_member_list)
    for index, team_member in enumerate(result_list):
        if "id" not in team_member:
            ctx.log(f"Team member #{index} does not have an id")
            continue
        enriched = id_to_enriched.get(team_member["id"])
        if enriched:
            for key, field in field_map.items():
                team_member[key] = enriched[field]

    ctx.write_json(raw_name, raw_document(response, result, system_prompt, user_prompt))
    ctx.write_json(clean_name, result_list)
