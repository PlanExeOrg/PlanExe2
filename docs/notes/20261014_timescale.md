# Time scale: plans that are not measured in months

2026-10-14

## Problem

PlanExe2 assumes that every plan is measured in months, with work in whole days. That fits most prompts
(a 12-month pilot, a 25-year programme), but not a plan whose natural unit is hours. The Yellowstone
evacuation prompt asks for phases at T+0 to T+6 h and T+6 to T+24 h, a 72-hour decision window, and "a
Phased Gantt Chart (hourly for the first 24h)". The run (`runs/20261014_yellowstone_evacuation`, v2.0.6)
wrote a good hour-by-hour response in prose, but the time machinery around it could not follow:

- 17 of the 53 estimated tasks got a realistic duration of 0 days (14) or -1 days (3).
- The scheduler raised them to 1 day each, so every few-hour task became a full day.
- The Gantt chart runs from 2026-10-14 to 2028-09-19, about two years, for a 72-hour operation.
- The text mixes units, e.g. "Month 0 (2026-10-14), Hour 6 (T+6h)", and the plan grew follow-up work in
  Months 1-3 (exercises, MOUs, "a Readiness Fund with annual Congressional appropriation by Month 2"),
  part of which comes from the month framing rather than from the prompt.
- No hourly Gantt chart can be produced, although the prompt asks for one.

## Where the assumption lives

1. **The time convention in every LLM call.** `calendar_reference()` in `planexe_skill/context.py` appends to
   every system prompt: refer to points in time as month offsets ("Month 3", "Month 3.5", "Months 48-72"),
   followed by a table of Month 0-12, then every 3 months up to Month 120.
2. **The date fixer.** `planexe_skill/calendar_fix.py` recognises "Month N", "Months A-B" and month lists,
   and appends calendar dates (no time of day). "Hour 6", "T+6h", "Day 3" or "Week 2" are left alone.
3. **Duration estimates.** `skills/estimate_task_durations/schema.json` asks for `days_min`, `days_max`
   and `days_realistic` as integers, with "If not applicable use minus 1". A 2-hour task can only be
   0 or -1.
4. **The scheduler.** `planexe_skill/shared/schedule/project_schedule_populator.py` reads
   `days_realistic` with `hours_per_day = 1` (its own comment already asks whether the unit should be
   hours, days or weeks) and sets negative durations to 1. `hierarchy_estimator.py`
   (`apply_minimum_duration`) raises 0-duration leaves to 1. Durations are `Decimal`, so fractions
   would survive the scheduling itself.
5. **The exports.** `export_gantt_csv.py` and `export_gantt_dhtmlx.py` add `timedelta(days=...)` to a
   `date`, which drops any fraction of a day. The DHTMLX template picks its scale from the project span,
   and its finest zoom level is one day.

## Proposed solution

Detect the plan's time unit once, early, and let each of the five places use it. Plans measured in months
must come out exactly as today.

### A. Durations, schedule and Gantt chart (self-contained, do first)

- `estimate_task_durations`: estimate in the plan's unit with fractional values allowed (`number`, not
  `integer`), e.g. `hours_*` for an hour-scale plan or fractional days. Drop the "-1 if not applicable"
  sentinel; reject or repair non-positive values in code instead.
- Scheduler: replace `hours_per_day = 1` with the plan's unit, and make the minimum duration one unit of
  that scale (one hour for an hour-scale plan) instead of always one day.
- Exports: compute starts and ends as `datetime`, not `date`, so fractions of a day survive; write
  times into the CSV and the DHTMLX data.
- DHTMLX template: add an hour scale (e.g. `day` with an `hour` subscale) to the zoom-fit choice and to
  the zoom in/out steps.

### B. Time convention and date fixer (touches every stage)

- New small artifact `time_scale.json` from an early stage (a field on an existing early stage, or a tiny
  stage of its own): `unit` (hour, day, week, month) and `horizon` (e.g. 72 hours), derived from the
  prompt. Signals: "T+6 hours", "within 72 hours" -> hour; "12-month program", "2026-2041" -> month.
  Default month.
- `calendar_reference()`: for an hour-scale plan, ask for "Hour N" / "T+N h" and show an hour table
  (Hour 0-72 with date and time); keep today's month text unchanged for month-scale plans.
- `calendar_fix.py`: also recognise Hour, Day and Week offsets (and "T+N h") and append date and time,
  e.g. "Hour 6 (2026-10-14 06:00)". Same rules as today: recompute dates the model wrote, never trust them.

### C. Work beyond the horizon (optional, decide after A and B)

For a short-horizon plan, keep follow-up work (after-action review, hardening, exercises) as a separate
phase, so the main timeline and Gantt chart cover the horizon the prompt asked for. Possibly an hourly
chart for the response and a daily or monthly chart for the follow-up.

## Testing without full reruns

- Yellowstone copy: run `estimate_task_durations` and `create_schedule` alone (a few minutes). Expect no
  zero or negative durations, hourly bars, and a chart spanning about 72 hours plus any follow-up phase.
- Month-scale regression: the same two stages on a rubber or heatwave copy; durations and the chart
  should be unchanged.
- Unit tests: Hour/Day/Week cases in `tests/test_calendar_fix.py`, duration validation, and the
  datetime exports.
- After B: one single-stage check of an early stage on both plans to confirm the time convention, then
  one full Yellowstone run, since B reaches every stage's prompt.

## Risks and open questions

- B changes the system prompt of every stage. It must be a no-op for month-scale plans; the rubber
  regression is the guard.
- Mixed scales: a plan can be hour-scale for its response and month-scale for its follow-up. C is where
  that is handled; A and B should pick one unit for the main timeline.
- Hour-scale prompts are rare in the test set (only Yellowstone so far). A also helps month-scale plans,
  where short setup tasks are rounded to 0 days and then raised to a full day today.
- The working-hours question in the scheduler's comment (8 or 24 hours per day) matters for day-scale
  plans; an emergency response runs around the clock, a construction project does not.
