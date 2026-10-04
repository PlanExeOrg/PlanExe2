import json

from planexe_skill.shared.schedule.create_wsb_table_csv import CreateWBSTableCSV
from planexe_skill.shared.schedule.wbs_populate import WBSPopulate
from planexe_skill.shared.schedule.wbs_task import WBSProject


def run(ctx):
    project = WBSProject.from_dict(ctx.read_json("wbs_project_level1_and_level2.json"))
    WBSPopulate.extend_project_with_decomposed_tasks_json(project, str(ctx.path("wbs_level3.json")))
    ctx.write_text("wbs_project_level1_and_level2_and_level3.json", json.dumps(project.to_dict(), indent=2))
    table = CreateWBSTableCSV(project)
    table.execute()
    ctx.write_text("wbs_project_level1_and_level2_and_level3.csv", table.to_csv_string())
