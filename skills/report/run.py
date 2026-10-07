import csv
import io
import json
import re
from datetime import datetime
from html import escape

from planexe_skill.planexe import plural
from planexe_skill.shared.markdown_html import render as md_to_html

EXECUTE_PLAN_SECTION_HIDDEN = True
PART = "\x00part"  # marker title for part headings in html_items / md_items


# PlanExe's one-line section subtitles, written as plain first lines into the documents; the report shows
# them in italics, like the Team section's "*Roles Needed & Example People*".
PLANEXE_SUBTITLES = (
    "Persuasive elevator pitch.",
    "A premortem assumes the project has failed and works backward to identify the most likely causes.",
    "Reality check: fix before go.",
)


def italic_subtitle(md: str) -> str:
    stripped = md.lstrip()
    for sub in PLANEXE_SUBTITLES:
        if stripped.startswith(sub + "\n") or stripped == sub:
            return f"*{sub}*" + stripped[len(sub):]
    return md


def heading_to_subtitle(md: str, heading: str, subtitle: str) -> str:
    """A leading '# <heading>' becomes the italic '*<subtitle>*' (scenarios.md keeps the heading)."""
    m = re.match(r"\s*#{1,6}\s+" + re.escape(heading) + r"\s*\n", md)
    return f"*{subtitle}*\n\n" + md[m.end():] if m else md


def strip_expert_headings(md: str) -> str:
    """Drop PlanExe's two opening headings of expert_criticism.md ("Project Expert Review & Recommendations",
    "A Compilation of Professional Feedback ..."): they repeat the section title (an italic subtitle replaces
    them)."""
    return re.sub(r"\A\s*# Project Expert Review & Recommendations\s*\n+"
                  r"(## A Compilation of Professional Feedback[^\n]*\n+)?", "", md)


def strip_repeated_title(title: str, md: str) -> str:
    """Drop a leading heading that repeats the section title ("Canonical Facts" > "## Canonical Facts")."""
    m = re.match(r"\s*#{1,6}\s+(.+?)\s*#*\s*(?:\n|$)", md)
    if m and m.group(1).strip().lower() == title.strip().lower():
        return md[m.end():].lstrip("\n")
    return md


# Emoji, pictographs and their joiners/modifiers ("🤷‍♂️", "☢︎", "⚠️").
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u200D\uFE0E\uFE0F]+")


def strip_heading_emoji(md: str) -> str:
    """'## Strengths 👍💪🦾' -> '## Strengths' (PlanExe's SWOT headings; swot_analysis.md keeps them)."""
    return re.sub(r"^(#{1,6} .*?)\s*$", lambda m: _EMOJI.sub("", m.group(1)).rstrip(), md, flags=re.M)


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


