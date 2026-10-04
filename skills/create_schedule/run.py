from datetime import datetime

from planexe_skill.shared.schedule.export_gantt_csv import ExportGanttCSV
from planexe_skill.shared.schedule.export_gantt_dhtmlx import ExportGanttDHTMLX
from planexe_skill.shared.schedule.project_schedule_populator import ProjectSchedulePopulator
from planexe_skill.shared.schedule.wbs_task import WBSProject
from planexe_skill.shared.schedule.wbs_task_tooltip import WBSTaskTooltip

ENABLE_CSV_EXPORT = False  # PlanExe's PIPELINE_CONFIG.enable_csv_export


def run(ctx):
    title = ctx.read_text("wbs_level1_project_title.json")
    ctx.read_json("task_dependencies_raw.json")  # read for parity with PlanExe (dependency edges are not used yet)
    duration_list = ctx.read_json("task_durations.json")
    wbs_project = WBSProject.from_dict(ctx.read_json("wbs_project_level1_and_level2_and_level3.json"))
    st = ctx.read_json("start_time.json")
    utc = st.get("server_iso_utc") or st.get("utc_timestamp", "")
    project_start = datetime.fromisoformat(utc.replace("Z", "+00:00")).date()

    html_tooltips = WBSTaskTooltip.html_tooltips(wbs_project)
    text_tooltips = WBSTaskTooltip.text_tooltips(wbs_project)
    schedule = ProjectSchedulePopulator.populate(wbs_project=wbs_project, duration_list=duration_list)
    csv_data = ExportGanttCSV.to_gantt_csv(schedule, project_start, text_tooltips)
    ctx.write_text("schedule_gantt_machai.csv", csv_data)
    html = ExportGanttDHTMLX.to_html(
        project_schedule=schedule, project_start=project_start,
        task_ids_to_treat_as_project_activities=wbs_project.task_ids_with_one_or_more_children(),
        task_id_to_tooltip_dict=html_tooltips, title=title,
        csv_data=csv_data if ENABLE_CSV_EXPORT else None)
    ctx.write_text("schedule_gantt_dhtmlx.html", html)
