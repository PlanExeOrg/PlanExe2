from planexe_skill.shared.consistency import DOCUMENTS, review


def run(ctx):
    review(ctx, DOCUMENTS, "consistency_review_raw.json", "consistency_review.md")
