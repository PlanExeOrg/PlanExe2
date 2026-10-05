import json
from collections import Counter

from planexe_skill.calendar_fix import fix_text
from planexe_skill.planexe import structured
from planexe_skill.shared.consistency import review, to_markdown

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


MAX_ROUNDS = 3
RECHECK_DOCUMENTS = [
    ("Executive Summary", "repaired_executive_summary.md"),
    ("Project Plan", "repaired_project_plan.md"),
    ("Assumptions", "consolidate_assumptions_short.md"),
    ("Review Plan", "repaired_review_plan.md"),
    ("Premortem", "repaired_premortem.md"),
    ("Self Audit", "repaired_self_audit.md"),
    ("Pitch", "repaired_pitch.md"),
]


def severities(review: dict) -> Counter:
    return Counter(c.get("severity") for c in review.get("contradictions") or [])


def run(ctx):
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    schema = ctx.skill_json("schema.json")
    for doc in REPAIRABLE:  # start from the originals
        ctx.write_text(f"repaired_{doc}", ctx.read_text(doc))

    def repair_round(todo: dict[str, list[dict]], rnd: int) -> list[dict]:
        def repair(doc: str) -> dict:
            diags = todo.get(doc) or []
            text = ctx.read_text(f"repaired_{doc}")
            user = f"# Diagnostics\n{describe(diags)}\n\n# Document '{doc}'\n{text}"
            try:
                response, _ = structured(ctx, system_prompt, user, schema, label=f"round {rnd}: {doc}")
            except Exception as e:  # a failed repair keeps the document as it is
                ctx.log(f"round {rnd}: repair of {doc} failed: {e}")
                return {"document": doc, "diagnostics": len(diags), "error": str(e)[:300], "edits": []}
            new_text, log = apply_edits(text, response.get("edits") or [])
            if ctx.project_start is not None:
                new_text, _ = fix_text(new_text, ctx.project_start)
            ctx.write_text(f"repaired_{doc}", new_text)
            return {"document": doc, "diagnostics": len(diags), "edits": log}
        return ctx.map(repair, [d for d in REPAIRABLE if todo.get(d)])

    first = ctx.read_json("consistency_review_raw.json")
    current, rounds = first, []
    best = None  # (high count, round, snapshot of repaired docs, review)
    for rnd in range(1, MAX_ROUNDS + 1):
        todo = diagnostics_by_document(current)
        if not todo:
            break
        docs = repair_round(todo, rnd)
        applied = sum(1 for d in docs for e in d.get("edits") or [] if e.get("applied"))
        missed = sum(1 for d in docs for e in d.get("edits") or [] if not e.get("applied"))
        current = review(ctx, RECHECK_DOCUMENTS, "consistency_recheck_raw.json", "consistency_recheck.md", tier="high",
                         previous=current)
        sev = severities(current)
        rounds.append({"round": rnd, "documents": docs, "edits_applied": applied, "edits_missed": missed,
                       "after": dict(sev)})
        ctx.log(f"round {rnd}: {applied} edits applied, {missed} missed; now {dict(sev)}")
        score = (sev.get("high", 0), sev.get("medium", 0))
        improved = best is None or score[0] < best[0][0]
        if best is None or score < best[0]:
            best = (score, rnd, {d: ctx.read_text(f"repaired_{d}") for d in REPAIRABLE}, current)
        if not sev.get("high") or not improved:
            break  # done, or this round did not reduce the high-severity count
    if best is not None and best[1] != rounds[-1]["round"]:
        # Publish the best round, not the last one (a later round can find or create new issues).
        for d, text in best[2].items():
            ctx.write_text(f"repaired_{d}", text)
        current = best[3]
        ctx.write_json("consistency_recheck_raw.json", current)
        ctx.write_text("consistency_recheck.md", to_markdown(current))
    if not rounds:  # nothing repairable: the first pass is the final result
        ctx.write_json("consistency_recheck_raw.json", first)
        ctx.write_text("consistency_recheck.md", to_markdown(first))

    s1, sn = severities(first), severities(current)
    steps = "; ".join(f"round {r['round']}: {r['edits_applied']} edits -> {r['after'].get('high', 0)} high / "
                      f"{r['after'].get('medium', 0)} medium" for r in rounds)
    preface = (f"_Consistency: first pass found {s1.get('high', 0)} high / {s1.get('medium', 0)} medium / "
               f"{s1.get('low', 0)} low contradictions. Repair{(': ' + steps) if steps else ' was not needed'}. "
               + (f" Published: round {best[1]} (fewest high-severity issues)." if best else "")
               + f" Shown below: the final check of the repaired documents "
               f"({sn.get('high', 0)} high / {sn.get('medium', 0)} medium / {sn.get('low', 0)} low)._")
    ctx.write_text("consistency_recheck.md", preface + "\n\n" + ctx.read_text("consistency_recheck.md"))
    ctx.write_text("consistency_repair_raw.json", json.dumps({"rounds": rounds}, indent=2, ensure_ascii=False))
