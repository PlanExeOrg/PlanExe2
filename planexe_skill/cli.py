"""Command line interface.

    python -m planexe_skill create RUN_DIR --prompt-file prompt.txt
    python -m planexe_skill run RUN_DIR [--only STAGE ...] [--until STAGE] [--force STAGE] [--force-downstream STAGE]
    python -m planexe_skill status RUN_DIR
    python -m planexe_skill explain RUN_DIR STAGE
    python -m planexe_skill graph
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from planexe_skill import SKILLS_ROOT
from planexe_skill.dag import Dag, DagError
from planexe_skill.llm import get_backend
from planexe_skill.manifest import Manifest
from planexe_skill.planexe import plural
from planexe_skill.runner import Runner, StageFailure
from planexe_skill.skill import load_skills

PLAN_RAW = "plan_raw.json"
START_TIME = "start_time.json"
METADATA = "planexe_metadata.json"
PIPELINE_VERSION = 2


def create_run_dir(run_dir: Path, prompt: str | None = None, plan_raw: Path | None = None,
                   start: datetime | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    local = (start or datetime.now()).astimezone()
    if plan_raw is not None:
        (run_dir / PLAN_RAW).write_text(plan_raw.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        assert prompt is not None
        data = {"plan_prompt": prompt, "pretty_date": local.strftime("%Y-%b-%d")}
        (run_dir / PLAN_RAW).write_text(json.dumps(data, indent=2), encoding="utf-8")
    utc = local.astimezone(timezone.utc).replace(microsecond=0)
    st = {"server_iso_utc": utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
          "server_iso_local": local.replace(microsecond=0).isoformat(),
          "server_timezone_name": local.tzname() or "unknown"}
    (run_dir / START_TIME).write_text(json.dumps(st, indent=2), encoding="utf-8")
    from planexe_skill.provenance import generator_brief
    meta = {"pipeline_version": PIPELINE_VERSION, "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "generator": generator_brief()}
    (run_dir / METADATA).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _dag(args) -> Dag:
    return Dag(load_skills(Path(args.skills)))


def _backend(args):
    if args.backend == "claude":
        models = {}
        if args.model_high:
            models["high"] = args.model_high
        if args.model_low:
            models["low"] = args.model_low
        if args.model_mid:
            models["mid"] = args.model_mid
        return get_backend("claude", models=models)
    return get_backend(args.backend)


def cmd_create(args) -> int:
    run_dir = Path(args.run_dir)
    if (run_dir / PLAN_RAW).exists() and not args.overwrite:
        print(f"{run_dir / PLAN_RAW} already exists (use --overwrite).", file=sys.stderr)
        return 2
    for f in (args.prompt_file, args.plan_raw):
        if f and not Path(f).is_file():
            print(f"error: file not found: {f}", file=sys.stderr)
            return 2
    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else args.prompt
    if prompt is None and args.plan_raw is None:
        print("give --prompt-file, --prompt or --plan-raw", file=sys.stderr)
        return 2
    start = None
    if getattr(args, "start_date", None):
        try:
            start = datetime.fromisoformat(args.start_date)
        except ValueError:
            print(f"error: --start-date must be YYYY-MM-DD, got {args.start_date!r}", file=sys.stderr)
            return 2
    create_run_dir(run_dir, prompt=prompt, plan_raw=Path(args.plan_raw) if args.plan_raw else None, start=start)
    print(f"Created {run_dir}. Next: python -m planexe_skill run {run_dir}")
    return 0


def cmd_run(args) -> int:
    run_dir = Path(args.run_dir)
    if args.prompt_file or args.prompt or args.plan_raw:
        if not (run_dir / PLAN_RAW).exists():
            args.overwrite = False
            rc = cmd_create(args)
            if rc:
                return rc
    if not run_dir.exists():
        print(f"run dir {run_dir} does not exist. Create it with: python -m planexe_skill create {run_dir} "
              f"--prompt-file PROMPT.txt", file=sys.stderr)
        return 2
    runner = Runner(_dag(args), run_dir, _backend(args), workers=args.workers, only=args.only, until=args.until,
                    force=args.force, force_downstream=args.force_downstream)
    if args.dry_run:
        planned = runner.plan()
        print(f"{plural(len(planned), 'stage')} would run:")
        for p in planned:
            print("  " + p)
        return 0
    try:
        result = runner.run()
    except StageFailure as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0 if result.ok else 1


def cmd_status(args) -> int:
    run_dir = Path(args.run_dir)
    dag = _dag(args)
    runner = Runner(dag, run_dir, get_backend("fake"))
    planned = set(runner.plan())
    manifest = Manifest.load(run_dir)
    for name in dag.order():
        st = manifest.status(dag.skills[name], run_dir)
        if name in planned:
            why = "; ".join(st.reasons) if st.dirty else "upstream will re-run"
            mark = "dirty "
        else:
            why = "edited: " + ", ".join(st.edited_outputs) if st.edited_outputs else ""
            mark = "clean "
        print(f"{mark} {name:<48} {why}")
    print(f"\n{len(planned)}/{len(dag.skills)} stages would run.")
    prog = run_dir / ".planexe_skill" / "progress.json"
    if prog.exists():
        p = json.loads(prog.read_text())
        print(f"last progress update {p['updated_at']}: {p['stages_done']}/{p['stages_total']} stages, "
              f"running: {', '.join(p['running']) or '-'}, eta {p['eta_seconds']:.0f}s")
    return 0


def cmd_explain(args) -> int:
    runner = Runner(_dag(args), Path(args.run_dir), get_backend("fake"))
    print("\n".join(runner.explain(args.stage)))
    return 0


def cmd_check_prompt(args) -> int:
    from planexe_skill.prompt_check import check_prompt, format_result
    if args.prompt_file and not Path(args.prompt_file).is_file():
        print(f"error: file not found: {args.prompt_file}", file=sys.stderr)
        return 2
    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else args.prompt
    if not prompt or not prompt.strip():
        print("give --prompt-file or --prompt", file=sys.stderr)
        return 2
    result = check_prompt(prompt, get_backend("claude"))
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_result(result))
    return 0 if result.get("ready") else 1


def cmd_graph(args) -> int:
    dag = _dag(args)
    if args.dot:
        print("digraph planexe {")
        for n in dag.order():
            for d in sorted(dag.deps(n)):
                print(f'  "{d}" -> "{n}";')
        print("}")
        return 0
    for i, n in enumerate(dag.order()):
        s = dag.skills[n]
        print(f"{i:3d} {n:<48} tier={s.tier:<4} calls~{s.est_llm_calls:<3} deps: {', '.join(sorted(dag.deps(n))) or '-'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m planexe_skill", description="Run PlanExe skills as a DAG.")
    ap.add_argument("--skills", default=str(SKILLS_ROOT), help="skills directory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_prompt_args(p):
        p.add_argument("--prompt-file", help="text file with the plan prompt")
        p.add_argument("--prompt", help="plan prompt text")
        p.add_argument("--plan-raw", help="copy an existing plan_raw.json (keeps its date)")
        p.add_argument("--start-date", help="plan start date (Month 0), YYYY-MM-DD; past or future; default today")

    p = sub.add_parser("create", help="create a run dir from a prompt")
    p.add_argument("run_dir")
    add_prompt_args(p)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("run", help="run all dirty stages")
    p.add_argument("run_dir")
    add_prompt_args(p)
    p.add_argument("--only", nargs="+", metavar="STAGE", help="run only these stages (inputs must exist)")
    p.add_argument("--until", nargs="+", metavar="STAGE", help="run these stages and everything upstream")
    p.add_argument("--force", nargs="+", default=[], metavar="STAGE", help="re-run these stages even if clean")
    p.add_argument("--force-downstream", nargs="+", default=[], metavar="STAGE",
                   help="re-run these stages and everything downstream")
    p.add_argument("--workers", type=int, default=4, help="max concurrent LLM calls (default 4)")
    p.add_argument("--backend", default="claude", choices=["claude", "fake"])
    p.add_argument("--model-high", help="model for tier=high stages")
    p.add_argument("--model-mid", help="model for tier=mid stages")
    p.add_argument("--model-low", help="model for tier=low stages")
    p.add_argument("--dry-run", action="store_true", help="only print which stages would run")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="show which stages are dirty and why")
    p.add_argument("run_dir")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("explain", help="explain one stage's state")
    p.add_argument("run_dir")
    p.add_argument("stage")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("check-prompt", help="pre-flight check of a plan prompt (1 LLM call); exit 0 = ready")
    p.add_argument("--prompt-file", help="text file with the plan prompt")
    p.add_argument("--prompt", help="plan prompt text")
    p.add_argument("--json", action="store_true", help="print the raw result as JSON")
    p.set_defaults(func=cmd_check_prompt)

    p = sub.add_parser("graph", help="print stages in topological order")
    p.add_argument("--dot", action="store_true", help="graphviz output")
    p.set_defaults(func=cmd_graph)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except DagError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
