from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "enriched_levers_raw.json", "enriched_levers", "enriched_levers_constraint.json")
