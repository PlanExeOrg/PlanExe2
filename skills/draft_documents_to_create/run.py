from planexe_skill.shared.documents import run_draft


def run(ctx):
    run_draft(ctx, "filter_documents_to_create_clean.json", "draft_documents_to_create_{}_raw.json", "draft_documents_to_create.json", "create")
