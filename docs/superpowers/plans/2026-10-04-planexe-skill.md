# PlanExe-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port PlanExe's 73-stage Luigi pipeline into stdlib-only Python skills run by a lightweight DAG with dirty detection and ETA progress.

**Architecture:** Skills live in `skills/<stage>/` (SKILL.md frontmatter declares input/output files, `run.py` does the work). `planexe_skill/` builds the DAG from file producer/consumer relations, decides dirtiness from a content-hash manifest, and executes stages on a thread pool, calling `claude -p --json-schema` for LLM work. `verify/` compares outputs against PlanExe-web baseline zips.

**Tech Stack:** Python >= 3.11 stdlib only (`graphlib`, `concurrent.futures`, `subprocess`, `hashlib`, `json`, `unittest`), Claude Code CLI 2.1+.

**Note on detail level:** code for the runtime is specified by interface + tests here; the
73 stage ports follow one repeatable recipe (Task 6) because each stage's content comes
from the corresponding PlanExe source file listed in `docs/reference/planexe_pipeline_dag.json`.

## Global Constraints

- Python >= 3.11, stdlib only. No `requirements.txt` entries.
- Output filenames and JSON/markdown structure identical to PlanExe (`worker_plan_api/filenames.py`).
- Tier `high` = `--model claude-sonnet-5-5 --effort high`; tier `low` = `--model claude-haiku-4-5-20251001`.
- 4 workers default.
- No napkin_math. all_details mode only.
- Don't hardcode any plan-specific content into skills.
- Commit message trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: Skill loading + DAG

**Files:** Create `planexe_skill/__init__.py`, `planexe_skill/skill.py`, `planexe_skill/dag.py`; Test `tests/test_dag.py`.

**Interfaces — produces:**
- `parse_frontmatter(text: str) -> tuple[dict, str]` — YAML subset: `key: scalar`, `key: [a, b]`, block lists `- item`.
- `@dataclass Skill(name, description, inputs: list[str], outputs: list[str], tier: str, est_llm_calls: int, dir: Path)`; `Skill.output_patterns()` (outputs containing `{n}` as regex), `load_skill(dir) -> Skill`, `load_skills(root) -> dict[str, Skill]`.
- `Dag(skills)`: `.producer_of(filename) -> str|None`, `.deps(name) -> set[str]`, `.dependents(name) -> set[str]`, `.order() -> list[str]` (deterministic topo order), `.downstream(name) -> set[str]`, `.root_inputs() -> set[str]`. Raises `DagError` with a readable message on cycles, duplicate producers, unknown stages.

- [ ] Tests: frontmatter parsing (inline list, block list, ints); DAG edges derived from files; cycle reported with the cycle path; duplicate producer error; topo order deterministic.
- [ ] Implement; run `python3 -m unittest tests.test_dag -v`; commit.

### Task 2: Manifest + dirty detection

**Files:** Create `planexe_skill/manifest.py`; Test `tests/test_manifest.py`.

**Produces:** `hash_file(p) -> str`, `hash_dir(p) -> str` (ignores `__pycache__`), `Manifest.load(run_dir)`, `.save()`, `.record(stage, skill_hash, inputs: dict[str,str], outputs: dict[str,str])`, `.status(skill, run_dir, dag) -> StageStatus(dirty: bool, reasons: list[str])`, `.adopt(...)`, `.forget(stage)`, `existing_outputs(skill, run_dir) -> list[str]` (expands `{n}` by globbing).

Rules: missing output → dirty; skill hash changed → dirty; input hash != recorded → dirty; not in manifest but all outputs present → adopt (clean). Edited outputs keep stage clean.

- [ ] Tests for each rule incl. adopt and `{n}` outputs; implement; commit.

### Task 3: LLM backends

**Files:** Create `planexe_skill/llm/__init__.py`, `base.py`, `claude_cli.py`, `fake.py`; Test `tests/test_llm.py`.

