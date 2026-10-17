"""Backend that runs each LLM call through the headless opencode CLI (`opencode run`).

opencode (https://opencode.ai) talks to many providers (OpenRouter, LM Studio, Ollama, ...), so this backend
lets the pipeline run on open models. Models are given as `provider/model`, as listed by `opencode models`.

opencode has no schema-enforced output, so structured output is always plain JSON in the reply, parsed and
validated here, with the validation problems fed back on a retry.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time

from planexe_skill.llm.base import Backend, BackendConfigError, LLMAuthError, LLMError, LLMResult
from planexe_skill.llm.claude_cli import ClaudeCLIBackend
from planexe_skill.llm.jsonschema_lite import extract_json_object, validate

AGENT = "planexe"

# Messages that are worth retrying after a pause.
_TRANSIENT = ("stalled", "overloaded", "rate limit", "rate_limit", "429", "529", "503", "502", "timeout",
              "timed out", "econnreset", "socket hang up", "internal server error", "server error",
              "provider returned error")
_AUTH = ("401", "unauthorized", "invalid api key", "api key", "no credentials", "free tier can only be used")


def _work_dir() -> str:
    """Neutral cwd plus the private session database: the child picks up no project AGENTS.md / opencode.json,
    and the pipeline's ~250 calls don't show up in the user's own opencode session list."""
    d = os.path.join(tempfile.gettempdir(), "planexe_skill_opencode")
    os.makedirs(os.path.join(d, "cwd"), exist_ok=True)
    return d


def child_env(config_file: str, web_search: bool) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "OPENCODE_CONFIG": config_file,
        "OPENCODE_DB": os.path.join(_work_dir(), "sessions.db"),
        # Isolation: no ~/.claude/CLAUDE.md or skills, no project config, no plugins, no update checks.
        "OPENCODE_DISABLE_CLAUDE_CODE": "1",
        "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
        "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_SHARE": "1",
    })
    if web_search:
        env["OPENCODE_ENABLE_EXA"] = "1"  # the `websearch` tool
    return env


def agent_config(system: str, web_search: bool) -> dict:
    """opencode config with one agent whose prompt is our system prompt and whose only tool is web search."""
    permission: dict[str, str] = {"*": "deny"}
    tools: dict[str, bool] = {"*": False}
    if web_search:
        permission["websearch"] = "allow"
        tools["websearch"] = True
    return {
        "$schema": "https://opencode.ai/config.json",
        "share": "disabled",
        "autoupdate": False,
        "instructions": [],
        "agent": {AGENT: {"mode": "primary", "prompt": system, "steps": 12 if web_search else 2,
                          "permission": permission, "tools": tools}},
    }


