"""Helpers for building throwaway skill trees in tests."""
from pathlib import Path
import textwrap


def make_skill(root: Path, name: str, inputs: list[str], outputs: list[str], run_py: str | None = None,
               tier: str = "low", est_llm_calls: int = 0) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(textwrap.dedent(f"""\
        ---
        name: {name}
        description: test skill {name}
        inputs: [{", ".join(inputs)}]
        outputs: [{", ".join(outputs)}]
        tier: {tier}
        est_llm_calls: {est_llm_calls}
        ---
        Body of {name}.
        """))
    if run_py is None:
        # Default: concatenate inputs into each output.
        run_py = textwrap.dedent("""\
            def run(ctx):
                parts = [ctx.read_text(i) for i in ctx.skill.inputs]
                for o in ctx.skill.outputs:
                    ctx.write_text(o, ctx.skill.name + ":" + "|".join(parts))
            """)
    (d / "run.py").write_text(run_py)
    return d
