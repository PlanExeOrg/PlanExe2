from planexe_skill.shared.documents import run_filter


def run(ctx):
    run_filter(ctx, "identified_documents_to_create.json", "filter_documents_to_create_raw.json", "filter_documents_to_create_clean.json")
