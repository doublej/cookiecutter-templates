#!/usr/bin/env python3
"""Local test for tools/update_projects.py.

Renders the released python/cli into a temp git repo and runs the batch update against it.
Needs the cookiecutter CLI and full git history (released_template reads the release commit),
so it is not in CI, which checks out shallow.

Usage:
    python3 tools/test_update_projects.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_projects as up  # noqa: E402
import update_scaffold as us  # noqa: E402

TOOL = ".claude/scripts/_diag.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def head_files(repo: Path) -> set[str]:
    return set(git(repo, "show", "--name-only", "--format=", "HEAD").split())


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        version, template_dir = us.released_template("python/cli", tmp / "released")
        project = us.render_template(template_dir, {}, tmp / "project")
        meta_path = project / ".template-meta.json"
        meta = json.loads(meta_path.read_text())
        meta["template_version"] = "0.0.1"
        meta["template_source"] = {"type": "local", "path": str(us.TEMPLATES_ROOT)}
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        git(project, "init", "-q")
        commit_all(project, "scaffold")
        pristine_tool = (project / TOOL).read_text()
        pristine_justfile = (project / "Justfile").read_text()

        def run() -> str:
            return up.update_project(project, {}, tmp, apply=True)

        (project / TOOL).write_text(pristine_tool + "# local edit\n")
        assert run().startswith("SKIP"), "an uncommitted edit in a tooling file blocks the project"
        assert (project / TOOL).read_text().endswith("# local edit\n")

        (project / "Justfile").write_text(pristine_justfile + "\n# local recipe\n")
        commit_all(project, "local edits")
        (project / "notes.txt").write_text("unrelated\n")
        git(project, "add", "notes.txt")
        assert run().startswith("APPLIED")
        assert (project / TOOL).read_text() == pristine_tool
        assert (project / "Justfile").read_text().endswith("# local recipe\n"), "seeds are never written"
        assert head_files(project) == {TOOL}
        assert json.loads(meta_path.read_text())["template_version"] == "0.0.1", "a pending seed keeps the version"
        assert git(project, "diff", "--cached", "--name-only").split() == ["notes.txt"]

        (project / "Justfile").write_text(pristine_justfile)
        git(project, "commit", "-q", "-m", "drop local recipe", "--", "Justfile")
        assert run().startswith("APPLIED")
        assert json.loads(meta_path.read_text())["template_version"] == version
        assert head_files(project) == {".template-meta.json"}
        assert git(project, "diff", "--cached", "--name-only").split() == ["notes.txt"]

        assert run() == "skip:up to date"
    print("test_update_projects: ok")


if __name__ == "__main__":
    main()
