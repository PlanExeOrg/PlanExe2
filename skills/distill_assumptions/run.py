from datetime import datetime

from planexe_skill.planexe import format_json_for_query, raw_document, structured


def to_markdown(assumption_list: list) -> str:
    if not assumption_list:
        return ("**No distilled assumptions:** It's unusual that a plan has no assumptions. Please check if the "
                "input data is contains assumptions. Please report to the developer of PlanExe.")
    return "\n".join(f"- {a}" for a in assumption_list)


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.json':\n{format_json_for_query(ctx.read_json('make_assumptions.json'))}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    system_prompt = system_prompt.replace("CURRENT_YEAR_PLACEHOLDER", str(datetime.now().year))
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = {"assumption_list": [str(a) for a in (response.get("assumption_list") or [])]}
    ctx.write_json("distill_assumptions_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("distill_assumptions.md", to_markdown(response["assumption_list"]))
