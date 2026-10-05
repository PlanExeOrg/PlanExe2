"""Shared by consistency_review (lint 1), consistency_repair and consistency_recheck (lint 2)."""
import json
from pathlib import Path

from planexe_skill.planexe import raw_document, structured

HERE = Path(__file__).parent

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
        needs_decision = "canonical" in str(c.get("offending_document", "")).lower()
        tag = " — needs a decision (the canonical facts themselves conflict)" if needs_decision else ""
        rows += [f"### {i}. {c['topic']} ({SEVERITY_ICON.get(c['severity'], c['severity'])}){tag}", "",
                 f"- **{c['where_a']}:** {c['statement_a']}",
                 f"- **{c['where_b']}:** {c['statement_b']}",
                 f"- **Why it conflicts:** {c['why_inconsistent']}",
                 f"- **Suggested resolution:** {c['suggested_resolution']}", ""]
    rows += ["## Summary", "", r.get("summary", "")]
    return "\n".join(rows)




def review(ctx, documents: list[tuple[str, str]], raw_name: str, md_name: str, preface: str = "",
           tier: str | None = None, previous: dict | None = None) -> dict:
    """One reasoning call: decision kernel + contradictions over `documents` (title, filename)."""
    sections = [f"File 'plan.txt':\n{ctx.read_text('plan.txt')}"]
    for title, name in documents:
        sections.append(f"File '{name}' ({title}):\n{ctx.read_text(name)}")
    user_prompt = "\n\n".join(sections)
    if previous is not None:
        # Verification mode (repair rounds 2+): re-check the known items first, so successive passes
        # converge instead of rediscovering different issues each time.
        prev = "\n".join(f"- [{c.get('severity')}] {c.get('topic')}: {c.get('why_inconsistent', '')}"
                         for c in previous.get("contradictions") or [])
        user_prompt += ("\n\n# Previously reported contradictions\nThe documents were edited to fix these. Re-check "
                        "each one and report it again only if it still holds. Report a new contradiction only if it is "
                        "clear, material and was missed before; do not escalate cosmetic differences.\n" + (prev or "(none)"))
    system_prompt = (HERE / "review_system.md").read_text(encoding="utf-8").strip()
    schema = json.loads((HERE / "review_schema.json").read_text(encoding="utf-8"))
    response, result = structured(ctx, system_prompt, user_prompt, schema, tier=tier)
    ctx.write_json(raw_name, raw_document(response, result, system_prompt, user_prompt))
    ctx.write_text(md_name, (preface + "\n\n" if preface else "") + to_markdown(response))
    return response