class Report:
    def __init__(self, ctx):
        self.ctx = ctx
        self.html_items: list[tuple[str, str]] = []
        self.md_items: list[tuple[str, str]] = []
        self.top_banner_html = ""
        self.top_banner_markdown = ""
        self.head: list[str] = []
        self.scripts: list[str] = []
        self.generator_line = "PlanExe2"
        self.repo_url = "https://github.com/PlanExeOrg/PlanExe2"
        self.metadata_line = ""

    def part(self, title: str) -> None:
        """A heading that groups the following sections (model / supporting analysis / audit trail)."""
        self.html_items.append((PART, f'<h2 class="report-part">{escape(title)}</h2>'))
        self.md_items.append((PART, f"# {title}"))

    def markdown(self, title: str, name: str, subtitle: str | None = None) -> None:
        self.markdown_text(title, self.ctx.read_text(name), subtitle)

    def markdown_text(self, title: str, md: str, subtitle: str | None = None) -> None:
        """`subtitle`: a one-line context sentence above the content, like PlanExe's "Why this fails."."""
        md = italic_subtitle(strip_repeated_title(title, md))
        if subtitle:
            md = f"*{subtitle}*\n\n{md}"
        self.html_items.append((title, md_to_html(md)))
        self.md_items.append((title, md))

    def csv_table(self, title: str, name: str) -> None:
        text = self.ctx.read_text(name)
        first = text.splitlines()[0] if text else ""
        delimiter = max([",", ";", "\t", "|"], key=lambda d: first.count(d))
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        header, body = rows[0], [r + [""] * (len(rows[0]) - len(r)) for r in rows[1:]]
        body = [r[:len(header)] for r in body if any(c.strip() for c in r)]
        keep = [i for i in range(len(header)) if any(r[i].strip() for r in body)] if body else list(range(len(header)))
        header = [header[i] for i in keep]
        body = [[r[i] for i in keep] for r in body]
        out = ['<table class="dataframe dataframe">', "  <thead>", '    <tr style="text-align: right;">']
        out += [f"      <th>{escape(h)}</th>" for h in header]
        out += ["    </tr>", "  </thead>", "  <tbody>"]
        for r in body:
            out.append("    <tr>")
            out += [f"      <td>{escape(c)}</td>" for c in r]
            out.append("    </tr>")
        out += ["  </tbody>", "</table>"]
        self.html_items.append((title, "\n".join(out)))
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(body)
        self.md_items.append((title, f"```csv\n{buf.getvalue()}```"))

    def embedded_html(self, title: str, name: str, subtitle: str | None = None) -> None:
        raw = self.ctx.read_text(name)
        sub = f"<p><em>{escape(subtitle)}</em></p>\n" if subtitle else ""
        m = re.search(r"<!--HTML_HEAD_START-->(.*)<!--HTML_HEAD_END-->", raw, re.DOTALL)
        if m:
            self.head.append(m.group(1))
        m = re.search(r"<!--HTML_BODY_CONTENT_START-->(.*)<!--HTML_BODY_CONTENT_END-->", raw, re.DOTALL)
        self.html_items.append((title, sub + (m.group(1) if m else raw)))
        m = re.search(r"<!--HTML_BODY_SCRIPT_START-->(.*)<!--HTML_BODY_SCRIPT_END-->", raw, re.DOTALL)
        if m:
            self.scripts.append(m.group(1))

    def initial_prompt_vetted(self, title: str) -> None:
        prompt = self.ctx.read_text("plan.txt")
        screening = self.ctx.read_json("screen_planning_prompt.json")
        if screening.get("verdict") == "UNUSABLE":
            reason_display = screening.get("reason", "unknown").replace("_", " ").title()
            rationale_raw = screening.get("rationale", "")
            self.top_banner_html = f"""
        <div class="prompt-quality-warning">
            <strong>&#9888; Prompt Quality Warning</strong>
            <p>
                The initial prompt was classified as <strong>UNUSABLE</strong> ({reason_display}).
                This plan is likely to contain hallucinated or nonsensical content. Garbage in, garbage out.
            </p>
            <p class="prompt-quality-warning-rationale">{escape(rationale_raw)}</p>
        </div>
"""
            self.top_banner_markdown = (
                f"> **⚠ Prompt Quality Warning**\n>\n"
                f"> The initial prompt was classified as **UNUSABLE** ({reason_display}). "
                f"This plan is likely to contain hallucinated or nonsensical content. Garbage in, garbage out.\n>\n"
                f"> {rationale_raw}")
        screening_md = self.ctx.read_text("screen_planning_prompt.md")
        redline_md = self.ctx.read_text("redline_gate.md")
        premise_md = self.ctx.read_text("premise_attack.md")
        html = f"""
        <h2>Initial Prompt</h2>
        <p>{escape(prompt).replace(chr(10), '<br>')}</p>
        <h2>Prompt Screening</h2>
        {md_to_html(screening_md)}
        <h2>Redline Gate</h2>
        {md_to_html(redline_md)}
        <h2>Premise Attack</h2>
        <p><em>Why this fails.</em></p>
        {md_to_html(premise_md)}
        """
        self.html_items.append((title, html))
        parts = ["## Initial Prompt", "", "```text", prompt, "```", "", "## Prompt Screening", "", screening_md, "",
                 "## Redline Gate", "", redline_md, "", "## Premise Attack", "", "*Why this fails.*", "", premise_md]
        self.md_items.append((title, "\n".join(parts)))

    def html_report(self, title: str, now: str) -> str:
        t = escape(title or "PlanExe Project Report")
        tpl = self.ctx.skill_file("template.html")
        tpl = tpl.replace("<!--HTML_HEAD_INSERT_HERE-->", "\n".join(self.head))
        tpl = tpl.replace("<!--HTML_BODY_SCRIPT_INSERT_HERE-->", "\n".join(self.scripts))
        tpl = tpl.replace("HEAD_TITLE_INSERT_HERE", t)
        tpl = tpl.replace("EXECUTE_PLAN_CSS_PLACEHOLDER",
                          "section-execute-plan-hidden" if EXECUTE_PLAN_SECTION_HIDDEN else "section-execute-plan-visible")
        parts = [f"""
        <h1>{t}</h1>
        <p class="planexe-report-info">Generated on: {now} with {escape(self.generator_line)}. <a href="https://planexe.org/discord.html">Discord</a>, <a href="{escape(self.repo_url)}">GitHub</a></p>
        {f'<p class="planexe-report-info">{escape(self.metadata_line)}</p>' if self.metadata_line else ''}
        """]
        if self.top_banner_html:
            parts.append(self.top_banner_html)
        for section_title, content in self.html_items:
            if section_title == PART:
                parts.append(content)
                continue
            parts.append(f"""
            <div class="section" id="{slug(section_title)}">
                <button class="collapsible">{escape(section_title)}</button>
                <div class="content">
                    {content}
                </div>
            </div>
            """)
        content = "\n".join(parts)
        start = tpl.index("<!--CONTENT-START-->")
        end = tpl.index("<!--CONTENT-END-->") + len("<!--CONTENT-END-->")
        return tpl[:start] + f"<!--CONTENT-START-->\n{content}\n<!--CONTENT-END-->" + tpl[end:]

    def markdown_report(self, title: str, now: str) -> str:
        parts = [f"# {title or 'PlanExe Project Report'}", "",
                 f"Generated on: {now} with {self.generator_line}. [Discord](https://planexe.org/discord.html), "
                 f"[GitHub]({self.repo_url})", ""] + ([self.metadata_line, ""] if self.metadata_line else [])
        if self.top_banner_markdown:
            parts += [self.top_banner_markdown, ""]
        for section_title, content in self.md_items:
            if section_title == PART:
                parts += [content, ""]
                continue
            parts += [f"# {section_title}", "", content, ""]
        return "\n".join(parts)


