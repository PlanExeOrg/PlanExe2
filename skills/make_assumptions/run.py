import json
from datetime import datetime

from planexe_skill.planexe import raw_document, structured

ITEM_KEYS = ("question", "assumptions", "assessments")


def normalize(r: dict) -> dict:
    items = []
    for i, item in enumerate(r.get("question_assumption_list") or [], start=1):
        d = {"item_index": item.get("item_index", i)}
        d.update({k: str(item.get(k) or "") for k in ITEM_KEYS})
        items.append(d)
    return {"question_assumption_list": items}


def to_markdown(d: dict) -> str:
    rows = []
    if d["question_assumption_list"]:
        for index, item in enumerate(d["question_assumption_list"], start=1):
            rows.append(f"\n## Question {index} - {item['question']}")
            rows.append(f"\n**Assumptions:** {item['assumptions']}")
            rows.append(f"\n**Assessments:** {item['assessments']}")
    else:
        rows.append("The 'question-assumption-list' is empty. Finding zero questions for a plan is unusual, "
                    "this is likely a bug. Please report this issue to the developer of PlanExe.")
    return "\n".join(rows)


def run(ctx):
    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}\n\n"
        f"File 'plan_type.md':\n{ctx.read_text('plan_type.md')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'physical_locations.md':\n{ctx.read_text('physical_locations.md')}\n\n"
        f"File 'currency_strategy.md':\n{ctx.read_text('currency_strategy.md')}\n\n"
        f"File 'identify_risks.md':\n{ctx.read_text('identify_risks.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    system_prompt = system_prompt.replace("CURRENT_YEAR_PLACEHOLDER", str(datetime.now().year))
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = normalize(response)
    assumptions = [{k: item[k] for k in ITEM_KEYS} for item in response["question_assumption_list"]]
    ctx.write_json("make_assumptions_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("make_assumptions.json", json.dumps(assumptions, indent=2))
    ctx.write_text("make_assumptions.md", to_markdown(response))
