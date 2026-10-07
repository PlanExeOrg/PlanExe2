from planexe_skill.shared.arithmetic import check_text

DOCUMENTS = [
    ("Decisions Required", "decision_register.md"),
    ("Canonical Facts", "canonical_facts.md"),
    ("Executive Summary", "repaired_executive_summary.md"),
    ("Pitch", "repaired_pitch.md"),
    ("Project Plan", "repaired_project_plan.md"),
    ("Strategic Decisions", "strategic_decisions.md"),
    ("Scenarios", "scenarios.md"),
    ("Assumptions", "consolidate_assumptions_full.md"),
    ("Governance", "consolidate_governance.md"),
    ("Related Resources", "related_resources.md"),
    ("Data Collection", "data_collection.md"),
    ("Documents to Create and Find", "documents_to_create_and_find.md"),
    ("SWOT Analysis", "swot_analysis.md"),
    ("Team", "team.md"),
    ("Expert Criticism", "expert_criticism.md"),
    ("Review Plan", "repaired_review_plan.md"),
    ("Questions & Answers", "repaired_questions_and_answers.md"),
    ("Premortem", "repaired_premortem.md"),
    ("Self Audit", "repaired_self_audit.md"),
    ("Premise Attack", "premise_attack.md"),
]


def cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def run(ctx):
    by_section, mismatches, checked = {}, [], 0
    for title, name in DOCUMENTS:
        found = check_text(name, ctx.read_text(name))
        bad = [f for f in found if not f.ok]
        by_section[title] = {"file": name, "checked": len(found), "mismatches": len(bad)}
        checked += len(found)
        mismatches += [{"section": title, "file": name, "line": f.line, "expression": f.expression,
                        "stated": f.stated, "computed": f.computed, "excerpt": f.excerpt} for f in bad]
    ctx.write_json("arithmetic_check.json", {"checked": checked, "mismatches": mismatches, "by_section": by_section})
    rows = [f"{checked} explicit calculations found in the documents were re-computed without an LLM; "
            f"{len(mismatches)} do not match their stated result.", ""]
    if mismatches:
        rows += ["| Section | Statement | Stated | Computed |", "|---|---|---|---|"]
        rows += [f"| {cell(m['section'])} | {cell(m['excerpt'])} | {cell(m['stated'])} | {cell(m['computed'])} |"
                 for m in mismatches]
    ctx.write_text("arithmetic_check.md", "\n".join(rows) + "\n")
