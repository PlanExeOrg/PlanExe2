# docs.planexe.org from PlanExe2

## Goal

docs.planexe.org is built from PlanExe v1 (`PlanExeOrg/PlanExe/docs/`). Switch it to PlanExe2. Only
`PlanExe2/docs/website/` is published; the rest of `PlanExe2/docs/` (`porting_guide.md`, `reference/`,
`superpowers/`) stays internal.

## Decisions

- **v1 docs are dropped from the site.** They remain readable on GitHub in `PlanExe/docs/`. Old URLs
  (e.g. `/mcp/claude/`) return 404; accepted.
- **Small core set of pages** at launch, rewritten for v2. No per-stage pages, no prompt-writing guide
  (the `make-plan` interview writes the prompt), no FAQ.
- **PlanExe-docs stays the builder** (approach A). It checks out PlanExe2 instead of PlanExe. GitHub Pages
  setup, CNAME and domain are unchanged. No auto-rebuild trigger from PlanExe2 for now; a rebuild happens on
  push to PlanExe-docs or via `workflow_dispatch`.

## PlanExe2: `docs/website/`

| file | content |
|---|---|
| `index.md` | what PlanExe2 is; v1 vs v2 in two lines; link to PlanExe v1 on GitHub |
| `getting_started.md` | requirements (Python 3.11+, logged-in Claude Code CLI, usage budget: 220-260 LLM calls, 65-90 min); recommended path: clone, start `claude`, ask for a plan; what the `make-plan` interview does (asks until it has enough, shows the drafted prompt, checks it, launches only after confirmation); what to expect while it runs (progress with ETA, `runs/<yyyymmdd>_<name>/report.html`); without git; sandbox note; why there is no pip package |
| `report.md` | the three parts of the report: key decisions and facts, supporting analysis, audit trail |
| `commands.md` | by-hand path (`check-prompt`, `create`, `run`) with a short note on what a hand-written prompt covers; command table and options; stopping; failures and resuming; versioning and report metadata |
| `how_it_works.md` | DAG runner; skill folder layout; tiers; dirtiness (manifest hashes); editing an intermediary file and re-running; adopting PlanExe v1 files; stages added by PlanExe2 |
| `assets/logo.svg`, `assets/favicon.png` | copied from `PlanExe/docs/assets/` |
| `assets/javascripts/copy-all.js`, `assets/stylesheets/copy-all.css` | copied from `PlanExe/docs/assets/` (referenced by `mkdocs.yml`) |

Source material is the PlanExe2 `README.md`, `CLAUDE.md` and `.claude/skills/make-plan/SKILL.md`; v1's
`plan_output_anatomy.md` for the shape of `report.md`. Tone: factual and direct, no marketing language.

The README is shortened to an overview plus getting started, linking to docs.planexe.org for the command
reference, report contents and internals, so the two do not drift.

## PlanExe-docs

- `build.py`: defaults `PLANEXE_REPO=../PlanExe2`, `DOCS_SOURCE_DIR=docs/website`. Remove the component
  README copying, the `nav-status.css` override and the proposals nav injection (and the `yaml` import if
  unused).
- `.github/workflows/deploy.yml`: check out `PlanExeOrg/PlanExe2`; `DOCS_SOURCE_DIR=docs/website`.
- `mkdocs.yml`: flat nav (Welcome, Getting started, The report, Commands, How it works); `repo_url` and
  `repo_name` → PlanExeOrg/PlanExe2; `edit_uri: edit/main/docs/website/`; drop `nav-status.css` from
  `extra_css`; theme, social cards and analytics unchanged. `site_description` updated if v1 wording no
  longer fits.
- `README.md`, `AGENTS.md`: source and logo paths point to PlanExe2 `docs/website/`.

## Verification

- `python build.py` in PlanExe-docs against the local PlanExe2 checkout completes without mkdocs warnings.
- `site/` contains no `porting_guide`, `reference` or `superpowers` paths.
- Pages render correctly via `serve.py` (nav, logo, social cards, internal links).