**Produces:** `LLMResult(data: Any, text: str, metadata: dict)`; `Backend.complete(system: str, user: str, schema: dict|None, tier: str) -> LLMResult`; `ClaudeCLIBackend(models={'high':..., 'low':...}, efforts={...}, timeout=600, retries=2)` running
`claude -p --output-format json --model M [--effort E] --tools "" --system-prompt S [--json-schema J] --no-session-persistence` with the user prompt on stdin; parses `structured_output`/`result`; raises `LLMError` containing command, exit code, stderr tail. `FakeBackend(responder)` for tests. `get_backend(name)`.

- [ ] Tests: command construction, JSON envelope parsing, error message contents (subprocess mocked); one opt-in live smoke test gated by `PLANEXE_SKILL_LIVE=1`.
- [ ] Implement; verify live once with a tiny schema; commit.

### Task 4: Context, runner, progress, CLI

**Files:** Create `planexe_skill/context.py`, `runner.py`, `progress.py`, `cli.py`, `__main__.py`; Test `tests/test_runner.py`.

**Produces:** `SkillContext(run_dir, skill, backend, progress)` with `read_text/read_json/write_text/write_json/llm/log/exists`; `Runner(dag, run_dir, backend, workers=4, only=None, force=set(), force_downstream=set())`; `.plan() -> list[str]` (stages to run), `.run() -> RunResult(ok, failed, blocked)`; `Progress` writing `progress.json` and status line with ETA; timings history in `~/.planexe_skill/timings.json` (override with `PLANEXE_SKILL_HOME`).
CLI: `python -m planexe_skill run RUN_DIR [--prompt-file F] [--only S...] [--force S] [--force-downstream S] [--workers N] [--backend claude|fake] [--model-high M] [--model-low M]`; `status RUN_DIR`; `explain RUN_DIR STAGE`; `graph`.

- [ ] Tests with toy skills in a temp dir + FakeBackend: runs in topo order, skips clean, re-runs downstream after edit, failure blocks dependents but independent stages finish, error message includes rerun command.
- [ ] Implement; commit; push branch (Phase 1 done).

### Task 5: Verification harness

**Files:** Create `verify/baselines.py`, `verify/structure.py`, `verify/judge.py`, `verify/eval_stage.py`; Test `tests/test_structure.py`.

**Produces:** `extract_baseline(name) -> Path`; `compare_structure(a: Path, b: Path) -> list[str]` (JSON shape diff ignoring list lengths, markdown heading outline diff); `judge(file_a, file_b, context) -> {'winner': 'new'|'baseline'|'tie', 'rationale': str}` blind + swapped; `eval_stage.py STAGE [--baselines ...]` → seeds a work dir from baseline, deletes stage outputs, runs stage, writes `verify/results/<stage>.json` and prints summary table.

- [ ] Structure tests; implement; commit.

### Task 6: Stage port recipe (repeat for each stage in topo order)

For stage S (order in `docs/reference/planexe_pipeline_dag.json`):
1. Read PlanExe node `plan/nodes/<S>.py` and business-logic module(s).
2. Create `skills/S/SKILL.md` (frontmatter inputs/outputs = node inputs/outputs), copy prompts verbatim into `prompts/`, convert pydantic models to JSON Schema in `schema*.json`, port deterministic post-processing (markdown rendering, cleaning) into `run.py`.
3. Raw JSON keeps PlanExe keys; `metadata` filled from `LLMResult.metadata`.
4. `python3 verify/eval_stage.py S` on 4 dev baselines. Fix until structure matches and win/tie >= 3/4.
5. Log results + tweaks in `report.md`; commit; push after each group.

Groups: (a) stages 0–9, (b) levers + scenarios 10–23, (c) assumptions 24–32, then remaining in topo order.

### Task 7: Final end-to-end verification

- [ ] `python -m planexe_skill run runs/<name> --prompt-file <baseline>/plan.txt` for euro_adoption, battery_breakthrough, gibraltar_tunnel, datacenter_in_france.
- [ ] `python3 verify/eval_run.py runs/<name> <baseline>` judges every file; revisit losing stages; record in `report.md`; commit + push.