KIND_LABEL = {"user_constraint": "user constraint", "decision": "decision",
              "proposed_threshold": "proposed threshold", "estimate": "estimate"}


def canonical_facts_markdown(facts: list[dict]) -> str:
    """The canonical facts table for readers (canonical_facts.md is worded for the later stages)."""
    rows = ["Kind: *user constraint* = from your prompt; *decision* = chosen in this plan; *proposed threshold* = "
            "a pass/fail line proposed in this plan, to be confirmed; *estimate* = not verified.", "",
            "| Fact | Value | Kind | Basis |", "|---|---|---|---|"]
    for f in facts:
        cells = [f.get("key", ""), f.get("value", ""), KIND_LABEL.get(f.get("kind", ""), f.get("kind", "")), f.get("basis", "")]
        rows.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    return "\n".join(rows)


def split_consistency(md: str) -> tuple[str, str]:
    """(dashboard, check) from consistency_recheck.md.

    Dashboard: the decision-kernel table alone. Check: the repair summary, the numbered contradictions and
    the summary. Dropped: the kernel's heading and one-line intro (the section title and the "If NO" column
    say it), and the compiler-style diagnostics block (the same items as the numbered list, kept in
    consistency_recheck.md for tooling)."""
    i = md.find("## Consistency Check")
    head, check = (md, "") if i < 0 else (md[:i], md[i:].replace("## Consistency Check", "", 1))
    k = head.find("## Decision Kernel")
    preface, kernel = (head[:k], head[k:]) if k >= 0 else ("", head)
    kernel = kernel.replace("## Decision Kernel", "", 1)
    kernel = kernel.replace("Any NO means delay, split, downsize or stop, as described.", "", 1).strip()
    check = re.sub(r"Diagnostics \(document vs canonical fact\):\s*```text.*?```\s*", "", check, count=1, flags=re.S)
    return kernel, (preface.strip() + "\n\n" + check.strip()).strip()


def is_decision(c: dict) -> bool:
    return c.get("resolution_type") == "needs_decision" or "canonical" in str(c.get("offending_document", "")).lower()


