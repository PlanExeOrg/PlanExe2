def lever_rows(rows: list[str], index: int, lever: dict, assessments: dict) -> None:
    rows.append(f"### Decision {index}: {lever['name']}")
    rows.append(f"**Lever ID:** `{lever['lever_id']}`\n")
    rows.append(f"**The Core Decision:** {lever['description']}\n")
    rows.append(f"**Why It Matters:** {lever['consequences']}\n")
    rows.append("**Strategic Choices:**\n")
    for option_index, option in enumerate(lever["options"], 1):
        rows.append(f"{option_index}. {option}")
    rows.append(f"\n**Trade-Off / Risk:** {lever['review']}\n")
    rows.append("**Strategic Connections:**\n")
    rows.append(f"**Synergy:** {lever['synergy_text']}\n")
    rows.append(f"**Conflict:** {lever['conflict_text']}\n")
    if lever["lever_id"] in assessments:
        a = assessments[lever["lever_id"]]
        rows.append(f"**Justification:** *{a['strategic_importance']}*, {a['justification']}\n")


def to_markdown(enrich_levers: list[dict], vital_levers: list[dict], summary: str, lever_assessments: list[dict]) -> str:
    assessments = {a["lever_id"]: a for a in lever_assessments or []}
    summary = summary.strip()
    rows = ["## Primary Decisions", "The vital few decisions that have the most impact.\n"]
    if summary:
        rows.append(f"\n{summary}\n")
    for i, lever in enumerate(vital_levers):
        lever_rows(rows, i + 1, lever, assessments)
    vital_ids = {lever["lever_id"] for lever in vital_levers}
    additional = [lever for lever in enrich_levers if lever["lever_id"] not in vital_ids]
    rows.append("---")
    rows.append("## Secondary Decisions")
    rows.append("These decisions are less significant, but still worth considering.\n")
    for i, lever in enumerate(additional):
        lever_rows(rows, len(vital_levers) + i + 1, lever, assessments)
    return "\n".join(rows)


def run(ctx):
    enrich_levers = ctx.read_json("enriched_levers_raw.json")["characterized_levers"]
    vital = ctx.read_json("vital_few_levers_raw.json")
    response = vital.get("response", {})
    ctx.write_text("strategic_decisions.md", to_markdown(enrich_levers, vital["levers"], response.get("summary", ""),
                                                         response.get("lever_assessments", [])))
