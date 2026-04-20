#!/usr/bin/env python3
"""Bump the `_version` field in a template's cookiecutter.json and prepend a changelog entry.

Usage:
    uv run tools/bump_version.py <template> {major|minor|patch} "note1" ["note2" ...]

Example:
    uv run tools/bump_version.py python/fastapi minor "add pytest-asyncio dev dep"
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def bump(version: str, segment: str) -> str:
    if not SEMVER_RE.match(version):
        raise SystemExit(
            f"error: '{version}' is not strict MAJOR.MINOR.PATCH (no pre-release suffixes allowed)"
        )
    major, minor, patch = (int(p) for p in version.split("."))
    if segment == "major":
        return f"{major + 1}.0.0"
    if segment == "minor":
        return f"{major}.{minor + 1}.0"
    if segment == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"error: segment must be major|minor|patch, got '{segment}'")


def _prepend_changelog(changelog: Path, version: str, notes: list[str]) -> None:
    today = date.today().isoformat()
    entry = f"## [{version}] - {today}\n" + "\n".join(f"- {n}" for n in notes) + "\n\n"
    text = changelog.read_text()
    # Insert entry before the first existing `## [` header, or append at end.
    header_match = re.search(r"^## \[", text, flags=re.MULTILINE)
    if header_match:
        idx = header_match.start()
        changelog.write_text(text[:idx] + entry + text[idx:])
    else:
        changelog.write_text(text.rstrip() + "\n\n" + entry)


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    template, segment, *notes = sys.argv[1:]
    cc = ROOT / template / "cookiecutter.json"
    if not cc.is_file():
        raise SystemExit(f"error: cookiecutter.json not found at {cc}")
    changelog = ROOT / template / "CHANGELOG.md"
    if not changelog.is_file():
        raise SystemExit(f"error: CHANGELOG.md not found at {changelog}")

    text = cc.read_text()
    current = json.loads(text).get("_version")
    if not current:
        raise SystemExit(f"error: {cc} is missing _version")

    new = bump(current, segment)
    pattern = re.compile(r'("_version"\s*:\s*")' + re.escape(current) + r'(")')
    text_new, n = pattern.subn(r"\g<1>" + new + r"\g<2>", text, count=1)
    if n != 1:
        raise SystemExit(f"error: could not locate _version line in {cc}")
    cc.write_text(text_new)
    _prepend_changelog(changelog, new, notes)
    print(f"{template}: {current} -> {new} (+CHANGELOG)")


if __name__ == "__main__":
    main()