def banner(r: "Report", title: str, body: str, anchor: str, anchor_title: str) -> None:
    r.top_banner_html += f"""
        <div class="prompt-quality-warning">
            <strong>&#9888; {escape(title)}</strong>
            <p>{escape(body)} See <a href="#{anchor}">{escape(anchor_title)}</a>.</p>
        </div>
"""
    r.top_banner_markdown += ("\n\n" if r.top_banner_markdown else "") + f"> **⚠ {title}**\n>\n> {body} See \"{anchor_title}\"."


def lint_banner(ctx, r: "Report") -> None:
    """Consistency lint: repairable high-severity contradictions remaining after repair = FAILED."""
    items = ctx.read_json("consistency_recheck_raw.json").get("contradictions") or []
    failed = [c for c in items if c.get("severity") == "high" and not is_decision(c)]
    if failed:
        topics = "; ".join(c.get("topic", "") for c in failed[:6])
        banner(r, f"Consistency lint FAILED: {plural(len(failed), 'high-severity contradiction')} "
               f"{'remains' if len(failed) == 1 else 'remain'} after repair",
               f"Some sections disagree on numbers or dates that change a decision: {topics}.",
               slug("Consistency Check"), "Consistency Check")


# Which stages produced each report section (for the per-section validation table).
SECTION_STAGES = {
    "Decisions Required": ["decision_register"],
    "Canonical Facts": ["canonical_facts"],
    "Executive Summary": ["executive_summary"],
    "Pitch": ["create_pitch", "convert_pitch_to_markdown"],
    "Project Plan": ["project_plan"],
    "Strategic Decisions": ["potential_levers", "enrich_levers", "focus_on_vital_few_levers", "strategic_decisions_markdown"],
    "Scenarios": ["candidate_scenarios", "select_scenario"],
    "Assumptions": ["make_assumptions", "distill_assumptions", "review_assumptions", "identify_risks",
                    "physical_locations", "currency_strategy"],
    "Governance": ["governance_phase1_audit", "governance_phase2_bodies", "governance_phase3_impl_plan",
                   "governance_phase4_decision_escalation_matrix", "governance_phase5_monitoring_progress",
                   "governance_phase6_extra"],
    "Related Resources": ["related_resources"],
    "Data Collection": ["data_collection"],
    "Documents to Create and Find": ["identify_documents", "draft_documents_to_create", "draft_documents_to_find"],
    "SWOT Analysis": ["swot_analysis"],
    "Team": ["find_team_members", "enrich_team_members_with_contract_type",
             "enrich_team_members_with_background_story", "enrich_team_members_with_environment_info", "review_team"],
    "Expert Criticism": ["expert_review"],
    "Review Plan": ["review_plan"],
    "Questions & Answers": ["questions_and_answers"],
    "Premortem": ["premortem"],
    "Self Audit": ["self_audit"],
    "Premise Attack": ["premise_attack"],
}
# Sections whose document is part of the consistency lint (repaired copies; assumptions: the short version).
LINTED = {"Executive Summary", "Project Plan", "Review Plan", "Premortem", "Self Audit", "Pitch"}
FIXED_STATUS = {
    "Decisions Required": "derived from the consistency check",
    "Canonical Facts": "reconciled across documents; own arithmetic re-checked",
}


