from planexe_skill.planexe import raw_document, structured
from planexe_skill.shared.team import build_query
from planexe_skill.shared.team_markdown_document import TeamMarkdownDocumentBuilder


def _items(value) -> list[dict]:
    return [{
        "issue": str(item.get("issue", "")),
        "explanation": str(item.get("explanation", "")),
        "recommendation": str(item.get("recommendation", "")),
    } for item in value or [] if isinstance(item, dict)]


def run(ctx):
    builder = TeamMarkdownDocumentBuilder()
    builder.append_roles(ctx.read_json("enrich_team_members_environment_info.json"), title=None)
    user_prompt = build_query(ctx, ("team-members.md", builder.to_string()))
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    response = {
        "omissions": _items(response.get("omissions")),
        "potential_improvements": _items(response.get("potential_improvements")),
    }
    ctx.write_json("review_team_raw.json", raw_document(response, result, system_prompt, user_prompt))
