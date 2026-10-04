import json
import uuid

from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared import constraint_checker

MIN_LEVERS = 15
MAX_CALLS = 5


def validate_lever(lever: dict) -> dict:
    """PlanExe's Lever validators: options may arrive as a stringified JSON array; >= 3 options;
    review_lever >= 10 chars and without square-bracket placeholders."""
    options = lever.get("options")
    if isinstance(options, str):
        try:
            parsed = json.loads(options)
            if isinstance(parsed, list):
                options = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    if not isinstance(options, list) or len(options) < 3:
        n = len(options) if isinstance(options, list) else 0
        raise ValueError(f"options must have at least 3 items, got {n}")
    review = str(lever.get("review_lever", ""))
    if len(review) < 10:
        raise ValueError(f"review_lever is too short ({len(review)} chars); expected at least 10")
    if "[" in review or "]" in review:
        raise ValueError("review_lever must not contain square-bracket placeholders")
    return {
        "lever_index": int(lever["lever_index"]),
        "name": str(lever["name"]),
        "consequences": str(lever["consequences"]),
        "options": [str(o) for o in options],
        "review_lever": review,
    }


def validate_document(doc: dict) -> dict:
    levers = [validate_lever(lv) for lv in doc.get("levers") or []]
    if len(levers) < 5:
        raise ValueError(f"levers must have at least 5 items, got {len(levers)}")
    return {"strategic_rationale": doc.get("strategic_rationale"), "levers": levers}


def check_constraints_on_response(ctx, constraints_markdown: str, doc: dict):
    """Run the constraint checker on each lever individually (independent calls, run concurrently).
    A failing check accepts the lever (as in PlanExe)."""
    constraints_json = json.dumps({"constraints_markdown": constraints_markdown})

    def check_one(lever: dict):
        lever_json = json.dumps({
            "lever_name": lever["name"],
            "consequences": lever["consequences"],
            "options": lever["options"],
            "review": lever["review_lever"],
        }, indent=2)
        try:
            d = constraint_checker.check(ctx, constraints_json, lever_json, f"lever: {lever['name']}",
                                         label=f"constraint check: {lever['name']}")
        except Exception as e:
            ctx.log(f"Constraint check failed for lever '{lever['name']}': {e}. Accepting lever.")
            return lever, None, {"lever_name": lever["name"], "status": "error", "error": str(e)}
        response = {k: d[k] for k in ("constraint_violations", "overall_status", "summary")}
        return lever, response, {"lever_name": lever["name"], **response}

    accepted, rejected, all_results = [], [], []
    for lever, response, record in ctx.map(check_one, doc["levers"]):
        all_results.append(record)
        violations = [v for v in (response or {}).get("constraint_violations", []) if v.get("status") == "violated"]
        if violations:
            rejected.append((lever, violations))
        else:
            accepted.append(lever)
    return accepted, rejected, all_results


def run(ctx):
    plan_prompt = ctx.read_text("plan.txt")
    classify_domain_markdown = ctx.read_text("classify_domain.md")
    identify_purpose_markdown = ctx.read_text("identify_purpose.md")
    plan_type_markdown = ctx.read_text("plan_type.md")
    constraints_markdown = ctx.read_text("extract_constraints.md")
    user_prompt = (
        f"File 'plan.txt':\n{plan_prompt}\n\n"
        f"File 'classify_domain.md':\n{classify_domain_markdown}\n\n"
        f"File 'purpose.md':\n{identify_purpose_markdown}\n\n"
        f"File 'plan_type.md':\n{plan_type_markdown}"
    )
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")

    responses: list[dict] = []
    metadata_list: list[dict] = []
    generated_lever_names: list[str] = []
    constraint_rejection_history: list[str] = []
    all_constraint_checks: list[dict] = []

    for call_index in range(1, MAX_CALLS + 1):
        if call_index == 1:
            prompt_content = user_prompt
        else:
            names_list = ", ".join(f'"{n}"' for n in generated_lever_names)
            prompt_content = (
                f"Generate 5 to 7 MORE levers with completely different names. "
                f"Do NOT reuse any of these already-generated names: [{names_list}]\n\n"
                f"{user_prompt}"
            )
        if constraint_rejection_history:
            rejection_text = "\n".join(constraint_rejection_history)
            prompt_content += (
                f"\n\n## Constraint Violation History\n"
                f"The following levers were REJECTED for violating constraints. "
                f"Do NOT generate levers that repeat these violations:\n{rejection_text}"
            )
        try:
            raw, result = structured(ctx, system_prompt, prompt_content, schema, label=f"call {call_index}")
            doc = validate_document(raw)
        except Exception as e:
            # PlanExe lets the adaptive loop retry; only a run with zero successful calls fails.
            if not responses and call_index == MAX_CALLS:
                raise
            ctx.log(f"Call {call_index} of {MAX_CALLS} failed ({e}); continuing with {len(responses)} prior call(s).")
            continue

        if constraints_markdown.strip():
            accepted, rejected, check_results = check_constraints_on_response(ctx, constraints_markdown, doc)
            all_constraint_checks.extend(check_results)
            if rejected:
                for lever, violations in rejected:
                    details = "; ".join(f"{v['constraint_text']}: {v['explanation']}" for v in violations)
                    constraint_rejection_history.append(f"- Lever \"{lever['name']}\" REJECTED: {details}")
                ctx.log(f"Call {call_index}: {len(rejected)} lever(s) rejected by constraint check, "
                        f"{len(accepted)} accepted.")
                doc = {**doc, "levers": accepted}

        generated_lever_names.extend(lv["name"] for lv in doc["levers"])
        responses.append(doc)
        meta = planexe_metadata(result)
        meta.pop("duration", None)
        meta.pop("response_byte_count", None)
        metadata_list.append(meta)
        if len(generated_lever_names) >= MIN_LEVERS:
            break

    seen_names: set[str] = set()
    levers_cleaned: list[dict] = []
    for response in responses:
        for lever in response["levers"]:
            if lever["name"] in seen_names:
                ctx.log(f"Duplicate lever name '{lever['name']}', skipping.")
                continue
            seen_names.add(lever["name"])
            levers_cleaned.append({
                "lever_id": str(uuid.uuid4()),
                "name": lever["name"],
                "consequences": lever["consequences"],
                "options": lever["options"],
                "review": lever["review_lever"],
            })

    raw_doc: dict = {"responses": responses, "levers": levers_cleaned}
    if all_constraint_checks:
        raw_doc["constraint_checks"] = all_constraint_checks
    raw_doc["metadata"] = {f"metadata_{i}": m for i, m in enumerate(metadata_list, start=1)}
    raw_doc["system_prompt"] = system_prompt
    raw_doc["user_prompt"] = user_prompt
    ctx.write_text("potential_levers_raw.json", json.dumps(raw_doc, indent=2))
    ctx.write_text("potential_levers.json", json.dumps(levers_cleaned, indent=2))
