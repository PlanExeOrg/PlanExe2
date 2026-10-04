from planexe_skill.planexe import raw_document, structured

LIST_FIELDS = ["data_to_collect", "simulation_steps", "expert_validation_steps", "responsible_parties", "notes"]
SENSITIVITY = {"low", "medium", "high"}


def normalize(response: dict) -> dict:
    items = []
    for i, item in enumerate(response.get("data_collection_list") or [], start=1):
        if not isinstance(item, dict):
            continue
        d = {"item_index": item.get("item_index", i), "title": str(item.get("title", ""))}
        for k in ("data_to_collect", "simulation_steps", "expert_validation_steps"):
            d[k] = [str(x) for x in item.get(k) or []]
        d["rationale"] = str(item.get("rationale", ""))
        d["responsible_parties"] = [str(x) for x in item.get("responsible_parties") or []]
        assumptions = []
        for j, a in enumerate(item.get("assumptions") or [], start=1):
            if not isinstance(a, dict):
                continue
            score = str(a.get("sensitivity_score", "")).strip().lower()
            if score not in SENSITIVITY:
                raise ValueError(f"invalid sensitivity_score: {a.get('sensitivity_score')!r}")
            assumptions.append({"item_index": a.get("item_index", j), "assumption": str(a.get("assumption", "")),
                                "sensitivity_score": score})
        d["assumptions"] = assumptions
        d["smart_validation_objective"] = str(item.get("smart_validation_objective", ""))
        d["notes"] = [str(x) for x in item.get("notes") or []]
        items.append(d)
    return {"data_collection_list": items, "summary": str(response.get("summary", ""))}


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def to_markdown(doc: dict) -> str:
    rows = []
    for item_index, item in enumerate(doc["data_collection_list"], start=1):
        if item_index > 1:
            rows.append("\n")
        rows.append(f"## {item_index}. {item['title']}\n")
        rows.append(item["rationale"])
        rows.append(f"\n### Data to Collect\n\n{bullets(item['data_to_collect'])}")
        rows.append(f"\n### Simulation Steps\n\n{bullets(item['simulation_steps'])}")
        rows.append(f"\n### Expert Validation Steps\n\n{bullets(item['expert_validation_steps'])}")
        rows.append(f"\n### Responsible Parties\n\n{bullets(item['responsible_parties'])}")
        assumption_list = [f"**{a['sensitivity_score'].capitalize()}:** {a['assumption']}" for a in item["assumptions"]]
        rows.append(f"\n### Assumptions\n\n{bullets(assumption_list)}")
        rows.append(f"\n### SMART Validation Objective\n\n{item['smart_validation_objective']}")
        rows.append(f"\n### Notes\n\n{bullets(item['notes'])}")
    rows.append(f"\n## Summary\n\n{doc['summary']}")
    return "\n".join(rows)


def run(ctx):
    user_prompt = (
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}\n\n"
        f"File 'assumptions.md':\n{ctx.read_text('consolidate_assumptions_short.md')}\n\n"
        f"File 'project-plan.md':\n{ctx.read_text('project_plan.md')}\n\n"
        f"File 'related-resources.md':\n{ctx.read_text('related_resources.md')}\n\n"
        f"File 'swot-analysis.md':\n{ctx.read_text('swot_analysis.md')}\n\n"
        f"File 'team.md':\n{ctx.read_text('team.md')}\n\n"
        f"File 'expert-review.md':\n{ctx.read_text('expert_criticism.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    doc = normalize(response)
    ctx.write_json("data_collection_raw.json", raw_document(doc, result, system_prompt, user_prompt))
    ctx.write_text("data_collection.md", to_markdown(doc))
