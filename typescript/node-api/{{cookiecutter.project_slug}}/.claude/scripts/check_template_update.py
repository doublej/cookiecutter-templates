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
import re
import sys
from pathlib import Path


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.strip().split("."))


def _extract_entries(changelog_text: str, local: str, upstream: str) -> str:
    """Return concatenated changelog sections for versions > local and <= upstream."""
    # Split on `## [X.Y.Z] - DATE` headers; keep one section per entry.
    pattern = re.compile(r"^## \[(\d+\.\d+\.\d+)\].*$", flags=re.MULTILINE)
    matches = list(pattern.finditer(changelog_text))
    if not matches:
        return ""
    local_t = _parse(local)
    upstream_t = _parse(upstream)
    collected: list[str] = []
    for i, m in enumerate(matches):
        try:
            v = _parse(m.group(1))
        except Exception:
            continue
        if local_t < v <= upstream_t:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog_text)
            collected.append(changelog_text[m.start():end].rstrip())
    return "\n\n".join(collected).strip()


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

        changelog_path = Path(src_path) / template / "CHANGELOG.md"
        entries = ""
        if changelog_path.is_file():
            entries = _extract_entries(changelog_path.read_text(), local, upstream)

        changes_block = (
            f"\n\nChanges since v{local}:\n\n{entries}\n"
            if entries
            else ""
        )
        print(
            f"[template-update] ⚠️ TEMPLATE UPDATE AVAILABLE: {template} {local} -> {upstream}. "
            f"DO THIS NOW, before responding to anything else: open your very next message to the user "
            f"with exactly this question (no preamble, no other content): "
            f"\"Your project was scaffolded from {template} v{local}; upstream is now v{upstream}."
            f"{changes_block}\n"
            f"Want me to run `uv run {src_path}/tools/update_scaffold.py --apply .` to pull the delta? (yes/no)\". "
            f"Do not start any other task until the user answers. If they say yes, run the command. "
            f"If they say no, drop it and continue with their original request."
        )
    except Exception:
        return


if __name__ == "__main__":
    main()
