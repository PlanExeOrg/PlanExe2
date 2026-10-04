---
name: create_schedule
description: Turn the WBS + task durations into a waterfall schedule; export the interactive DHTMLX Gantt HTML and a CSV.
inputs: [start_time.json, wbs_level1_project_title.json, task_dependencies_raw.json, task_durations.json, wbs_project_level1_and_level2_and_level3.json]
outputs: [schedule_gantt_dhtmlx.html, schedule_gantt_machai.csv]
tier: low
est_llm_calls: 0
uses: [planexe_skill/shared/schedule]
---
Deterministic, vendored from PlanExe (`planexe_skill/shared/schedule/`):
leaf durations come from task_durations.json (days_realistic); parent durations are resolved
bottom-up by the hierarchy estimator; activities are scheduled as an unoptimized waterfall from the
project start date (start_time.json, UTC date). The CSV export is computed but, as in PlanExe
(`enable_csv_export = False`), not embedded in the HTML.