def validation_status(ctx) -> str:
    """What was checked, how, and what was not: sources, consistency, arithmetic, calendar."""
    meta = ctx.run_metadata()
    stages = meta.get("stages") or {}
    searched = {n: st.get("web_searches", 0) for n, st in stages.items() if st.get("web_searches")}
    first = ctx.read_json("consistency_review_raw.json").get("contradictions") or []
    final = ctx.read_json("consistency_recheck_raw.json").get("contradictions") or []
    def count(items, decision):
        sev = [c.get("severity") for c in items if is_decision(c) == decision]
        return {k: sev.count(k) for k in ("high", "medium", "low")}
    r1, rn, dn = count(first, False), count(final, False), count(final, True)
    facts = ctx.read_json("canonical_facts.json").get("facts") or []
    kinds = {k: sum(1 for f in facts if f.get("kind") == k) for k in ("user_constraint", "decision", "proposed_threshold", "estimate")}
    arith = ctx.read_json("arithmetic_check.json")
    mism = arith.get("mismatches") or []

    section_of = {stage: title for title, stages in SECTION_STAGES.items() for stage in stages}
    src = ("; ".join(f"{section_of.get(n, n)} ({k})" for n, k in searched.items()) if searched else "none")
    rows = [
        "| Check | Method | Covers | Result |", "|---|---|---|---|",
        f"| Against sources | Web search | Sections that searched: {src} | {plural(sum(searched.values()), 'search', 'searches')}. "
        f"Other real-world figures (prices, costs, market sizes, laws, precedents) were not verified. |",
        f"| Canonical facts | Reconciled, then the table's own arithmetic re-checked | {len(facts)} key numbers and "
        f"dates | {kinds['user_constraint']} from your prompt, {kinds['decision']} decisions, "
        f"{kinds['proposed_threshold']} proposed thresholds, {kinds['estimate']} estimates. |",
        f"| Internal consistency | Lint against the canonical facts, then repair and re-lint | "
        f"{', '.join(sorted(LINTED))} and the assumptions (summary version) | Before repair: {r1['high']} high / {r1['medium']} "
        f"medium. After: {rn['high']} high / {rn['medium']} medium, plus {dn['high'] + dn['medium']} needing a "
        f"decision (see Decisions Required). |",
        f"| Arithmetic | Deterministic re-computation | Every written calculation (\"a x b = c\") in "
        f"{len(arith.get('by_section') or {})} sections | {arith.get('checked', 0)} checked, {len(mism)} wrong. |",
        "| Calendar | Deterministic | Every \"Month N\" paired with a date | Dates recomputed from the plan start "
        "(Month 0). |",
        "| Schedule | Deterministic | Gantt and WBS | Computed from the estimated durations and dependencies. |", "",
        "## By section", "",
        "| Section | Checks applied |", "|---|---|",
    ]
    by_section = arith.get("by_section") or {}
    for title, names in SECTION_STAGES.items():
        checks = [FIXED_STATUS[title]] if title in FIXED_STATUS else []
        n_search = sum(searched.get(n, 0) for n in names)
        if n_search:
            checks.append(f"web search ({plural(n_search, 'search', 'searches')})")
        if title in LINTED:
            checks.append("consistency lint and repair")
        a = by_section.get(title) or {}
        if a.get("checked"):
            checks.append(f"arithmetic ({plural(a['checked'], 'calculation')}, {a.get('mismatches', 0)} wrong)")
        rows.append(f"| {title} | {'; '.join(checks) if checks else 'none'} |")
    if mism:
        rows += ["", "## Arithmetic errors", "",
                 "Stated results that do not match their own calculation:", "",
                 "| Section | Statement | Stated | Computed |", "|---|---|---|---|"]
        rows += [f"| {m['section']} | {str(m['excerpt']).replace('|', '/')} | {m['stated']} | {m['computed']} |"
                 for m in mism]
    return "\n".join(rows)


def metadata_texts(ctx) -> tuple[str, str, str, str]:
    """(generator line, repo url, line under the title, Metadata section markdown)."""
    from planexe_skill.report_metadata import generator_info
    g = generator_info()
    meta = ctx.run_metadata()
    repo = g.get("repo") or "PlanExeOrg/PlanExe2"
    repo_url = f"https://github.com/{repo}"
    generator_line = g["name"]  # the version is in the Metadata section
    start = meta.get("plan_start_date")
    versions = meta.get("generator_versions_used") or []
    edited = meta.get("hand_edited_files") or []
    adopted = meta.get("adopted_stages") or []
    # The plan date is in the prompt (Initial Prompt Vetted) and in Metadata; under the title only hand edits,
    # which change what the reader is looking at.
    line = f"Includes {plural(len(edited), 'hand-edited intermediary file')} (see Metadata)." if edited else ""

    rows = ["## Generator", "",
            f"- Plan generated by **{g['name']} {g['version']}**",
            f"- Repository: {repo}; commit: {g.get('commit') or 'unknown'}" + (f"; git tag: {g['tag']}" if g.get("tag") else "")
            + ("; working tree had uncommitted changes" if g.get("dirty") else ""),
            f"- Run created: {meta.get('created_at') or 'unknown'}"
            + (f" with {(meta.get('created_by') or {}).get('version')}" if meta.get("created_by") else ""),
            f"- Plan start (Month 0): {start or 'unknown'}; date in the prompt: {meta.get('plan_date_in_prompt') or 'unknown'}",
            f"- Generator versions used by the stages: {', '.join(versions) or 'unknown'}", ""]
    if edited:
        rows += ["## Hand-edited intermediary files", "",
                 "These files were changed after they were generated; the edits were kept and the stages that "
                 "depend on them were regenerated.", ""]
        rows += [f"- `{e['file']}` (stage {e['stage']})" for e in edited]
        rows.append("")
    if adopted:
        rows += ["## Adopted stages", "", "Outputs that existed before this generator recorded them:", "",
                 ", ".join(adopted), ""]
    rows += ["## Stages", "", "| Stage | Generated at | Generator | Models | LLM calls |", "|---|---|---|---|---|"]
    for name, st in (meta.get("stages") or {}).items():
        gen = (st.get("generator") or {}).get("version") or ("adopted" if st.get("adopted") else "unknown")
        rows.append(f"| {name} | {st.get('generated_at') or ''} | {gen} | {', '.join(st.get('models') or []) or '-'} | "
                    f"{st.get('llm_calls', 0)} |")
    return generator_line, repo_url, line, "\n".join(rows)


