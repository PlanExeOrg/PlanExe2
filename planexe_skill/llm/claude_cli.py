"""Backend that runs each LLM call through the headless Claude Code CLI (`claude -p`).

Uses the user's Claude subscription, no API key or SDK needed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time

from planexe_skill.llm.base import Backend, LLMError, LLMResult
from planexe_skill.llm.jsonschema_lite import extract_json_object, validate

# Tiers: "high" = reasoning (the early, foundational stages); "mid" = strong model, no thinking
# (later stages where Haiku isn't good enough); "low" = fast model, no thinking.
DEFAULT_MODELS = {"high": "claude-sonnet-5-5", "mid": "claude-sonnet-5-5", "low": "claude-haiku-4-5-20251001"}
DEFAULT_EFFORTS = {"high": "high", "mid": "low", "low": None}
_NO_THINKING_SETTINGS = json.dumps({"alwaysThinkingEnabled": False})

# Messages that are worth retrying after a pause.
_TRANSIENT = ("overloaded", "rate limit", "rate_limit", "529", "503", "502", "timeout", "timed out",
              "econnreset", "socket hang up", "internal server error", "api_error",
              "structured_output_retry_exhausted", "server error")


def child_env() -> dict[str, str]:
    """Environment for the child `claude` process.

    When this runner is itself started from inside Claude Code (desktop app, IDE, or a
    nested session) the parent injects CLAUDE_CODE_* / ANTHROPIC_BASE_URL variables that
    point the CLI at the host's private auth channel. A spawned CLI can't use that, so we
    strip them and let it use the user's own login (keychain / ~/.claude).
    """
    drop_exact = {"ANTHROPIC_BASE_URL", "AI_AGENT", "BAGGAGE", "CLAUDECODE"}
    return {k: v for k, v in os.environ.items()
            if k not in drop_exact and not k.startswith("CLAUDE_CODE_") and not k.startswith("CLAUDE_")}


def _neutral_cwd() -> str:
    """An empty directory, so the child picks up no project CLAUDE.md / .claude settings."""
    d = os.path.join(tempfile.gettempdir(), "planexe_skill_claude_cwd")
    os.makedirs(d, exist_ok=True)
    return d


class ClaudeCLIBackend(Backend):
    name = "claude"

    def __init__(self, models: dict[str, str] | None = None, efforts: dict[str, str | None] | None = None,
                 timeout: float = 900.0, retries: int = 3, executable: str = "claude"):
        self.models = {**DEFAULT_MODELS, **(models or {})}
        self.efforts = {**DEFAULT_EFFORTS, **(efforts or {})}
        self.timeout = timeout
        self.retries = retries
        self.executable = executable

    def model_for(self, tier: str) -> str:
        return self.models.get(tier, self.models["low"])

    def build_command(self, system_file: str, schema: dict | None, tier: str) -> list[str]:
        """`system_file` holds the system prompt (a file avoids OS argument-length limits)."""
        # Isolation: the child must behave like a plain LLM call. Without these flags it would
        # inherit the user's settings (e.g. effortLevel, plugins, SessionStart hooks that inject
        # text, MCP servers, skills) and the effort level of the user's own sessions.
        cmd = [self.executable, "-p", "--output-format", "json",
               "--model", self.model_for(tier),
               "--tools", "",
               "--no-session-persistence",
               "--setting-sources", "project",
               "--strict-mcp-config",
               "--disable-slash-commands",
               "--system-prompt-file", system_file]
        effort = self.efforts.get(tier)
        if effort:
            cmd += ["--effort", effort]
        elif "haiku" in self.model_for(tier):
            # No reasoning: switch extended thinking off (halves latency; see report.md).
            cmd += ["--settings", _NO_THINKING_SETTINGS]
        else:
            # Sonnet 5.5 rejects thinking=disabled; low effort is its fastest mode.
            cmd += ["--effort", "low"]
        if schema is not None:
            cmd += ["--json-schema", json.dumps(schema)]
        return cmd

    @staticmethod
    def describe_command(cmd: list[str]) -> str:
        """Shell-ish rendering with long arguments abbreviated (for error messages)."""
        out = []
        for a in cmd:
            if len(a) > 80:
                a = a[:60] + f"...<{len(a)} chars>"
            out.append(json.dumps(a) if (" " in a or a == "") else a)
        return " ".join(out)

    def _run_once(self, cmd: list[str], user: str) -> dict:
        env = child_env()
        if _NO_THINKING_SETTINGS in cmd:
            env["MAX_THINKING_TOKENS"] = "0"
        if shutil.which(self.executable) is None:
            raise LLMError(f"'{self.executable}' was not found on PATH. Install Claude Code "
                           f"(https://docs.claude.com/claude-code) and run 'claude auth login'.")
        try:
            proc = subprocess.run(cmd, input=user, capture_output=True, text=True,
                                  timeout=self.timeout, env=env, cwd=_neutral_cwd())
        except subprocess.TimeoutExpired:
            raise LLMError(f"claude CLI timed out after {self.timeout:.0f}s") from None
        envelope = None
        try:
            envelope = json.loads(proc.stdout) if proc.stdout.strip() else None
        except json.JSONDecodeError:
            pass
        if envelope is None:
            raise LLMError(f"claude CLI exited with code {proc.returncode} and no JSON output.\n"
                           f"stderr (tail):\n{proc.stderr[-2000:]}\nstdout (tail):\n{proc.stdout[-1000:]}")
        if envelope.get("is_error"):
            msg = envelope.get("result") or envelope.get("terminal_reason") or "unknown error"
            hint = ""
            if "authenticate" in str(msg).lower() or "oauth" in str(msg).lower():
                hint = ("\nHint: run 'claude auth login' in a terminal. If you run inside a sandbox, "
                        "the CLI may be unable to reach the macOS keychain; run without the sandbox.")
            raise LLMError(f"claude CLI reported an error: {msg}{hint}\nstderr (tail):\n{proc.stderr[-1500:]}")
        return envelope

    def complete(self, system: str, user: str, schema: dict | None = None, tier: str = "low") -> LLMResult:
        fd, system_file = tempfile.mkstemp(prefix="planexe_skill_system_", suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(system)
        try:
            return self._complete(system_file, user, schema, tier)
        finally:
            os.unlink(system_file)

    def _text_json_files(self, system_file: str, schema: dict) -> str:
        """System prompt for plain-JSON mode: the original prompt + the schema to follow."""
        with open(system_file, encoding="utf-8") as f:
            system = f.read()
        fd, path = tempfile.mkstemp(prefix="planexe_skill_system_json_", suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(system + "\n\n# Output format\nRespond with ONLY one JSON object (no prose, no markdown "
                    "fences) that conforms to this JSON schema:\n" + json.dumps(schema, indent=1))
        return path

    def _complete(self, system_file: str, user: str, schema: dict | None, tier: str) -> LLMResult:
        # Two ways to get structured output: the CLI's schema-enforced tool ("tool"), and, if that gives
        # up (structured_output_retry_exhausted, seen with long outputs), plain JSON in the reply that we
        # parse and validate ourselves ("text"), with the validation problems fed back on a retry.
        mode = "tool"
        text_system_file: str | None = None
        feedback = ""
        last_error: LLMError | None = None
        try:
            for attempt in range(self.retries + 1):
                if mode == "tool" or schema is None:
                    cmd = self.build_command(system_file, schema, tier)
                    prompt = user
                else:
                    if text_system_file is None:
                        text_system_file = self._text_json_files(system_file, schema)
                    cmd = self.build_command(text_system_file, None, tier)
                    prompt = user + feedback
                start = time.time()
                try:
                    env = self._run_once(cmd, prompt)
                except LLMError as e:
                    last_error = e
                    if schema is not None and "structured_output_retry_exhausted" in str(e):
                        mode = "text"
                        continue
                    transient = any(t in str(e).lower() for t in _TRANSIENT)
                    if attempt < self.retries and transient:
                        time.sleep(min(60, 5 * 2 ** attempt))
                        continue
                    if attempt < self.retries and "no json output" in str(e).lower():
                        time.sleep(3)
                        continue
                    break
                duration = time.time() - start
                text = env.get("result") or ""
                data = env.get("structured_output") if mode == "tool" else None
                if schema is not None and data is None:
                    try:
                        data = extract_json_object(text)
                        problems = validate(data, schema)
                    except (ValueError, json.JSONDecodeError) as e:
                        problems = [f"reply is not a JSON object: {e}"]
                    if problems:
                        last_error = LLMError("model output does not match the schema: " + "; ".join(problems[:10]))
                        mode = "text"
                        feedback = ("\n\n# Your previous reply was rejected\nFix these problems and reply with the "
                                    "complete JSON object only:\n- " + "\n- ".join(problems[:20]))
                        continue
                usage = env.get("usage") or {}
                meta = {
                    "model": self.model_for(tier),
                    "backend": self.name,
                    "duration_seconds": round(duration, 3),
                    "input_tokens": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
                                    + (usage.get("cache_creation_input_tokens") or 0),
                    "output_tokens": usage.get("output_tokens") or 0,
                    "cost_usd": env.get("total_cost_usd"),
                    "attempts": attempt + 1,
                    "structured_mode": mode if schema is not None else None,
                }
                return LLMResult(data=data, text=text, metadata=meta)
        finally:
            if text_system_file:
                os.unlink(text_system_file)
        assert last_error is not None
        raise LLMError(f"{last_error}\ncommand: {self.describe_command(cmd)}")
