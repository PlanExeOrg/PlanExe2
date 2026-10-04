def to_markdown(scenarios: list[dict], pc: dict, scenario_assessments: list[dict], final_choice: dict) -> str:
    assessments = {a["scenario_name"]: a for a in scenario_assessments}
    chosen = final_choice["chosen_scenario_name"]
    rows = ["# Choosing Our Strategic Path", "## The Strategic Context",
            "Understanding the core ambitions and constraints that guide our decision.\n",
            f"**Ambition and Scale:** {pc['ambition_and_scale']}\n",
            f"**Risk and Novelty:** {pc['risk_and_novelty']}\n",
            f"**Complexity and Constraints:** {pc['complexity_and_constraints']}\n",
            f"**Domain and Tone:** {pc['domain_and_tone']}\n",
            f"**Holistic Profile:** {pc['holistic_profile_of_the_plan']}\n",
            "---", "## The Path Forward",
            "This scenario aligns best with the project's characteristics and goals.\n"]
    selected = next((s for s in scenarios if s["scenario_name"] == chosen), None)
    if selected:
        rows.append(f"### {selected['scenario_name']}")
        rows.append(f"**Strategic Logic:** {selected['strategic_logic']}\n")
        if selected["scenario_name"] in assessments:
            a = assessments[selected["scenario_name"]]
            rows.append(f"**Fit Score:** {a['fit_score']}/10\n")
            rows.append(f"**Why This Path Was Chosen:** {a['fit_assessment']}\n")
        rows.append("**Key Strategic Decisions:**\n")
        for name, setting in selected["lever_settings"].items():
            rows.append(f"- **{name}:** {setting}")
        rows.append("")
        rows.append("**The Decisive Factors:**\n")
        rows.append(final_choice["justification"])
        rows.append("")
    rows.append("---")
    rows.append("## Alternative Paths")
    for s in scenarios:
        if s["scenario_name"] == chosen:
            continue
        rows.append(f"### {s['scenario_name']}")
        rows.append(f"**Strategic Logic:** {s['strategic_logic']}\n")
        if s["scenario_name"] in assessments:
            a = assessments[s["scenario_name"]]
            rows.append(f"**Fit Score:** {a['fit_score']}/10\n")
            rows.append(f"**Assessment of this Path:** {a['fit_assessment']}\n")
        rows.append("**Key Strategic Decisions:**\n")
        for name, setting in s["lever_settings"].items():
            rows.append(f"- **{name}:** {setting}")
        rows.append("")
    return "\n".join(rows)


def run(ctx):
    scenarios = ctx.read_json("candidate_scenarios.json").get("scenarios", [])
    selected = ctx.read_json("selected_scenario.json")
    ctx.write_text("scenarios.md", to_markdown(scenarios, selected.get("plan_characteristics", {}),
                                               selected.get("scenario_assessments", []),
                                               selected.get("final_choice", {})))
