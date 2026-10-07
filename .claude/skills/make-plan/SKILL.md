---
name: make-plan
description: Turn a user's planning idea into a strong PlanExe2 prompt through a short interview, check it, confirm with the user, then launch the full plan-generation DAG. Use whenever the user wants a plan made ("make a plan for ...", "plan my restaurant", "generate a PlanExe report"), even if their idea is a one-liner.
---

# Make a plan with PlanExe2

A full plan costs about 200 LLM calls and roughly an hour on the user's Claude subscription. A vague
prompt ("make me a restaurant") produces a generic plan full of invented details, so first help the user
get to a concrete prompt, and launch only after they explicitly say go.

## 1. Understand the idea

Read what the user gave you. Note which of these the plan will need and the user hasn't stated:
objective (concrete outcome and why), location, budget (amount + currency) or resources, timeline
(duration, deadlines, start date), scale (size/capacity/volume), stakeholders, constraints (rules,
non-negotiables, things to avoid), success criteria (and what would count as failure).

## 2. Ask, briefly

Ask one round of questions about the missing items that matter most, at most 5, each with 2-4 concrete
suggested answers so the user can just pick (use AskUserQuestion when available). Offer "you decide" as an
option where a sensible default exists. Don't interrogate: if the user wants to skip, proceed with
explicit, stated defaults. A second round is fine only if an answer opened a new, important gap.

Ask whether the plan should start today or on another date (past dates are fine, e.g. to compare with an
older plan; future dates for planning ahead). This becomes Month 0 of the plan.

## 3. Draft the prompt

Write 300-800 words of flowing prose (not bullet lists, no markdown headings) that weaves in the
objective, scope, location, budget, timeline, scale, stakeholders, constraints and success criteria.
Keep the user's own facts and wording where they gave them; label your additions as assumptions in the
prose ("assume a budget of about ...") so the plan treats them as estimates. Don't invent facts about the
user. Save it as `runs/<name>.prompt.txt` (`<name>`: short, lowercase, underscores).

## 4. Check it

```bash
python3 -m planexe_skill check-prompt --prompt-file runs/<name>.prompt.txt
```

One LLM call. It screens the prompt the way the pipeline will, rates each dimension
present/partial/missing, says whether it is ready (exit code 0) and suggests the most useful questions.
If it is not ready, or important items are only "partial", go back to step 2 with its questions (once or
twice is usually enough).

## 5. Confirm before launching

Show the user the final prompt (or a summary plus the file path if it is long), the check result, the
plan start date, and what launching costs: about 200 LLM calls, roughly an hour, on their Claude
subscription, in the background. Then ask explicitly, e.g. with AskUserQuestion:
"Launch the full plan generation now?" with options Launch / Revise the prompt / Cancel.

Do not run step 6 without an explicit yes in this conversation.

## 6. Launch and follow

```bash
python3 -m planexe_skill create runs/<name> --prompt-file runs/<name>.prompt.txt [--start-date YYYY-MM-DD]
python3 -m planexe_skill run runs/<name>     # in the background, outside any sandbox
```

The child `claude` CLI needs keychain access, so the run must not be sandboxed. Progress lines include an
ETA; `runs/<name>/.planexe_skill/progress.json` has the same data. Check in occasionally rather than
polling constantly. On failure the runner prints the failing stage, the error, the log path and a retry
command (re-running resumes; finished stages and completed LLM calls are kept). If authentication fails,
ask the user to run `claude auth login`, then resume.

When it finishes, give the user `runs/<name>/report.html` and summarize, leading with what the user
must decide: the open decisions from "Decisions Required" (`decision_register.md`: question, options,
owner, decide-by month) and the "Choices made on your behalf" to ratify; then the Decision Dashboard
gates; what "Validation Status" says was and was not checked (web searches, consistency lint result,
arithmetic errors); any "Consistency lint FAILED" banner; and the run's time and call count.
