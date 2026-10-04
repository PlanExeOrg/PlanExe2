import json

from planexe_skill.planexe import planexe_metadata, structured


def normalize(response: dict) -> dict:
    """ScenarioAnalysisResult.model_dump() shape."""
    return {
        "analysis_title": str(response.get("analysis_title", "")),
        "core_tension": str(response.get("core_tension", "")),
        "scenarios": [{
            "scenario_name": str(s.get("scenario_name", "")),
            "strategic_logic": str(s.get("strategic_logic", "")),
            "lever_settings": {str(k): str(v) for k, v in (s.get("lever_settings") or {}).items()},
        } for s in response.get("scenarios") or []],
    }


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    vital_levers = ctx.read_json("vital_few_levers_raw.json")["levers"]
    if not vital_levers:
        raise ValueError("The list of vital levers cannot be empty.")
    project_context = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}\n\n"
    )
    formatted = []
    for lever in vital_levers:
        options_str = ", ".join(f"'{opt}'" for opt in lever["options"])
        formatted.append(
            f"**Lever: {lever['name']}**\n"
            f"  - Description: {lever['review']}\n"
            f"  - Options: [{options_str}]"
        )
    levers_prompt_text = "\n\n".join(formatted)
    user_prompt = (
        f"**Project Context:**\n{project_context}\n\n"
        "---\n\n"
        f"**Vital Levers & Options:**\n{levers_prompt_text}\n\n"
        "Please synthesize these levers into 3 distinct strategic scenarios as requested."
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    response = normalize(response)
    meta = planexe_metadata(result)
    meta.pop("duration", None)
    meta.pop("response_byte_count", None)
    raw = {"response": response, "metadata": meta, "system_prompt": system_prompt, "user_prompt": user_prompt}
    ctx.write_text("candidate_scenarios_raw.json", json.dumps(raw, indent=2))
    ctx.write_text("candidate_scenarios.json", json.dumps(response, indent=2))
