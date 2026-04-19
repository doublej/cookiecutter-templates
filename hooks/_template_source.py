"""Resolve source-repo info for a rendered cookiecutter template.

Used by every template's `post_gen_project.py` to populate the
`template_source` block in `.template-meta.json`. Best-effort: on any
failure, returns a shape with `type: "unknown"` and no crashes.

The function is intentionally dependency-free (stdlib only) so it can be
inlined or dynamically loaded from inside cookiecutter's hook-exec
sandbox.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _find_repo_root(template_path: Path) -> Path | None:
    for p in [template_path, *template_path.parents]:
        if (p / "tools" / "sync_manifest.json").is_file():
            return p
    return None


def _git(repo: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    return out or None


def resolve(template_path_str: str) -> dict:
    """Return a `template_source` dict for `.template-meta.json`."""
    try:
        template_path = Path(template_path_str).resolve()
    except Exception:
        return {"type": "unknown"}

    repo_root = _find_repo_root(template_path)
    if repo_root is None:
        return {"type": "unknown", "path": str(template_path)}

    remote = _git(repo_root, "config", "--get", "remote.origin.url")
    sha = _git(repo_root, "rev-parse", "HEAD")
    return {
        "type": "local",
        "path": str(repo_root),
        "git_remote": remote,
        "git_sha": sha,
    }
