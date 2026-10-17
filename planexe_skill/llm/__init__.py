from planexe_skill.llm.base import Backend, BackendConfigError, LLMError, LLMResult


def get_backend(name: str, **kwargs) -> Backend:
    if name == "claude":
        from planexe_skill.llm.claude_cli import ClaudeCLIBackend
        return ClaudeCLIBackend(**kwargs)
    if name == "opencode":
        from planexe_skill.llm.opencode_cli import OpenCodeCLIBackend
        return OpenCodeCLIBackend(**kwargs)
    if name == "fake":
        from planexe_skill.llm.fake import FakeBackend
        return FakeBackend()
    raise ValueError(f"unknown backend '{name}'. Available: claude, opencode, fake")


__all__ = ["Backend", "BackendConfigError", "LLMError", "LLMResult", "get_backend"]
