from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "vital_few_levers_raw.json", "vital_few_levers", "vital_few_levers_constraint.json")
