"""Evaluate one or more stages against the PlanExe baselines.

For every baseline: copy the baseline run into a work dir, delete only this stage's outputs,
run the stage (upstream inputs = baseline files), then compare structure and ask the judge.

    python3 -m verify.eval_stage identify_purpose plan_type
    python3 -m verify.eval_stage identify_purpose --no-judge
    python3 -m verify.eval_stage identify_purpose --reuse     # re-judge existing outputs
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from planexe_skill import REPO_ROOT, SKILLS_ROOT
from planexe_skill.dag import Dag
from planexe_skill.llm import get_backend
from planexe_skill.manifest import existing_outputs
from planexe_skill.runner import Runner
from planexe_skill.skill import Skill, load_skills
from verify.baselines import DEV_BASELINES, INFRA_FILES, WORK_DIR, extract_baseline
from verify.judge import judge_pair, load_for_judging
from verify.structure import compare_json_files, compare_markdown, template_headings

RESULTS_DIR = REPO_ROOT / "verify" / "results"


def files_to_judge(skill: Skill) -> list[str]:
    explicit = skill.meta.get("judge")
    if explicit:
        return list(explicit) if isinstance(explicit, list) else [explicit]
    fixed = skill.fixed_outputs()
    md = [o for o in fixed if o.endswith(".md")]
    if md:
        return md
    clean = [o for o in fixed if o.endswith(".json") and not o.endswith("_raw.json")]
    if clean:
        return clean
    return [o for o in fixed if o.endswith(".json")][:1]


def seed_work_dir(skill: Skill, baseline: str, work: Path) -> None:
    src = extract_baseline(baseline)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file() and f.name not in INFRA_FILES:
            shutil.copy2(f, work / f.name)
    for o in existing_outputs(skill, work):
        (work / o).unlink()


def run_stage(dag: Dag, skill: Skill, work: Path, workers: int, model_overrides: dict) -> tuple[bool, str]:
    out = io.StringIO()
    backend = get_backend("claude", models=model_overrides)
    runner = Runner(dag, work, backend, workers=workers, only=[skill.name], stream=out, heartbeat_secs=120)
    result = runner.run()
    (work / ".planexe_skill").mkdir(exist_ok=True)
    (work / ".planexe_skill" / "eval_stdout.txt").write_text(out.getvalue())
    return result.ok, out.getvalue()


def structure_check(skill: Skill, baseline_dir: Path, work: Path, templates: dict) -> list[str]:
    problems = []
    for o in skill.fixed_outputs():
        b, c = baseline_dir / o, work / o
        if not b.exists():
            continue
        if not c.exists():
            problems.append(f"{o}: missing")
            continue
        if o.endswith(".json"):
            problems += [f"{o}: {p}" for p in compare_json_files(b, c)]
        elif o.endswith(".md"):
            problems += [f"{o}: {p}" for p in compare_markdown(templates.get(o, []), c.read_text())]
    for pattern in skill.pattern_outputs():
        rx = Skill.pattern_regex(pattern)
        base_files = sorted(p for p in baseline_dir.iterdir() if rx.match(p.name))
        new_files = sorted(p for p in work.iterdir() if rx.match(p.name))
        if base_files and not new_files:
            problems.append(f"{pattern}: no files produced (baseline has {len(base_files)})")
        elif base_files and new_files and pattern.endswith(".json"):
            problems += [f"{new_files[0].name}: {p}" for p in compare_json_files(base_files[0], new_files[0])]
    return problems


_TIMESTAMP_LINE = re.compile(r"^.*Generated on: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.*$", re.M)
_HTML_TAGS = ["<h1", "<h2", "<h3", "<h4", "<ul", "<ol", "<li", "<table", "<tr", "<strong", "<em>", "<code", "<pre",
              "<script", "<div"]


def deterministic_equal(baseline: Path, candidate: Path) -> bool:
    """Byte equality, ignoring 'Generated on' timestamps. HTML files are compared by tag profile
    (the stdlib markdown renderer is not byte-compatible with Python-Markdown): every tag count
    must be within 2% of the baseline's."""
    a, b = baseline.read_bytes(), candidate.read_bytes()
    if a == b:
        return True
    ta = _TIMESTAMP_LINE.sub("", a.decode("utf-8", "replace"))
    tb = _TIMESTAMP_LINE.sub("", b.decode("utf-8", "replace"))
    if ta == tb:
        return True
    if baseline.suffix == ".html":
        # PlanExe-web injects Google Analytics (2 <script> tags) into published reports.
        ta = re.sub(r"<script async src=\"https://www.googletagmanager.com.*?</script>\s*<script>.*?</script>", "",
                    ta, flags=re.S)
        for tag in _HTML_TAGS:
            ca, cb = ta.count(tag), tb.count(tag)
            if abs(ca - cb) > max(1, 0.02 * ca):
                return False
        return True
    return False


