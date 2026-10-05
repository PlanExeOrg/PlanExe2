from planexe_skill.planexe import raw_document, structured

DOCUMENTS = [
    ("Executive Summary", "executive_summary.md"),
    ("Project Plan", "project_plan.md"),
    ("Assumptions", "consolidate_assumptions_short.md"),
    ("Review Plan", "review_plan.md"),
    ("Premortem", "premortem.md"),
    ("Self Audit", "self_audit.md"),
    ("Pitch", "pitch.md"),
]
SEVERITY_ICON = {"high": "🔴 High", "medium": "🟡 Medium", "low": "⚪ Low"}


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(r: dict) -> str:
    rows = ["## Decision Kernel", "",
            "Any NO means delay, split, downsize or stop, as described.", "",
            "| # | Question | Threshold | Evidence | If NO |", "|---|---|---|---|---|"]
    for i, q in enumerate(r.get("decision_questions") or [], start=1):
        rows.append(f"| {i} | {cell(q['question'])} | {cell(q['threshold'])} | {cell(q['evidence'])} | {cell(q['if_no'])} |")
    rows += ["", "## Consistency Check", ""]
    items = r.get("contradictions") or []
    if not items:
        rows.append("No contradictions found between the core documents.")
    diag = [c for c in items if c.get("canonical_key")]
    if diag:
        rows += ["Diagnostics (document vs canonical fact):", "", "```text"]
        for i, c in enumerate(diag, start=1):
            rows += [f"{c['severity'].upper()} CF-{i:03d}  document: {c.get('offending_document', '')}",
                     f"    canonical: {c['canonical_key']} = {c.get('canonical_value', '')}",
                     f"    observed:  {c.get('observed_value', '')}"]
        rows += ["```", ""]
    for i, c in enumerate(items, start=1):
        rows += [f"### {i}. {c['topic']} ({SEVERITY_ICON.get(c['severity'], c['severity'])})", "",
                 f"- **{c['where_a']}:** {c['statement_a']}",
                 f"- **{c['where_b']}:** {c['statement_b']}",
                 f"- **Why it conflicts:** {c['why_inconsistent']}",
                 f"- **Suggested resolution:** {c['suggested_resolution']}", ""]
    rows += ["## Summary", "", r.get("summary", "")]
    return "\n".join(rows)


def run(ctx):
    sections = [f"File 'plan.txt':\n{ctx.read_text('plan.txt')}"]
    for title, name in DOCUMENTS:
        sections.append(f"File '{name}' ({title}):\n{ctx.read_text(name)}")
    user_prompt = "\n\n".join(sections)
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    response, result = structured(ctx, system_prompt, user_prompt, ctx.skill_json("schema.json"))
    ctx.write_json("consistency_review_raw.json", raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text("consistency_review.md", to_markdown(response))
