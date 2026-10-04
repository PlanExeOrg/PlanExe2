from planexe_skill.planexe import raw_document, structured
from planexe_skill.shared.team import build_query


def cleanup_team_members_and_assign_id(response: dict) -> list[dict]:
    result = []
    for i, tm in enumerate(response.get("brainstorm_of_needed_team_members") or [], start=1):
        result.append({
            "id": i,
            "category": tm["job_category_title"],
            "explanation": tm["short_explanation"],
            "consequences": tm["consequences_of_not_having_this_role"],
            "count": tm["people_needed"],
        })
    return result


def run(ctx):
    user_prompt = build_query(ctx)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    members = [{
        "job_category_title": str(tm.get("job_category_title", "")),
        "short_explanation": str(tm.get("short_explanation", "")),
        "people_needed": str(tm.get("people_needed", "")),
        "consequences_of_not_having_this_role": str(tm.get("consequences_of_not_having_this_role", "")),
    } for tm in response.get("brainstorm_of_needed_team_members") or [] if isinstance(tm, dict)]
    if not members:
        raise ValueError("find_team_members: the model returned no team members")
    response = {"brainstorm_of_needed_team_members": members}
    ctx.write_json("find_team_members_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_json("find_team_members.json", cleanup_team_members_and_assign_id(response))