class OpenCodeCLIBackend(Backend):
    name = "opencode"
    login_hint = "Run 'opencode auth login' (or check the provider's API key)"

    def __init__(self, models: dict[str, str] | None = None, variants: dict[str, str | None] | None = None,
                 timeout: float = 600.0, retries: int = 3, executable: str = "opencode",
                 idle_timeout: float = 180.0):
        models = {k: v for k, v in (models or {}).items() if v}
        if not models:
            raise BackendConfigError("the opencode backend needs a model: give --model PROVIDER/MODEL "
                             "(see `opencode models`)")
        fallback = models.get("mid") or models.get("high") or next(iter(models.values()))
        self.models = {t: models.get(t, fallback) for t in ("high", "mid", "low")}
        self.variants = variants or {}
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        self.retries = retries
        self.executable = executable

    def model_for(self, tier: str) -> str:
        return self.models.get(tier, self.models["low"])

    def build_command(self, tier: str) -> list[str]:
        cmd = [self.executable, "run", "--format", "json", "--pure", "--agent", AGENT, "-m", self.model_for(tier)]
        variant = self.variants.get(tier)
        if variant:
            cmd += ["--variant", variant]
        return cmd

    describe_command = staticmethod(ClaudeCLIBackend.describe_command)

    def _run_once(self, cmd: list[str], user: str, env: dict[str, str]) -> dict:
        """Run one CLI call, streaming its JSON events so a stalled call is detected early.

        Returns {"text", "input_tokens", "output_tokens", "cost_usd", "web_searches"}.
        """
        if shutil.which(self.executable) is None:
            raise LLMError(f"'{self.executable}' was not found on PATH. Install opencode "
                           f"(https://opencode.ai) and configure a provider with 'opencode auth login'.")
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=env, cwd=os.path.join(_work_dir(), "cwd"))
        state: dict = {"last": time.time(), "texts": [], "input": 0, "output": 0, "cost": 0.0, "searches": 0,
                       "errors": [], "lines": []}
        stderr_chunks: list[str] = []

        def read_stdout() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                state["last"] = time.time()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    state["lines"].append(line[-500:])
                    continue
                etype = event.get("type")
                part = event.get("part") or {}
                if etype == "text":
                    state["texts"].append(part.get("text") or "")
                elif etype == "tool_use" and part.get("tool") == "websearch":
                    state["searches"] += 1
                elif etype == "step_finish":
                    tokens = part.get("tokens") or {}
                    cache = tokens.get("cache") or {}
                    state["input"] += (tokens.get("input") or 0) + (cache.get("read") or 0) + (cache.get("write") or 0)
                    state["output"] += (tokens.get("output") or 0) + (tokens.get("reasoning") or 0)
                    state["cost"] += part.get("cost") or 0.0
                elif etype == "error":
                    err = event.get("error") or {}
                    data = err.get("data") or {}
                    msg = data.get("message") or err.get("name") or json.dumps(err)[:500]
                    if data.get("statusCode"):
                        msg = f"{msg} (HTTP {data['statusCode']})"
                    state["errors"].append(msg)

        def read_stderr() -> None:
            assert proc.stderr is not None
            stderr_chunks.append(proc.stderr.read())

        readers = [threading.Thread(target=read_stdout, daemon=True), threading.Thread(target=read_stderr, daemon=True)]
        for r in readers:
            r.start()
        try:
            assert proc.stdin is not None
            proc.stdin.write(user)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        started = time.time()
        failure = None
        while proc.poll() is None:
            time.sleep(0.5)
            now = time.time()
            # opencode emits whole text parts, not token deltas, so the idle limit is longer than for claude.
            if now - state["last"] > self.idle_timeout:
                failure = f"opencode CLI stalled: no output for {self.idle_timeout:.0f}s (after {now - started:.0f}s)"
            elif now - started > self.timeout:
                failure = f"opencode CLI timed out after {self.timeout:.0f}s (output is probably too long)"
            if failure:
                proc.kill()
                break
        proc.wait()
        for r in readers:
            r.join(timeout=5)
        stderr = "".join(stderr_chunks)
        if failure:
            raise LLMError(failure)
        if state["errors"]:
            msg = "; ".join(state["errors"])
            text = f"opencode CLI reported an error: {msg}\nstderr (tail):\n{stderr[-1500:]}"
            if "free tier can only be used" in msg.lower():
                raise LLMAuthError(text + "\nHint: opencode's free models refuse custom system prompts; "
                                   "pick a model from another provider (e.g. openrouter/..., lmstudio/...).")
            if any(a in msg.lower() for a in _AUTH):
                raise LLMAuthError(text + f"\nHint: {self.login_hint}, then resume the run.")
            raise LLMError(text)
        text = "".join(state["texts"]).strip()
        if not text:
            raise LLMError(f"opencode CLI exited with code {proc.returncode} and no text output.\n"
                           f"stderr (tail):\n{stderr[-2000:]}\nstdout (tail):\n{''.join(state['lines'])[-1000:]}")
        return {"text": text, "input_tokens": state["input"], "output_tokens": state["output"],
                "cost_usd": round(state["cost"], 6), "web_searches": state["searches"]}

    def complete(self, system: str, user: str, schema: dict | None = None, tier: str = "low",
                 web_search: bool = False) -> LLMResult:
        if schema is not None:
            system = (system.rstrip() + "\n\n# Output format\nRespond with ONLY one JSON object (no prose, no "
                      "markdown fences) that conforms to this JSON schema:\n" + json.dumps(schema, indent=1))
        fd, config_file = tempfile.mkstemp(prefix="planexe_skill_opencode_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(agent_config(system, web_search), f)
        try:
            return self._complete(config_file, user, schema, tier, web_search)
        finally:
            os.unlink(config_file)

    def _complete(self, config_file: str, user: str, schema: dict | None, tier: str, web_search: bool) -> LLMResult:
        cmd = self.build_command(tier)
        env = child_env(config_file, web_search)
        feedback = ""
        slow_failures = 0
        last_error: LLMError | None = None
        for attempt in range(self.retries + 1):
            start = time.time()
            try:
                out = self._run_once(cmd, user + feedback, env)
            except LLMAuthError:
                raise
            except LLMError as e:
                last_error = e
                msg = str(e).lower()
                transient = any(t in msg for t in _TRANSIENT)
                if ("stalled" in msg or "timed out" in msg) and slow_failures >= 1:
                    transient = False  # one retry for a stall/timeout, then fail fast
                if "stalled" in msg or "timed out" in msg:
                    slow_failures += 1
                if attempt < self.retries and transient:
                    time.sleep(min(60, 5 * 2 ** attempt))
                    continue
                if attempt < self.retries and "no text output" in msg:
                    time.sleep(3)
                    continue
                break
            data = None
            if schema is not None:
                try:
                    data = extract_json_object(out["text"])
                    problems = validate(data, schema)
                except (ValueError, json.JSONDecodeError) as e:
                    problems = [f"reply is not a JSON object: {e}"]
                if problems:
                    last_error = LLMError("model output does not match the schema: " + "; ".join(problems[:10]))
                    feedback = ("\n\n# Your previous reply was rejected\nFix these problems and reply with the "
                                "complete JSON object only:\n- " + "\n- ".join(problems[:20]))
                    continue
            meta = {
                "model": self.model_for(tier),
                "backend": self.name,
                "duration_seconds": round(time.time() - start, 3),
                "input_tokens": out["input_tokens"],
                "output_tokens": out["output_tokens"],
                "cost_usd": out["cost_usd"],
                "attempts": attempt + 1,
                "structured_mode": "text" if schema is not None else None,
                "web_searches": out["web_searches"],
            }
            return LLMResult(data=data, text=out["text"], metadata=meta)
        assert last_error is not None
        raise LLMError(f"{last_error}\ncommand: {self.describe_command(cmd)}")
