from planexe_skill.shared.constraint_checker import run_stage


def run(ctx):
    run_stage(ctx, "selected_scenario.json", "selected_scenario", "selected_scenario_constraint.json")
