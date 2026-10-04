import json

from planexe_skill.planexe import format_json_for_query, planexe_metadata, structured


def normalize(response: dict) -> dict:
    """ScenarioSelectionResult.model_dump() shape (holistic_profile_of_the_plan defaults to "")."""
    pc = response.get("plan_characteristics") or {}
    fc = response.get("final_choice") or {}
    return {
        "plan_characteristics": {
            "ambition_and_scale": str(pc.get("ambition_and_scale", "")),
            "risk_and_novelty": str(pc.get("risk_and_novelty", "")),
            "complexity_and_constraints": str(pc.get("complexity_and_constraints", "")),
            "domain_and_tone": str(pc.get("domain_and_tone", "")),
            "holistic_profile_of_the_plan": str(pc.get("holistic_profile_of_the_plan") or ""),
        },
        "scenario_assessments": [{
            "scenario_name": str(a.get("scenario_name", "")),
            "fit_score": int(a.get("fit_score", 0)),
            "fit_assessment": str(a.get("fit_assessment", "")),
        } for a in response.get("scenario_assessments") or []],
        "final_choice": {
            "chosen_scenario_name": str(fc.get("chosen_scenario_name", "")),
            "justification": str(fc.get("justification", "")),
        },
    }


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    lever_item_list = ctx.read_json("vital_few_levers_raw.json")["levers"]
    scenarios = ctx.read_json("candidate_scenarios.json").get("scenarios", [])
    project_context = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}\n\n"
        f"File 'levers_vital_few.json':\n{format_json_for_query(lever_item_list)}\n\n"
        f"File 'candidate_scenarios.json':\n{format_json_for_query(scenarios)}"
    )
    if not scenarios:
        raise ValueError("Scenarios list cannot be empty.")
    user_prompt = (
        f"**Project Plan:**\n```\n{project_context}\n```\n\n"
        f"**Strategic Scenarios for Evaluation:**\n```json\n{json.dumps(scenarios, indent=2)}\n```\n\n"
        "Please perform the three-step analysis as instructed and provide the final `ScenarioSelectionResult` JSON."
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    response = normalize(response)
    meta = planexe_metadata(result)
    meta.pop("duration", None)
    meta.pop("response_byte_count", None)
    raw = {"response": response, "metadata": meta, "system_prompt": system_prompt, "user_prompt": user_prompt}
    ctx.write_text("selected_scenario_raw.json", json.dumps(raw, indent=2))
    ctx.write_text("selected_scenario.json", json.dumps(response, indent=2))
