import json

from planexe_skill.planexe import planexe_metadata, structured

LEVER_KEYS = ("lever_id", "name", "consequences", "options", "review")


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    raw_levers = ctx.read_json("potential_levers.json")
    project_context = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}"
    )
    # InputLever(**lever).model_dump(): exactly these keys, in this order.
    input_levers = [{k: lever[k] for k in LEVER_KEYS} for lever in raw_levers]
    if not input_levers:
        raise ValueError("No input levers to deduplicate.")

    system_prompt = ctx.skill_file("prompts/system.md").strip()
    levers_json = json.dumps(input_levers, indent=2)
    user_prompt = (
        f"**Project Context:**\n{project_context}\n\n"
        f"**Levers to classify ({len(input_levers)} total):**\n{levers_json}\n\n"
        f"Classify every lever as primary, secondary, or remove."
    )

    batch_decisions = None
    metadata_list: list[dict] = []
    try:
        response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
        batch_decisions = response.get("decisions") or []
        meta = planexe_metadata(result)
        meta.pop("duration", None)
        meta.pop("response_byte_count", None)
        metadata_list.append(meta)
    except Exception as e:  # PlanExe logs and keeps everything as secondary
        ctx.log(f"Batch deduplication call failed: {e}")

    input_ids = {lv["lever_id"] for lv in input_levers}
    decisions: list[dict] = []
    seen: set[str] = set()
    for d in batch_decisions or []:
        lever_id = d.get("lever_id")
        if lever_id not in input_ids:
            ctx.log(f"LLM returned classification for unknown lever_id: '{lever_id}'. Skipping.")
            continue
        if lever_id in seen:
            ctx.log(f"LLM returned duplicate lever_id: '{lever_id}'. Keeping first entry.")
            continue
        seen.add(lever_id)
        decisions.append({"lever_id": lever_id, "classification": d["classification"],
                          "justification": str(d.get("justification", ""))})
    for lever in input_levers:
        if lever["lever_id"] not in seen:
            decisions.append({"lever_id": lever["lever_id"], "classification": "secondary",
                              "justification": "Not classified by LLM. Keeping as secondary to avoid data loss."})

    by_id = {d["lever_id"]: d for d in decisions}
    triaged = []
    for lever in input_levers:
        decision = by_id[lever["lever_id"]]
        if decision["classification"] == "remove":
            continue
        justification = decision["justification"].strip() or "Empty explanation. Keeping this lever."
        triaged.append({**lever, "classification": decision["classification"],
                        "deduplication_justification": justification})

    min_expected = max(3, len(input_levers) // 4)
    if len(triaged) < min_expected:
        ctx.log(f"Only {len(triaged)} levers survived deduplication (expected at least {min_expected}).")

    raw = {
        "response": decisions,
        "triaged_levers": triaged,
        "metadata": metadata_list,
        "system_prompt": system_prompt,
        "user_prompt": project_context,
    }
    ctx.write_text("triaged_levers_raw.json", json.dumps(raw, indent=2))
