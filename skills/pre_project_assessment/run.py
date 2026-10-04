import json
from datetime import datetime

from planexe_skill.planexe import raw_document, structured


def clean_assessment(response: dict) -> dict:
    """Flatten both experts' feedback; discard expert names and titles."""
    feedback = []
    for key in ("expert1", "expert2"):
        expert = response.get(key)
        if expert is None:
            continue
        for item in expert.get("feedback_item_list", []):
            feedback.append({"title": item.get("feedback_title", "Empty"),
                             "description": item.get("feedback_description", "Empty")})
    return {
        "go_no_go_recommendation": response.get("go_no_go_recommendation", "Empty"),
        "combined_summary": response.get("combined_summary", "Empty"),
        "feedback": feedback,
    }


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    system_prompt = system_prompt.replace("CURRENT_YEAR_PLACEHOLDER", str(datetime.now().year))
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    for key in ("combined_summary", "go_no_go_recommendation"):  # pydantic defaults of the optional fields
        response.setdefault(key, "")
    ctx.write_json("pre_project_assessment_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("pre_project_assessment.json", json.dumps(clean_assessment(response), indent=2))
