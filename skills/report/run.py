import csv
import io
import json
import re
from datetime import datetime
from html import escape

from planexe_skill.shared.markdown_html import render as md_to_html

EXECUTE_PLAN_SECTION_HIDDEN = True


class Report:
    def __init__(self, ctx):
        self.ctx = ctx
        self.html_items: list[tuple[str, str]] = []
        self.md_items: list[tuple[str, str]] = []
        self.top_banner_html = ""
        self.top_banner_markdown = ""
        self.head: list[str] = []
        self.scripts: list[str] = []

    def markdown(self, title: str, name: str) -> None:
        md = self.ctx.read_text(name)
        self.html_items.append((title, md_to_html(md)))
        self.md_items.append((title, md))

    def markdown_text(self, title: str, md: str) -> None:
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
        out = ['<table border="1" class="dataframe dataframe">', "  <thead>", '    <tr style="text-align: right;">']
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
        sub = f"<p>{escape(subtitle)}</p>\n" if subtitle else ""
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
        <p>Why this fails.</p>
        {md_to_html(premise_md)}
        """
        self.html_items.append((title, html))
        parts = ["## Initial Prompt", "", "```text", prompt, "```", "", "## Prompt Screening", "", screening_md, "",
                 "## Redline Gate", "", redline_md, "", "## Premise Attack", "", "Why this fails.", "", premise_md]
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
        <p class="planexe-report-info">Generated on: {now} with PlanExe. <a href="https://planexe.org/discord.html">Discord</a>, <a href="https://github.com/PlanExeOrg/PlanExe">GitHub</a></p>
        """]
        if self.top_banner_html:
            parts.append(self.top_banner_html)
        for section_title, content in self.html_items:
            parts.append(f"""
            <div class="section">
                <button class="collapsible">{section_title}</button>
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
                 f"Generated on: {now} with PlanExe. [Discord](https://planexe.org/discord.html), "
                 f"[GitHub](https://github.com/PlanExeOrg/PlanExe)", ""]
        if self.top_banner_markdown:
            parts += [self.top_banner_markdown, ""]
        for section_title, content in self.md_items:
            parts += [f"# {section_title}", "", content, ""]
        return "\n".join(parts)


def split_consistency(md: str) -> tuple[str, str]:
    """Decision kernel (short, for the top of the report) vs the long consistency check (analysis part)."""
    i = md.find("## Consistency Check")
    if i < 0:
        return md, ""
    j = md.find("## Summary", i)
    kernel = md[:i].rstrip()
    check = md[i:].replace("## Consistency Check", "", 1).strip()
    if j >= 0:  # keep the one-paragraph summary with the dashboard as well
        kernel += "\n\n## Consistency\n\n" + md[j:].replace("## Summary", "", 1).strip()
        kernel += "\n\nDetails: see the \"Consistency Check\" and \"Canonical Facts\" sections."
    return kernel, check


def lint_banner(ctx, r: "Report") -> None:
    """Consistency lint: surface high-severity contradictions at the very top of the report."""
    items = ctx.read_json("consistency_recheck_raw.json").get("contradictions") or []
    high = [c for c in items if c.get("severity") == "high"]
    if not high:
        return
    topics = "; ".join(escape(c.get("topic", "")) for c in high[:6])
    r.top_banner_html += f"""
        <div class="prompt-quality-warning">
            <strong>&#9888; Consistency lint FAILED: {len(high)} high-severity contradiction(s) remain after repair</strong>
            <p>Some sections disagree on numbers or dates that change a decision: {topics}.
            See the "Consistency Check" section for the canonical values and resolutions.</p>
        </div>
"""
    r.top_banner_markdown += ("\n\n" if r.top_banner_markdown else "") + (
        f"> **⚠ Consistency lint FAILED: {len(high)} high-severity contradiction(s) remain after repair**\n>\n"
        f"> {'; '.join(c.get('topic', '') for c in high[:6])}. See \"Consistency Check\".")


def run(ctx):
    title = ctx.read_text("wbs_level1_project_title.json")
    r = Report(ctx)
    dashboard, consistency = split_consistency(ctx.read_text("consistency_recheck.md"))
    r.markdown_text("Decision Dashboard", dashboard)
    r.markdown("Executive Summary", "repaired_executive_summary.md")
    r.embedded_html("Gantt", "schedule_gantt_dhtmlx.html", subtitle="Unoptimized waterfall. Parallel work not modelled here.")
    r.markdown("Pitch", "repaired_pitch.md")
    r.markdown("Project Plan", "repaired_project_plan.md")
    r.markdown("Strategic Decisions", "strategic_decisions.md")
    r.markdown("Scenarios", "scenarios.md")
    r.markdown("Assumptions", "consolidate_assumptions_full.md")
    r.markdown("Governance", "consolidate_governance.md")
    r.markdown("Related Resources", "related_resources.md")
    r.markdown("Data Collection", "data_collection.md")
    r.markdown("Documents to Create and Find", "documents_to_create_and_find.md")
    r.markdown("SWOT Analysis", "swot_analysis.md")
    r.markdown("Team", "team.md")
    r.markdown("Expert Criticism", "expert_criticism.md")
    r.csv_table("Work Breakdown Structure", "wbs_project_level1_and_level2_and_level3.csv")
    r.markdown("Review Plan", "repaired_review_plan.md")
    r.markdown("Questions & Answers", "repaired_questions_and_answers.md")
    r.markdown("Premortem", "repaired_premortem.md")
    r.markdown("Self Audit", "repaired_self_audit.md")
    r.markdown_text("Consistency Check", consistency)
    r.markdown("Canonical Facts", "canonical_facts.md")
    r.initial_prompt_vetted("Initial Prompt Vetted")
    r.markdown("Prompt Adherence", "prompt_adherence.md")
    lint_banner(ctx, r)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx.write_text("report.html", r.html_report(title, now))
    ctx.write_text("report.md", r.markdown_report(title, now))
