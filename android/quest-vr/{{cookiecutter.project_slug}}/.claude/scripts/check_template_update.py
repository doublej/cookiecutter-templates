#!/usr/bin/env python3
"""SessionStart hook: flag when the upstream cookiecutter template has advanced.

Reads .template-meta.json in the project root, compares its template_version
against the upstream cookiecutter.json _version, and prints a single line to
stdout so Claude Code surfaces it as additional session context. Any failure
is silent (exit 0) so the hook never blocks a session.

Opt-out:
  - env NO_TEMPLATE_UPDATE_CHECK=1
  - sentinel file .claude/no-template-update-check
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.strip().split("."))


def main() -> None:
    try:
        if os.environ.get("NO_TEMPLATE_UPDATE_CHECK"):
            return

        root = Path.cwd()
        if (root / ".claude" / "no-template-update-check").is_file():
            return

        meta_path = root / ".template-meta.json"
        if not meta_path.is_file():
            return

        meta = json.loads(meta_path.read_text())
        local = meta.get("template_version")
        template = meta.get("template")
        source = meta.get("template_source") or {}
        src_path = source.get("path")
        if not (local and template and src_path):
            return

        upstream_cc = Path(src_path) / template / "cookiecutter.json"
        if not upstream_cc.is_file():
            return

        upstream = json.loads(upstream_cc.read_text()).get("_version")
        if not upstream:
            return

        if _parse(upstream) <= _parse(local):
            return

        print(
            f"[template-update] {template} {local} -> {upstream} available. "
            f"Ask the user if they want to run: "
            f"uv run {src_path}/tools/update_scaffold.py --apply ."
        )
    except Exception:
        return


if __name__ == "__main__":
    main()
