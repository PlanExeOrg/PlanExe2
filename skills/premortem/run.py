import json

from planexe_skill.planexe import planexe_metadata, structured
from planexe_skill.shared.final_review import QUESTIONS_AND_ANSWERS, REVIEW_PLAN, build_query, transcript

FOLLOWUP_PROMPTS = [
    "Generate 3 new assumptions that are thematically different from the previous ones. Start assumption_id at A4.",
    "Generate 3 new assumptions that are thematically different from the previous ones and covers different archetypes. Start assumption_id at A7.",
]
ASSUMPTION_KEYS = ("assumption_id", "statement", "test_now", "falsifier")


def _opt_int(v):
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _opt_list(v):
    if v is None:
        return None
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v]


def normalize(response: dict) -> dict:
    """Mirror PremortemAnalysis.model_dump(): every field present (optional ones as null)."""
    assumptions = [{k: str(a.get(k) or "") for k in ASSUMPTION_KEYS}
                   for a in response.get("assumptions_to_kill") or [] if isinstance(a, dict)]
    failure_modes = []
    for i, f in enumerate(response.get("failure_modes") or [], start=1):
        if not isinstance(f, dict):
            continue
        failure_modes.append({
            "failure_mode_index": _opt_int(f.get("failure_mode_index")) or i,
            "root_cause_assumption_id": str(f.get("root_cause_assumption_id") or ""),
            "failure_mode_archetype": str(f.get("failure_mode_archetype") or ""),
            "failure_mode_title": str(f.get("failure_mode_title") or ""),
            "risk_analysis": str(f.get("risk_analysis") or ""),
            "early_warning_signs": _opt_list(f.get("early_warning_signs")) or [],
            "owner": f.get("owner") if f.get("owner") is None else str(f.get("owner")),
            "likelihood_5": _opt_int(f.get("likelihood_5")),
            "impact_5": _opt_int(f.get("impact_5")),
            "tripwires": _opt_list(f.get("tripwires")),
            "playbook": _opt_list(f.get("playbook")),
            "stop_rule": f.get("stop_rule") if f.get("stop_rule") is None else str(f.get("stop_rule")),
        })
    return {"assumptions_to_kill": assumptions, "failure_modes": failure_modes}


def drop_repeated(response: dict, previous: list[dict]) -> dict:
    """Haiku sometimes answers a follow-up by repeating the earlier assumptions (A1-A3) before the
    new ones. Drop assumptions whose id was already used by an earlier response, and the failure
    modes rooted in them, so the merged premortem has no duplicate ids."""
    seen = {a["assumption_id"] for r in previous for a in r["assumptions_to_kill"]}
    if not seen:
        return response
    return {"assumptions_to_kill": [a for a in response["assumptions_to_kill"] if a["assumption_id"] not in seen],
            "failure_modes": [f for f in response["failure_modes"] if f["root_cause_assumption_id"] not in seen]}


def _classify(score: int) -> str:
    if score >= 15:
        return "CRITICAL"
    if score >= 9:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def risk_level_brief(likelihood, impact) -> str:
    if likelihood is None or impact is None:
        return "Not Scored"
    score = likelihood * impact
    return f"{_classify(score)} ({score}/25)"


