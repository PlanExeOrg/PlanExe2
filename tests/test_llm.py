import json
import os
import subprocess
import unittest
from unittest import mock

from planexe_skill.llm.base import LLMError
from planexe_skill.llm.claude_cli import ClaudeCLIBackend, child_env

SCHEMA = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


class FakePopen:
    """Stands in for subprocess.Popen: replays a final `result` event as a stream-json line."""
    def __init__(self, envelope: str, returncode: int = 0, stderr: str = ""):
        self._envelope = envelope
        self.returncode = returncode
        self._stderr = stderr
        self.input = None

    def __call__(self, cmd, **kwargs):
        import io
        self.cmd = cmd
        result = json.loads(self._envelope)
        result.setdefault("type", "result")
        self.stdout = io.StringIO(json.dumps(result) + "\n")
        self.stderr = io.StringIO(self._stderr)
        outer = self

        class _Stdin:
            def write(self, s):
                outer.input = s

            def close(self):
                pass
        self.stdin = _Stdin()
        return self

    def poll(self):
        return self.returncode

    def wait(self):
        return self.returncode

    def kill(self):
        pass


def fake_proc(stdout: str, returncode: int = 0, stderr: str = ""):
    return FakePopen(stdout, returncode, stderr)


def popen_sequence(*fakes):
    """side_effect for a mocked Popen: each call is served by the next FakePopen."""
    it = iter(fakes)
    return lambda cmd, **kw: next(it)(cmd, **kw)


class ClaudeCLITest(unittest.TestCase):
    def test_command_high_tier(self):
        b = ClaudeCLIBackend()
        cmd = b.build_command("SYS", SCHEMA, "high")
        self.assertIn("--json-schema", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "claude-sonnet-5-5")
        self.assertEqual(cmd[cmd.index("--effort") + 1], "high")
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertEqual(cmd[cmd.index("--system-prompt-file") + 1], "SYS")

    def test_command_low_tier_isolated_no_thinking(self):
        cmd = ClaudeCLIBackend().build_command("SYS", None, "low")
        self.assertNotIn("--effort", cmd)
        self.assertIn('"alwaysThinkingEnabled": false', cmd[cmd.index("--settings") + 1])
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "project")
        self.assertNotIn("--json-schema", cmd)

    @mock.patch("planexe_skill.llm.claude_cli.shutil.which", return_value="/bin/claude")
    @mock.patch("planexe_skill.llm.claude_cli.subprocess.Popen")
    def test_parses_structured_output(self, run, _):
        fake = fake_proc(json.dumps({
            "is_error": False, "result": '{"x":"y"}', "structured_output": {"x": "y"},
            "usage": {"input_tokens": 3, "cache_creation_input_tokens": 10, "output_tokens": 5},
            "total_cost_usd": 0.01}))
        run.side_effect = popen_sequence(fake)
        r = ClaudeCLIBackend().complete("s", "u", SCHEMA, "low")
        self.assertEqual(r.data, {"x": "y"})
        self.assertEqual(r.metadata["input_tokens"], 13)
        self.assertEqual(r.metadata["output_tokens"], 5)
        self.assertEqual(fake.input, "u")
        self.assertIn("--include-partial-messages", fake.cmd)

    @mock.patch("planexe_skill.llm.claude_cli.time.sleep")
    @mock.patch("planexe_skill.llm.claude_cli.shutil.which", return_value="/bin/claude")
    @mock.patch("planexe_skill.llm.claude_cli.subprocess.Popen")
    def test_error_message_is_readable(self, run, _which, _sleep):
        run.side_effect = popen_sequence(fake_proc(json.dumps({"is_error": True, "result": "Failed to authenticate: x"})))
        with self.assertRaises(LLMError) as cm:
            ClaudeCLIBackend(retries=0).complete("s", "u", SCHEMA, "low")
        msg = str(cm.exception)
        self.assertIn("Failed to authenticate", msg)
        self.assertIn("claude auth login", msg)
        self.assertIn("command: claude -p", msg)

    @mock.patch("planexe_skill.llm.claude_cli.time.sleep")
    @mock.patch("planexe_skill.llm.claude_cli.shutil.which", return_value="/bin/claude")
    @mock.patch("planexe_skill.llm.claude_cli.subprocess.Popen")
    def test_retries_transient(self, run, _which, sleep):
        ok = json.dumps({"is_error": False, "result": "", "structured_output": {"x": "1"}})
        run.side_effect = popen_sequence(fake_proc(json.dumps({"is_error": True, "result": "API overloaded"})), fake_proc(ok))
        r = ClaudeCLIBackend(retries=2).complete("s", "u", SCHEMA, "low")
        self.assertEqual(r.data, {"x": "1"})
        self.assertEqual(r.metadata["attempts"], 2)

    @mock.patch("planexe_skill.llm.claude_cli.time.sleep")
    @mock.patch("planexe_skill.llm.claude_cli.shutil.which", return_value="/bin/claude")
    @mock.patch("planexe_skill.llm.claude_cli.subprocess.Popen")
    def test_falls_back_to_text_json(self, run, _which, _sleep):
        exhausted = fake_proc(json.dumps({"is_error": True, "result": "structured_output_retry_exhausted"}))
        bad = fake_proc(json.dumps({"is_error": False, "result": '{"y": 1}'}))
        good = fake_proc(json.dumps({"is_error": False, "result": 'Here:\n```json\n{"x": "ok"}\n```'}))
        run.side_effect = popen_sequence(exhausted, bad, good)
        r = ClaudeCLIBackend(retries=3).complete("s", "u", SCHEMA, "low")
        self.assertEqual(r.data, {"x": "ok"})
        self.assertEqual(r.metadata["structured_mode"], "text")
        self.assertNotIn("--json-schema", bad.cmd)
        self.assertIn("missing required key", good.input)

    def test_child_env_strips_host_vars(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_X": "1", "ANTHROPIC_BASE_URL": "u", "KEEP": "k"}):
            env = child_env()
        self.assertNotIn("CLAUDE_CODE_X", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertEqual(env["KEEP"], "k")


@unittest.skipUnless(os.environ.get("PLANEXE_SKILL_LIVE") == "1", "set PLANEXE_SKILL_LIVE=1 for live test")
class ClaudeCLILiveTest(unittest.TestCase):
    def test_live_structured(self):
        r = ClaudeCLIBackend().complete("You classify plans.", "Open a bakery in Paris.", {
            "type": "object", "properties": {"purpose": {"type": "string", "enum": ["business", "personal", "other"]}},
            "required": ["purpose"], "additionalProperties": False}, "low")
        self.assertEqual(r.data["purpose"], "business")



class JsonSchemaLiteTest(unittest.TestCase):
    def test_validate(self):
        from planexe_skill.llm.jsonschema_lite import validate
        schema = {"$defs": {"I": {"type": "object", "properties": {"k": {"enum": ["a", "b"]}}, "required": ["k"]}},
                  "type": "object", "properties": {"items": {"type": "array", "items": {"$ref": "#/$defs/I"}},
                                                   "n": {"anyOf": [{"type": "integer"}, {"type": "null"}]}},
                  "required": ["items"]}
        self.assertEqual(validate({"items": [{"k": "a"}], "n": None}, schema), [])
        problems = validate({"items": [{"k": "z"}, {}], "n": "x"}, schema)
        self.assertEqual(len(problems), 3)


if __name__ == "__main__":
    unittest.main()
