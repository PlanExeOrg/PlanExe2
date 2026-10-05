import json

from planexe_skill.calendar_fix import fix_text
from planexe_skill.planexe import structured

# repairable document -> keywords that identify it in a diagnostic's `offending_document`
REPAIRABLE = {
    "executive_summary.md": ["executive"],
    "project_plan.md": ["project plan", "project_plan"],
    "pitch.md": ["pitch"],
    "review_plan.md": ["review_plan", "review plan", "plan review"],
    "premortem.md": ["premortem"],
    "self_audit.md": ["self_audit", "self-audit", "self audit"],
    "questions_and_answers.md": ["questions_and_answers", "q&a", "questions and answers"],
}


def diagnostics_by_document(review: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for i, c in enumerate(review.get("contradictions") or [], start=1):
        if c.get("severity") not in ("high", "medium"):
            continue
        where = f"{c.get('offending_document', '')}".lower()
        for doc, keys in REPAIRABLE.items():
            if any(k in where for k in keys):
                out.setdefault(doc, []).append({"id": f"CF-{i:03d}", **c})
    return out


def describe(diags: list[dict]) -> str:
    lines = []
    for d in diags:
        lines.append(f"- {d['id']} ({d['severity']}) {d['topic']}\n"
                     f"  canonical: {d.get('canonical_key', '')} = {d.get('canonical_value', '')}\n"
                     f"  observed in this document: {d.get('observed_value', '')}\n"
                     f"  resolution: {d.get('suggested_resolution', '')}")
    return "\n".join(lines)


def apply_edits(text: str, edits: list[dict]) -> tuple[str, list[dict]]:
    log = []
    for e in edits:
        find, repl = e.get("find", ""), e.get("replace", "")
        n = text.count(find) if find else 0
        if n:
            text = text.replace(find, repl)
        log.append({"diagnostic": e.get("diagnostic", ""), "applied": n, "find": find[:200]})
    return text, log


def run(ctx):
    review = ctx.read_json("consistency_review_raw.json")
    todo = diagnostics_by_document(review)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")

    def repair(doc: str) -> tuple[str, dict]:
        text = ctx.read_text(doc)
        diags = todo.get(doc) or []
        if not diags:
            return doc, {"document": doc, "diagnostics": 0, "edits": []}
        user = f"# Diagnostics\n{describe(diags)}\n\n# Document '{doc}'\n{text}"
        try:
            response, _ = structured(ctx, system_prompt, user, schema, label=doc)
        except Exception as e:  # a failed repair keeps the original document
            ctx.log(f"repair of {doc} failed: {e}")
            return doc, {"document": doc, "diagnostics": len(diags), "error": str(e)[:300], "edits": []}
        new_text, log = apply_edits(text, response.get("edits") or [])
        if ctx.project_start is not None:
            new_text, _ = fix_text(new_text, ctx.project_start)
        ctx.write_text(f"repaired_{doc}", new_text)
        return doc, {"document": doc, "diagnostics": len(diags), "edits": log}

    results = dict(ctx.map(repair, list(REPAIRABLE)))
    for doc in REPAIRABLE:
        if not ctx.exists(f"repaired_{doc}"):
            ctx.write_text(f"repaired_{doc}", ctx.read_text(doc))
    ctx.write_text("consistency_repair_raw.json", json.dumps({"documents": list(results.values())}, indent=2,
                                                              ensure_ascii=False))
