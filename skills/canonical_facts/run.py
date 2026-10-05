import json

from planexe_skill.planexe import structured

KIND_LABEL = {"user_constraint": "user constraint", "decision": "decision",
              "proposed_threshold": "proposed threshold", "estimate": "estimate"}


def to_markdown(r: dict) -> str:
    rows = ["## Canonical Facts", "",
            "Single source of truth for key numbers and dates. All later documents were instructed to use these values; the "
            "Consistency Check above lists any document that does not.", "",
            "| Fact | Value | Kind | Basis |", "|---|---|---|---|"]
    for f in r.get("facts") or []:
        cells = [f["key"], f["value"], KIND_LABEL.get(f["kind"], f["kind"]), f["basis"]]
        rows.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    rows += ["", r.get("reconciliation_notes", "")]
    return "\n".join(rows)


def run(ctx):
    names = ["plan.txt", "strategic_decisions.md", "scenarios.md", "consolidate_assumptions_short.md", "pre_project_assessment.json"]
    user_prompt = "\n\n".join(f"File '{n}':\n{ctx.read_text(n)}" for n in names)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    raw = {"facts": response.get("facts") or [], "reconciliation_notes": response.get("reconciliation_notes", ""),
           "metadata": result.metadata, "system_prompt": system_prompt, "user_prompt": user_prompt}
    ctx.write_text("canonical_facts.json", json.dumps(raw, indent=2, ensure_ascii=False))
    ctx.write_text("canonical_facts.md", to_markdown(response))
