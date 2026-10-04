from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared.final_review import REVIEW_PLAN, build_query, fix_bullet_lists

KEYS = ("audience_tailoring", "focus_and_context", "purpose_and_goals", "key_deliverables_and_outcomes",
        "timeline_and_budget", "risks_and_mitigations", "action_orientation", "overall_takeaway", "feedback")


def to_markdown(d: dict) -> str:
    rows = [
        f"## Focus and Context\n{d['focus_and_context']}",
        f"\n## Purpose and Goals\n{d['purpose_and_goals']}",
        f"\n## Key Deliverables and Outcomes\n{d['key_deliverables_and_outcomes']}",
        f"\n## Timeline and Budget\n{d['timeline_and_budget']}",
        f"\n## Risks and Mitigations\n{d['risks_and_mitigations']}",
        f"\n## Audience Tailoring\n{d['audience_tailoring']}",
        f"\n## Action Orientation\n{d['action_orientation']}",
        f"\n## Overall Takeaway\n{d['overall_takeaway']}",
        f"\n## Feedback\n{d['feedback']}",
    ]
    return fix_bullet_lists("\n".join(rows))


def run(ctx):
    user_prompt = build_query(ctx, [REVIEW_PLAN])
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    response = {k: str(response.get(k) or "") for k in KEYS}
    markdown = to_markdown(response)
    raw = dict(response)
    raw["markdown"] = markdown
    raw["metadata"] = planexe_metadata(result)
    raw["system_prompt"] = system_prompt
    raw["user_prompt"] = user_prompt
    ctx.write_json("executive_summary_raw.json", raw)
    ctx.write_text("executive_summary.md", markdown)
