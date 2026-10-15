#!/usr/bin/env python3
"""Local test for the 3-way merge in tools/update_scaffold.py.

Renders python/cli at an older released version, customizes it, then updates it to the current
release. Needs the cookiecutter CLI and full git history, so it is not in CI.

Usage:
    python3 tools/test_update_scaffold.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_scaffold as us  # noqa: E402

TEMPLATE, OLD = "python/cli", "2.1.0"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        project = us.render_template(us.base_template(TEMPLATE, OLD, tmp / "old"), {}, tmp / "project")
        meta_path = project / ".template-meta.json"
        meta = json.loads(meta_path.read_text())
        meta["template_version"] = OLD
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        _, new_dir = us.released_template(TEMPLATE, tmp / "new")
        new = us.render_template(new_dir, {}, tmp / "rendered")

        justfile = project / "Justfile"
        justfile.write_text(justfile.read_text() + "\n# local recipe\n")
        claude_md = project / "CLAUDE.md"
        old_lines, new_lines = claude_md.read_text().splitlines(), (new / "CLAUDE.md").read_text().splitlines()
        clash = next(i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b)
        old_lines[clash] = "local rewrite of a line the template also changed"
        claude_md.write_text("\n".join(old_lines) + "\n")
        (project / ".quality.json").unlink()  # changed upstream, deleted locally -> stays deleted
        untouched = sorted(p.relative_to(project) for p in project.rglob("*.py"))

        out = subprocess.run([sys.executable, str(Path(us.__file__)), "--apply", str(project)],
                             capture_output=True, text=True, check=True).stdout
        assert not list(project.rglob("*.upstream")), out

        assert justfile.read_text().endswith("\n# local recipe\n"), "local edit kept"
        assert "i18n-check" in justfile.read_text(), "upstream recipe merged in"
        assert "||||||| template (old)" in claude_md.read_text() and "[conflict] CLAUDE.md" in out, out
        assert not (project / ".quality.json").exists(), "a local deletion is respected"
        for rel in (".claude/agents/verify-runner.md", "src/my_cli_tool/i18n.py"):
            assert (project / rel).read_bytes() == (new / rel).read_bytes(), f"new {rel} is added"
        assert all((project / rel).exists() for rel in untouched)
        assert json.loads(meta_path.read_text())["template_version"] != OLD
    print("test_update_scaffold: ok")


if __name__ == "__main__":
    main()
