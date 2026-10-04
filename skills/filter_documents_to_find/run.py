from planexe_skill.shared.documents import run_filter


def run(ctx):
    run_filter(ctx, "identified_documents_to_find.json", "filter_documents_to_find_raw.json", "filter_documents_to_find_clean.json")
