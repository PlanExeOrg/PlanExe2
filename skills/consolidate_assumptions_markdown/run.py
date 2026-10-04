import re

DOCUMENTS = [
    ("Purpose", "identify_purpose.md"),
    ("Domain", "classify_domain.md"),
    ("Plan Type", "plan_type.md"),
    ("Physical Locations", "physical_locations.md"),
    ("Currency Strategy", "currency_strategy.md"),
    ("Identify Risks", "identify_risks.md"),
    ("Make Assumptions", "make_assumptions.md"),
    ("Distill Assumptions", "distill_assumptions.md"),
    ("Review Assumptions", "review_assumptions.md"),
]
START_DELIMITER = "[START_MARKDOWN]"
END_DELIMITER = "[END_MARKDOWN]"


def remove_bold_formatting(text: str) -> str:
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    return re.sub(r'__([^_]+?)__', r'\1', text)


def fix_bullet_lists(markdown_text: str) -> str:
    """Ensure a blank line before and after every '- ' bullet list."""
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


def extract_markdown(response_content: str) -> str:
    start_index = response_content.find(START_DELIMITER)
    end_index = response_content.find(END_DELIMITER)
    if start_index != -1 and end_index != -1:
        markdown_content = response_content[start_index + len(START_DELIMITER):end_index].strip()
    else:
        markdown_content = response_content  # use the entire content if the delimiters are missing
    markdown_content = fix_bullet_lists(markdown_content)
    return remove_bold_formatting(markdown_content)


def run(ctx):
    system_prompt = ctx.skill_file("prompts/shorten_markdown.md").strip()

    docs = []  # (title, content or None, problem text or None)
    for title, name in DOCUMENTS:
        try:
            docs.append((title, ctx.read_text(name), None))
        except FileNotFoundError:
            ctx.log(f"Markdown file not found: {name} (from {title})")
            docs.append((title, None, f"**Problem with document:** '{title}'\n\nFile not found."))

    def shorten(doc):
        title, content, problem = doc
        if problem is not None:
            return problem
        user_prompt = remove_bold_formatting(content.strip())
        try:
            result = ctx.llm(system=system_prompt, user=user_prompt, schema=None, label=title)
        except Exception as e:  # PlanExe logs the error and continues with the other documents
            ctx.log(f"Error shortening markdown ({title}): {e}")
            return f"**Problem with document:** '{title}'\n\nError shortening markdown file."
        return f"# {title}\n{extract_markdown(result.text)}"

    full_chunks = [problem if problem is not None else f"# {title}\n\n{content}" for title, content, problem in docs]
    short_chunks = ctx.map(shorten, docs, max_workers=len(docs))

    ctx.write_text("consolidate_assumptions_full.md", "\n\n".join(full_chunks))
    ctx.write_text("consolidate_assumptions_short.md", "\n\n".join(short_chunks))
