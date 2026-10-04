from planexe_skill.planexe import raw_document, structured

VERDICT_DISPLAY = {"ALLOW": "🟢 ALLOW", "ALLOW_WITH_SAFETY_FRAMING": "🟡 ALLOW WITH SAFETY FRAMING",
                   "REFUSE": "🔴 REFUSE"}


def to_markdown(d: dict) -> str:
    verdict = VERDICT_DISPLAY.get(d["verdict"], f"❓ {d['verdict']}")
    parts = [f"**Verdict:** {verdict}\n", f"**Rationale:** {d.get('rationale_short', 'The prompt is safe')}"]
    details = []
    if d.get("violation_category"):
        details.append(f"| **Category**              | {d['violation_category']} |")
    if d.get("violation_claim"):
        details.append(f"| **Claim**                 | {d['violation_claim']} |")
    if d.get("violation_capability_uplift") is not None:
        details.append(f"| **Capability Uplift**     | {'Yes' if d['violation_capability_uplift'] else 'No'} |")
    if d.get("violation_severity"):
        details.append(f"| **Severity**              | {d['violation_severity']} |")
    if details:
        parts.append("\n### Violation Details\n")
        parts.append("| Detail                | Value |")
        parts.append("|-----------------------|-------|")
        parts.extend(details)
    return "\n".join(parts)


def run(ctx):
    plan = ctx.read_text("plan.txt")
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, plan, ctx.skill_json("schema.json"))
    # Same field order / defaults as PlanExe's pydantic model_dump().
    full = {"verdict": response["verdict"],
            "rationale_short": response.get("rationale_short", "The prompt is safe"),
            "violation_category": response.get("violation_category"),
            "violation_claim": response.get("violation_claim"),
            "violation_capability_uplift": response.get("violation_capability_uplift"),
            "violation_severity": response.get("violation_severity")}
    ctx.write_json("redline_gate_raw.json", raw_document(full, result, system_prompt, plan))
    ctx.write_text("redline_gate.md", to_markdown(full))