def eval_one(dag: Dag, skill: Skill, baseline: str, args, templates: dict) -> dict:
    work = WORK_DIR / "stage_runs" / skill.name / baseline
    baseline_dir = extract_baseline(baseline)
    t0 = time.time()
    ok, log = True, ""
    have = work.exists() and all((work / o).exists() for o in skill.fixed_outputs())
    if not (args.reuse and have):
        seed_work_dir(skill, baseline, work)
        ok, log = run_stage(dag, skill, work, args.workers, args.models)
    rec: dict = {"baseline": baseline, "ran_ok": ok, "seconds": round(time.time() - t0, 1)}
    if not ok:
        rec["error"] = log[-3000:]
        return rec
    rec["structure_problems"] = structure_check(skill, baseline_dir, work, templates)
    if skill.est_llm_calls == 0:
        # Deterministic stage: must reproduce the baseline (given identical inputs).
        rec["identical"] = {o: deterministic_equal(baseline_dir / o, work / o)
                            for o in existing_outputs(skill, baseline_dir) if (work / o).exists()}
    if args.no_judge or skill.est_llm_calls == 0:
        return rec
    plan = (baseline_dir / "plan.txt").read_text()
    desc = f"{skill.name}: {skill.description}\n\n{skill.body.strip()[:3000]}"
    judgments = {}
    for f in files_to_judge(skill):
        if not (baseline_dir / f).exists() or not (work / f).exists():
            continue
        judgments[f] = judge_pair(plan, desc, f, load_for_judging(baseline_dir / f), load_for_judging(work / f),
                                  seed=hash((skill.name, baseline, f)) & 0xFFFF)
    rec["judgments"] = judgments
    return rec


def summarize(stage: str, records: list[dict]) -> str:
    lines = [f"\n=== {stage} ==="]
    wins = ties = losses = 0
    for r in records:
        if not r.get("ran_ok"):
            lines.append(f"  {r['baseline']:<40} RUN FAILED")
            losses += 1
            continue
        sp = r.get("structure_problems", [])
        js = r.get("judgments", {})
        verdicts = []
        for f, j in js.items():
            verdicts.append(f"{f}={j['verdict']}({j['score_new']:.1f} vs {j['score_baseline']:.1f})")
        worst = "loss" if any(j["verdict"] == "baseline" for j in js.values()) else (
            "win" if js and all(j["verdict"] == "new" for j in js.values()) else "tie")
        if js:
            wins += worst == "win"
            ties += worst == "tie"
            losses += worst == "loss"
        if "identical" in r:
            same = all(r["identical"].values())
            wins += 0
            ties += same
            losses += not same
            diffs = [o for o, v in r["identical"].items() if not v]
            verdicts.append("identical" if same else f"DIFFERS: {', '.join(diffs)}")
        lines.append(f"  {r['baseline']:<40} struct={'OK' if not sp else str(len(sp)) + ' problems'} "
                     f"{' '.join(verdicts)} [{r['seconds']}s]")
        for p in sp[:8]:
            lines.append(f"      - {p}")
    passed = all(r.get("ran_ok") and not r.get("structure_problems") for r in records) and \
        (wins + ties) >= max(1, len(records) - 1)
    lines.append(f"  => wins {wins}, ties {ties}, losses {losses}: {'PASS' if passed else 'NEEDS WORK'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stages", nargs="+")
    ap.add_argument("--baselines", nargs="+", default=DEV_BASELINES)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="don't re-run the stage if its outputs exist")
    ap.add_argument("--workers", type=int, default=2, help="LLM calls per baseline run")
    ap.add_argument("--model-high")
    ap.add_argument("--model-low")
    args = ap.parse_args(argv)
    args.models = {k: v for k, v in (("high", args.model_high), ("low", args.model_low)) if v}
    dag = Dag(load_skills(SKILLS_ROOT))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for stage in args.stages:
        skill = dag.skills[stage]
        base_dirs = [extract_baseline(b) for b in DEV_BASELINES]
        templates = {o: template_headings([(d / o).read_text() for d in base_dirs if (d / o).exists()])
                     for o in skill.fixed_outputs() if o.endswith(".md")}
        with ThreadPoolExecutor(max_workers=len(args.baselines)) as ex:
            records = list(ex.map(lambda b: eval_one(dag, skill, b, args, templates), args.baselines))
        (RESULTS_DIR / f"{stage}.json").write_text(json.dumps(
            {"stage": stage, "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "records": records},
            indent=2, ensure_ascii=False))
        text = summarize(stage, records)
        print(text, flush=True)
        if "NEEDS WORK" in text:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
