"""Shared code for the final review stages (review_plan, executive_summary, questions_and_answers,
premortem, self_audit).

Mirrors the query the PlanExe node wrappers in worker_plan_internal/plan/nodes/{review_plan,
executive_summary,questions_and_answers,premortem,self_audit}.py assemble: the same 11 documents,
optionally followed by the outputs of the earlier review stages.
"""
from __future__ import annotations

# (label used in the prompt, input file). Note: PlanExe reads the *short* assumptions and the WBS *csv*.
BASE_DOCUMENTS = [
    ("strategic_decisions.md", "strategic_decisions.md"),
    ("scenarios.md", "scenarios.md"),
    ("assumptions.md", "consolidate_assumptions_short.md"),
    ("project-plan.md", "project_plan.md"),
    ("data-collection.md", "data_collection.md"),
    ("related-resources.md", "related_resources.md"),
    ("swot-analysis.md", "swot_analysis.md"),
    ("team.md", "team.md"),
    ("pitch.md", "pitch.md"),
    ("expert-review.md", "expert_criticism.md"),
    ("work-breakdown-structure.csv", "wbs_project_level1_and_level2_and_level3.csv"),
]

REVIEW_PLAN = ("review-plan.md", "review_plan.md")
QUESTIONS_AND_ANSWERS = ("questions-and-answers.md", "questions_and_answers.md")
PREMORTEM = ("premortem.md", "premortem.md")


def build_query(ctx, extra: list[tuple[str, str]] | tuple = ()) -> str:
    """`File '<label>':\\n<content>` sections joined by blank lines (PlanExe's query layout)."""
    return "\n\n".join(f"File '{label}':\n{ctx.read_text(name)}" for label, name in [*BASE_DOCUMENTS, *extra])


def transcript(history: list[tuple[str, str]], current: str, initial: str = "") -> str:
    """Render a multi-turn PlanExe chat as one user message (ctx.llm is single-turn).

    `initial` is the first user message (omitted when empty), `history` the (role, content) turns
    that followed it, `current` the new user message the model must answer now."""
    if not history:
        return f"{initial}\n\n{current}" if initial else current
    parts = [initial, "## Conversation so far"] if initial else ["## Conversation so far"]
    for role, content in history:
        parts.append(f"### {role}\n{content}")
    parts.append(f"## Current request (answer this one)\n\n### User\n{current}")
    return "\n\n".join(parts)


def fix_bullet_lists(markdown_text: str) -> str:
    """PlanExe's markdown_util.fix_bullet_lists: blank line before and after every '- ' list."""
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
