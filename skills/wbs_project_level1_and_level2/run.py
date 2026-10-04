import json

from planexe_skill.shared.schedule.wbs_populate import WBSPopulate


def run(ctx):
    project = WBSPopulate.project_from_level1_json(str(ctx.path("wbs_level1.json")))
    WBSPopulate.extend_project_with_level2_json(project, str(ctx.path("wbs_level2.json")))
    ctx.write_text("wbs_project_level1_and_level2.json", json.dumps(project.to_dict(), indent=2))
