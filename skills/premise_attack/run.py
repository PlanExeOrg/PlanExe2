import time

from planexe_skill.planexe import planexe_metadata, structured

LENSES = [
    ("lens_5.md", "Integrity", "Forensic audit of foundational soundness across axes."),
    ("lens_8.md", "Accountability", "Rights, oversight, jurisdiction-shopping, enforceability."),
    ("lens_6.md", "Spectrum", "Enforced breadth: distinct reasons across ethical/feasibility/governance/societal axes."),
    ("lens_3.md", "Cascade", "Tracks second/third-order effects and copycat propagation."),
    ("lens_9.md", "Escalation", "Narrative of worsening failure from cracks → amplification → reckoning."),
]


def to_markdown(results: list) -> str:
    out: list[str] = []
    for i, (d, name, desc) in enumerate(results):
        if i > 0:
            out.append("\n\n")
        out.append(f"### Premise Attack {i + 1} — {name}")
        out.append(f"_{desc}_\n")
        out.append(f"**{d['core_thesis']}**\n")
        out.append(f"**Bottom Line:** {d['bottom_line']}\n")
        for key, title in (("reasons", "Reasons for Rejection"), ("second_order_effects", "Second-Order Effects"),
                           ("evidence", "Evidence")):
            if d.get(key):
                out.append(f"\n#### {title}\n")
                out.extend(f"- {x}" for x in d[key])
    return "\n".join(out)


def run(ctx):
    plan = ctx.read_text("plan.txt").strip()
    schema = ctx.skill_json("schema.json")
    start = time.time()

    def attack(item):
        index, (fname, name, desc) = item
        system_prompt = ctx.skill_file(f"prompts/{fname}")
        try:
            response, result = structured(ctx, system_prompt.strip(), plan, schema, label=name)
        except Exception as e:  # PlanExe skips a failing lens
            ctx.log(f"lens {name} failed: {e}")
            return None
        meta = planexe_metadata(result)
        meta["system_prompt_index"] = index
        meta["system_prompt_name"] = name
        return response, meta, system_prompt, name, desc

    results = [r for r in ctx.map(attack, list(enumerate(LENSES))) if r is not None]
    if not results:
        raise RuntimeError("all premise-attack lenses failed")
    raw = {
        "response_list": [r[0] for r in results],
        "metadata": {"models": [r[1] for r in results], "duration": int(time.time() - start + 0.999)},
        "system_prompt_list": [r[2] for r in results],
        "user_prompt": plan,
    }
    ctx.write_json("premise_attack_raw.json", raw)
    ctx.write_text("premise_attack.md", to_markdown([(r[0], r[3], r[4]) for r in results]))
