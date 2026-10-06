# Instructions for coding agents

To generate a plan for the user, use the `make-plan` skill (`.claude/skills/make-plan/SKILL.md`): it
interviews the user to turn a vague idea into a concrete prompt, checks it with
`python3 -m planexe_skill check-prompt`, and asks for explicit confirmation before launching (a full plan is
~200 LLM calls, ~1 hour). The launch steps:

1. Write the agreed prompt to a text file (flowing prose, ~300-800 words: objective, scope, location,
   budget, timeline, stakeholders, constraints, success criteria).
2. `python3 -m planexe_skill create runs/<name> --prompt-file <file> [--start-date YYYY-MM-DD]`
3. `python3 -m planexe_skill run runs/<name>` (run in background; it prints progress lines with an ETA,
   and mirrors them to `runs/<name>/.planexe_skill/progress.json`). The child `claude` process needs
   keychain access, so run it outside any sandbox.
4. On failure the runner prints the failing stage, the error, the log path and a retry command.
5. The result is `runs/<name>/report.html` (and `report.md`).

When editing skills: a skill must only read files listed in its SKILL.md `inputs` and write files
listed in `outputs` (the runner enforces this). Run `python3 -m unittest discover -s tests -t .`.
