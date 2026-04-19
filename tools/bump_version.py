#!/usr/bin/env python3
"""Bump the `_version` field in a template's cookiecutter.json.

Usage:
    uv run tools/bump_version.py <template> {major|minor|patch}

Example:
    uv run tools/bump_version.py python/fastapi minor   # 1.0.0 -> 1.1.0
"""
from __future__ import annotations

import json
import re
import sys
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


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    template, segment = sys.argv[1], sys.argv[2]
    cc = ROOT / template / "cookiecutter.json"
    if not cc.is_file():
        raise SystemExit(f"error: cookiecutter.json not found at {cc}")

    text = cc.read_text()
    current = json.loads(text).get("_version")
    if not current:
        raise SystemExit(f"error: {cc} is missing _version")

    new = bump(current, segment)
    # In-place edit preserves the file's existing indentation and key order.
    pattern = re.compile(r'("_version"\s*:\s*")' + re.escape(current) + r'(")')
    text_new, n = pattern.subn(r"\g<1>" + new + r"\g<2>", text, count=1)
    if n != 1:
        raise SystemExit(f"error: could not locate _version line in {cc}")
    cc.write_text(text_new)
    print(f"{template}: {current} -> {new}")


if __name__ == "__main__":
    main()
