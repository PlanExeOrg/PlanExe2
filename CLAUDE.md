# Instructions for coding agents

To generate a plan for the user:

1. Write the user's plan description to a text file (flowing prose, ~300-800 words works best:
   objective, scope, constraints, timeline, stakeholders, budget, success criteria).
2. `python3 -m planexe_skill create runs/<name> --prompt-file <file>`
3. `python3 -m planexe_skill run runs/<name>` (run in background; it prints progress lines with an ETA,
   and mirrors them to `runs/<name>/.planexe_skill/progress.json`). The child `claude` process needs
   keychain access, so run it outside any sandbox.
4. On failure the runner prints the failing stage, the error, the log path and a retry command.
5. The result is `runs/<name>/report.html` (and `report.md`).

When editing skills: a skill must only read files listed in its SKILL.md `inputs` and write files
listed in `outputs` (the runner enforces this). Run `python3 -m unittest discover -s tests -t .`.
