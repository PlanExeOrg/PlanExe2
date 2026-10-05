from collections import Counter

from planexe_skill.shared.consistency import review

DOCUMENTS = [
    ("Executive Summary", "repaired_executive_summary.md"),
    ("Project Plan", "repaired_project_plan.md"),
    ("Assumptions", "consolidate_assumptions_short.md"),
    ("Review Plan", "repaired_review_plan.md"),
    ("Premortem", "repaired_premortem.md"),
    ("Self Audit", "repaired_self_audit.md"),
    ("Pitch", "repaired_pitch.md"),
]


def run(ctx):
    first = Counter(c.get("severity") for c in ctx.read_json("consistency_review_raw.json").get("contradictions") or [])
    repair = ctx.read_json("consistency_repair_raw.json").get("documents") or []
    applied = sum(1 for d in repair for e in d.get("edits") or [] if e.get("applied"))
    missed = sum(1 for d in repair for e in d.get("edits") or [] if not e.get("applied"))
    docs = [d["document"] for d in repair if any(e.get("applied") for e in d.get("edits") or [])]
    preface = (f"_Consistency pass 1 found {first.get('high', 0)} high / {first.get('medium', 0)} medium / "
               f"{first.get('low', 0)} low contradictions; {applied} edits were applied to "
               f"{', '.join(docs) or 'no documents'}"
               + (f" ({missed} proposed edits did not match the text)" if missed else "")
               + ". The check below is pass 2, on the repaired documents._")
    review(ctx, DOCUMENTS, "consistency_recheck_raw.json", "consistency_recheck.md", preface=preface)
