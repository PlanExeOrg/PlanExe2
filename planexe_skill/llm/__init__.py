from planexe_skill.llm.base import Backend, LLMError, LLMResult


def get_backend(name: str, **kwargs) -> Backend:
    if name == "claude":
        from planexe_skill.llm.claude_cli import ClaudeCLIBackend
        return ClaudeCLIBackend(**kwargs)
    if name == "fake":
        from planexe_skill.llm.fake import FakeBackend
        return FakeBackend()
    raise ValueError(f"unknown backend '{name}'. Available: claude, fake (codex: not implemented yet)")


__all__ = ["Backend", "LLMError", "LLMResult", "get_backend"]
