from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "candidate_scenarios.json", "candidate_scenarios", "candidate_scenarios_constraint.json")
