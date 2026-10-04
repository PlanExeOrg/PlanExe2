import json

from planexe_skill.planexe import format_json_for_query, planexe_metadata


def fix_bullet_lists(markdown_text: str) -> str:
    """Make sure bullet lists are preceded (and followed) by a blank line (PlanExe fix_bullet_lists)."""
    lines = markdown_text.split('\n')
    fixed_lines = []
    in_list = False
    for i, line in enumerate(lines):
        if line.startswith('- '):
            if not in_list:
                if i > 0 and lines[i - 1].strip() != '':
                    fixed_lines.append('')
                in_list = True
            fixed_lines.append(line)
        else:
            if in_list:
                if line.strip() != '':
                    fixed_lines.append('')
                in_list = False
            fixed_lines.append(line)
    if in_list:
        fixed_lines.append('')
    return '\n'.join(fixed_lines)


def run(ctx):
    user_prompt = format_json_for_query(ctx.read_json("pitch_raw.json"))
    system_prompt = ctx.skill_file("prompts/system.md").strip()
    result = ctx.llm(system=system_prompt, user=user_prompt)
    response_content = result.text or ""

    start_delimiter = "[START_MARKDOWN]"
    end_delimiter = "[END_MARKDOWN]"
    start_index = response_content.find(start_delimiter)
    end_index = response_content.find(end_delimiter)
    if start_index != -1 and end_index != -1:
        markdown_content = response_content[start_index + len(start_delimiter):end_index].strip()
    else:
        markdown_content = response_content  # Use the entire content if delimiters are missing
        ctx.log("Output delimiters not found in LLM response.")

    markdown_content = fix_bullet_lists(markdown_content)
    markdown_content = "Persuasive elevator pitch.\n\n" + markdown_content

    raw = {
        "response_content": response_content,
        "markdown": markdown_content,
        "metadata": planexe_metadata(result),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }
    ctx.write_text("pitch_to_markdown_raw.json", json.dumps(raw, indent=2))
    ctx.write_text("pitch.md", markdown_content)
