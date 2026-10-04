from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "potential_levers.json", "potential_levers", "potential_levers_constraint.json")
