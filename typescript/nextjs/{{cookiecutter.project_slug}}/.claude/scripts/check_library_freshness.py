#!/usr/bin/env python3
"""SessionStart hook: prompt agent to audit external library freshness.

Detects dependency manifests in the project root and prints a single reminder
block to stdout so Claude Code surfaces it as additional session context. Any
failure is silent (exit 0) so the hook never blocks a session. Snoozeable for
N days via the companion `snooze_library_check.py` script.

Opt-out:
  - env NO_LIBRARY_CHECK=1
  - sentinel file .claude/no-library-check
  - snooze state file .claude/.library-check-snooze.json (auto-managed)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

MANIFESTS = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "Package.swift",
    "Podfile",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
)


def _detect_manifests(root: Path) -> list[str]:
    found = [m for m in MANIFESTS if (root / m).is_file()]
    found.extend(sorted(p.name for p in root.glob("requirements*.txt")))
    return found


def main() -> None:
    try:
        if os.environ.get("NO_LIBRARY_CHECK"):
            return

        root = Path.cwd()
        if (root / ".claude" / "no-library-check").is_file():
            return

        snooze_path = root / ".claude" / ".library-check-snooze.json"
        if snooze_path.is_file():
            try:
                data = json.loads(snooze_path.read_text())
                until = datetime.fromisoformat(data["until"])
                if until > datetime.now(timezone.utc):
                    return
            except Exception:
                pass

        manifests = _detect_manifests(root)
        if not manifests:
            return

        print(
            f"[library-check] Audit external dependencies ({', '.join(manifests)}):\n"
            f"  1. Enumerate third-party deps from each manifest\n"
            f"  2. Compare pinned/installed versions vs latest upstream releases\n"
            f"  3. Skim release notes + security advisories for each outdated dep\n"
            f"  4. Flag unmaintained libraries / known CVEs / breaking-change notices\n"
            f"When done: python3 .claude/scripts/snooze_library_check.py [--days 14]"
        )
    except Exception:
        return


if __name__ == "__main__":
    main()
