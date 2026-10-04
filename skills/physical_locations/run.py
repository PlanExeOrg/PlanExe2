from planexe_skill.planexe import raw_document, structured

DIGITAL_TEXT = "The plan is purely digital, without any physical locations."
LOCATION_KEYS = ("physical_location_broad", "physical_location_detailed", "physical_location_specific",
                 "rationale_for_suggestion")


def normalize(r: dict) -> dict:
    """Mirror pydantic's model_dump: every field present, in schema order."""
    locations = []
    for i, loc in enumerate(r.get("physical_locations") or [], start=1):
        item = {"item_index": loc.get("item_index", i)}
        item.update({k: str(loc.get(k) or "") for k in LOCATION_KEYS})
        locations.append(item)
    return {
        "has_location_in_plan": bool(r.get("has_location_in_plan")),
        "requirements_for_the_physical_locations": list(r.get("requirements_for_the_physical_locations") or []),
        "physical_locations": locations,
        "location_summary": str(r.get("location_summary") or ""),
    }


def to_markdown(d: dict) -> str:
    rows = []
    if d["has_location_in_plan"]:
        rows.append("This plan implies one or more physical locations.")
    else:
        rows.append("This plan **does not** imply any physical location.")

    if d["requirements_for_the_physical_locations"]:
        rows.append("\n## Requirements for physical locations\n")
        for requirement in d["requirements_for_the_physical_locations"]:
            rows.append(f"- {requirement}")
    else:
        rows.append("No requirements for the physical location.")

    for location_index, location in enumerate(d["physical_locations"], start=1):
        rows.append(f"\n## Location {location_index}")
        broad = location["physical_location_broad"].strip()
        detailed = location["physical_location_detailed"].strip()
        specific = location["physical_location_specific"].strip()
        if broad:
            rows.append(f"{broad}\n")
        if detailed:
            rows.append(f"{detailed}\n")
        if specific:
            rows.append(f"{specific}\n")
        if not (broad or detailed or specific):
            rows.append("Missing location info.\n")
        rows.append(f"**Rationale**: {location['rationale_for_suggestion']}")

    rows.append(f"\n## Location Summary\n{d['location_summary']}")
    return "\n".join(rows)


def run(ctx):
    plan_type = ctx.read_json("plan_type_raw.json").get("plan_type")
    if plan_type != "physical":
        ctx.write_json("physical_locations_raw.json", {"comment": DIGITAL_TEXT})
        ctx.write_text("physical_locations.md", DIGITAL_TEXT)
        return

    query = (
        f"File 'plan.txt':\n{ctx.read_text('plan.txt')}\n\n"
        f"File 'purpose.md':\n{ctx.read_text('identify_purpose.md')}\n\n"
        f"File 'plan_type.md':\n{ctx.read_text('plan_type.md')}\n\n"
        f"File 'strategic_decisions.md':\n{ctx.read_text('strategic_decisions.md')}\n\n"
        f"File 'scenarios.md':\n{ctx.read_text('scenarios.md')}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, query, ctx.skill_json("schema.json"))
    response = normalize(response)
    ctx.write_json("physical_locations_raw.json", raw_document(response, result, system_prompt, query))
    ctx.write_text("physical_locations.md", to_markdown(response))
