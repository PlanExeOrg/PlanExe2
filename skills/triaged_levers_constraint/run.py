from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "triaged_levers_raw.json", "triaged_levers", "triaged_levers_constraint.json")