def risk_level_verbose(likelihood, impact) -> str:
    if likelihood is None or impact is None:
        return f"Likelihood {likelihood}/5, Impact {impact}/5"
    score = likelihood * impact
    return f"{_classify(score)} {score}/25 (Likelihood {likelihood}/5 × Impact {impact}/5)"


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def to_markdown(d: dict) -> str:
    rows = []
    rows.append("A premortem assumes the project has failed and works backward to identify the most likely causes.\n")
    rows.append("## Assumptions to Kill\n")
    rows.append("These foundational assumptions represent the project's key uncertainties. If proven false, they could lead to failure. Validate them immediately using the specified methods.\n")
    rows.append("| ID | Assumption | Validation Method | Failure Trigger |")
    rows.append("|----|------------|-------------------|-----------------|")
    for a in d["assumptions_to_kill"]:
        rows.append(f"| {a['assumption_id']} | {a['statement']} | {a['test_now']} | {a['falsifier']} |")
    rows.append("\n")

    rows.append("## Failure Scenarios and Mitigation Plans\n")
    rows.append("Each scenario below links to a root-cause assumption and includes a detailed failure story, early warning signs, measurable tripwires, a response playbook, and a stop rule to guide decision-making.\n")
    rows.append("### Summary of Failure Modes\n")
    rows.append("| ID | Title | Archetype | Root Cause | Owner | Risk Level |")
    rows.append("|----|-------|-----------|------------|-------|------------|")
    for index, fm in enumerate(d["failure_modes"], start=1):
        rows.append(f"| FM{index} | {fm['failure_mode_title']} | {fm['failure_mode_archetype']} | "
                    f"{fm['root_cause_assumption_id']} | {fm['owner'] or 'Unassigned'} | "
                    f"{risk_level_brief(fm['likelihood_5'], fm['impact_5'])} |")
    rows.append("\n")

    rows.append("### Failure Modes\n")
    for index, fm in enumerate(d["failure_modes"], start=1):
        if index > 1:
            rows.append("---\n")
        rows.append(f"#### FM{index} - {fm['failure_mode_title']}\n")
        rows.append(f"- **Archetype**: {fm['failure_mode_archetype']}")
        rows.append(f"- **Root Cause**: Assumption {fm['root_cause_assumption_id']}")
        rows.append(f"- **Owner**: {fm['owner'] or 'Unassigned'}")
        rows.append(f"- **Risk Level:** {risk_level_verbose(fm['likelihood_5'], fm['impact_5'])}\n")
        rows.append("##### Failure Story")
        rows.append(f"{fm['risk_analysis']}\n")
        rows.append("##### Early Warning Signs")
        rows.append(bullet_list(fm["early_warning_signs"]))
        rows.append("\n##### Tripwires")
        rows.append(bullet_list(fm["tripwires"] or ["No tripwires defined"]))
        rows.append("\n##### Response Playbook")
        rows.append(bullet_list(fm["playbook"] or ["No response actions defined"]))
        rows.append("\n")
        rows.append(f"**STOP RULE:** {fm['stop_rule'] or 'Not specified'}\n")
    return "\n".join(rows)


def run(ctx):
    user_prompt = build_query(ctx, [REVIEW_PLAN, QUESTIONS_AND_ANSWERS])
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")

    # PlanExe: one accumulating chat [system, user(query), assistant(r1), user(A4 prompt), assistant(r2),
    # user(A7 prompt)]. Sequential: every follow-up sees the previous responses. A failed follow-up is
    # skipped (its prompt is not kept in the history); a failed first call fails the stage.
    history: list[tuple[str, str]] = []
    responses: list[dict] = []
    metadata_list: list[dict] = []
    prompts = [None, *FOLLOWUP_PROMPTS]
    for index, followup in enumerate(prompts):
        if followup is None:
            prompt = user_prompt
        else:
            prompt = transcript(history, followup, initial=user_prompt)
        try:
            raw, result = structured(ctx, system_prompt, prompt, schema, label=f"call {index + 1}")
        except Exception as e:
            if index == 0:
                raise
            ctx.log(f"User prompt {index + 1} failed ({e}). Continuing with next user prompt.")
            continue
        response = drop_repeated(normalize(raw), responses)
        if index > 0 and not response["assumptions_to_kill"]:
            ctx.log(f"User prompt {index + 1} only repeated earlier assumptions. Continuing with next user prompt.")
            continue
        content = json.dumps(response, separators=(',', ':'))
        if followup is not None:
            history.append(("User", followup))
        history.append(("Assistant", content))
        responses.append(response)
        meta = planexe_metadata(result)
        meta.pop("response_byte_count", None)
        metadata_list.append(meta)

    final = {"assumptions_to_kill": [a for r in responses for a in r["assumptions_to_kill"]],
             "failure_modes": [f for r in responses for f in r["failure_modes"]]}
    markdown = to_markdown(final)
    raw_doc = dict(final)
    raw_doc["metadata"] = {"models": metadata_list,
                           "response_byte_count": len(json.dumps(final).encode("utf-8"))}
    raw_doc["system_prompt"] = system_prompt
    raw_doc["user_prompt"] = user_prompt
    raw_doc["markdown"] = markdown
    ctx.write_json("premortem_raw.json", raw_doc)
    ctx.write_text("premortem.md", markdown)
