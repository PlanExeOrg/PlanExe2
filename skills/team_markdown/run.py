from planexe_skill.shared.team_markdown_document import TeamMarkdownDocumentBuilder


def run(ctx):
    builder = TeamMarkdownDocumentBuilder()
    builder.append_team_member_subtitle()
    builder.append_roles(ctx.read_json("enrich_team_members_environment_info.json"))
    builder.append_separator()
    builder.append_full_review(ctx.read_json("review_team_raw.json"))
    ctx.write_text("team.md", builder.to_string())
