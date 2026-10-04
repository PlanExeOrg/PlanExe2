from planexe_skill.planexe import raw_document, structured


def compute_prompt_stats(prompt: str) -> str:
    lines = [
        f"Byte count: {len(prompt.encode('utf-8'))}",
        f"Character count: {len(prompt)}",
        f"Word count: {len(prompt.split())}",
        f"Line count: {prompt.count(chr(10)) + 1 if prompt else 0}",
        f"Symbol count: {sum(1 for c in prompt if not c.isalnum() and not c.isspace())}",
    ]
    return "\n".join(lines)


def to_markdown(r: dict) -> str:
    verdict_display = "🟢 USABLE" if r["verdict"] == "USABLE" else "🔴 UNUSABLE"
    parts = [f"**Verdict:** {verdict_display}\n", f"**Rationale:** {r['rationale']}"]
    if r["verdict"] == "UNUSABLE":
        parts.append("\n### Details\n")
        parts.append("| Detail                | Value |")
        parts.append("|-----------------------|-------|")
        parts.append(f"| **Reason**            | {r['reason'].replace('_', ' ').title()} |")
        parts.append(f"| **Confidence**        | {r['confidence'].title()} |")
    return "\n".join(parts)


def run(ctx):
    plan_prompt = ctx.read_json("plan_raw.json")["plan_prompt"]
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    composed = f"## Prompt Statistics\n{compute_prompt_stats(plan_prompt)}\n\n## User Prompt\n{plan_prompt}"
    response, result = structured(ctx, system_prompt, composed, ctx.skill_json("schema.json"))
    ctx.write_json("screen_planning_prompt.json", raw_document(response, result, system_prompt, plan_prompt))
    ctx.write_text("screen_planning_prompt.md", to_markdown(response))
