PLAN_TEMPLATE = "Plan:\n{plan_prompt}\n\nToday's date:\n{pretty_date}\n\nProject start ASAP"


def run(ctx):
    raw = ctx.read_json("plan_raw.json")
    ctx.write_text("plan.txt", PLAN_TEMPLATE.format(plan_prompt=raw["plan_prompt"], pretty_date=raw["pretty_date"]))
