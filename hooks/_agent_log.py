"""Bootstrap the shared agent journal in a rendered project.

Canonical copy of the `bootstrap_agent_log()` helper inlined in every
template's `post_gen_project.py` (cookiecutter's hook-exec sandbox can't
import siblings, so templates inline it — same pattern as
`_template_source.py`). Post-gen cwd is the generated project directory,
which is exactly where `atlas agent-log init` should run.

Best-effort: if `atlas` is not on PATH or the call fails, print a hint and
return. Never raises — scaffolding must not fail on this.
"""
from __future__ import annotations

import shutil
import subprocess

SKIP_HINT = "  skipped agent-log bootstrap — run 'atlas agent-log init' later"


def bootstrap_agent_log() -> None:
    """Seed the journal: ./agent-log shim + CLAUDE.md policy + db warm-up."""
    if not shutil.which("atlas"):
        print(SKIP_HINT)
        return
    try:
        subprocess.run(["atlas", "agent-log", "init"], timeout=15, check=True)
    except Exception:
        print(SKIP_HINT)