def run(ctx):
    title = ctx.read_text("wbs_level1_project_title.json")
    r = Report(ctx)
    r.generator_line, r.repo_url, r.metadata_line, metadata_md = metadata_texts(ctx)
    dashboard, consistency = split_consistency(ctx.read_text("consistency_recheck.md"))

    r.part("Part 1: Key decisions and facts")
    r.markdown_text("Decision Dashboard", dashboard, "Go/no-go gates. A NO at an early gate costs the least.")
    r.markdown("Decisions Required", "decision_register.md", "Decisions the plan cannot make by itself.")
    facts = ctx.read_json("canonical_facts.json")
    r.markdown_text("Canonical Facts", canonical_facts_markdown(facts.get("facts") or []),
                    "Key numbers and dates.")
    r.markdown_text("Validation Status", validation_status(ctx), "What was checked, and how.")
    r.markdown("Executive Summary", "repaired_executive_summary.md")
    r.embedded_html("Gantt", "schedule_gantt_dhtmlx.html", subtitle="Unoptimized waterfall. Parallel work not modelled here.")

    r.part("Part 2: Supporting analysis")
    r.markdown("Pitch", "repaired_pitch.md")
    r.markdown("Project Plan", "repaired_project_plan.md")
    r.markdown("Strategic Decisions", "strategic_decisions.md")
    r.markdown_text("Scenarios", heading_to_subtitle(ctx.read_text("scenarios.md"), "Choosing Our Strategic Path",
                                                           "Choosing our strategic path."))
    r.markdown("Assumptions", "consolidate_assumptions_full.md")
    r.markdown("Governance", "consolidate_governance.md")
    r.markdown("Related Resources", "related_resources.md")
    r.markdown("Data Collection", "data_collection.md")
    r.markdown("Documents to Create and Find", "documents_to_create_and_find.md")
    r.markdown_text("SWOT Analysis", strip_heading_emoji(ctx.read_text("swot_analysis.md")))
    r.markdown("Team", "team.md")
    r.markdown_text("Expert Criticism", strip_expert_headings(ctx.read_text("expert_criticism.md")),
                    "Critique and recommended actions from domain experts.")
    r.csv_table("Work Breakdown Structure", "wbs_project_level1_and_level2_and_level3.csv")
    r.markdown("Review Plan", "repaired_review_plan.md")
    r.markdown("Questions & Answers", "repaired_questions_and_answers.md")
    r.markdown("Premortem", "repaired_premortem.md")
    r.markdown("Self Audit", "repaired_self_audit.md")

    r.part("Part 3: Audit trail")
    notes = (facts.get("reconciliation_notes") or "").strip()
    if notes:
        consistency += "\n\n## How the canonical facts were reconciled\n\n" + notes
    r.markdown_text("Consistency Check", consistency, "Contradictions between the core documents, after repair.")
    r.initial_prompt_vetted("Initial Prompt Vetted")
    r.markdown("Prompt Adherence", "prompt_adherence.md")
    r.markdown_text("Metadata", metadata_md, "Which generator version and models produced each part.")
    lint_banner(ctx, r)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx.write_text("report.html", r.html_report(title, now))
    ctx.write_text("report.md", r.markdown_report(title, now))
