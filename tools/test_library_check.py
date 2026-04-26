#!/usr/bin/env python3
"""Offline test for the library-check SessionStart hook + snooze script.

Builds a fake rendered project in a tempdir, exercises the hook through every
opt-out path (manifest absence, env var, sentinel file, snooze active, snooze
expired), then exercises the snooze script (default + --days override + invalid
input). No network calls.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "python/fastapi/{{cookiecutter.project_slug}}/.claude/scripts"


def _make_project(root: Path, with_manifest: bool = True) -> Path:
    project = root / "proj"
    scripts = project / ".claude" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC_DIR / "check_library_freshness.py", scripts)
    shutil.copy(SRC_DIR / "snooze_library_check.py", scripts)
    if with_manifest:
        (project / "pyproject.toml").write_text("[project]\nname='x'\n")
    return project


def _run_check(project: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, ".claude/scripts/check_library_freshness.py"],
        cwd=project, capture_output=True, text=True, env=env,
    )


def _run_snooze(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, ".claude/scripts/snooze_library_check.py", *args],
        cwd=project, capture_output=True, text=True,
    )


def main() -> None:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. Manifest present + no snooze -> reminder.
        project = _make_project(tmp_path / "case1")
        r = _run_check(project)
        if "[library-check]" not in r.stdout:
            failures.append(f"1: expected reminder, got: {r.stdout!r}")
        if r.returncode != 0:
            failures.append(f"1: expected exit 0, got {r.returncode}")

        # 2. Snooze script writes valid JSON + correct offset.
        r = _run_snooze(project, "--days", "14")
        if "[library-check] Snoozed until" not in r.stdout:
            failures.append(f"2: snooze output missing: {r.stdout!r}")
        snooze_path = project / ".claude" / ".library-check-snooze.json"
        if not snooze_path.is_file():
            failures.append("2: snooze state file not written")
        else:
            data = json.loads(snooze_path.read_text())
            until = datetime.fromisoformat(data["until"])
            expected = datetime.now(timezone.utc) + timedelta(days=14)
            delta = abs((until - expected).total_seconds())
            if delta > 60:
                failures.append(f"2: snooze offset wrong, delta={delta}s")
            if data.get("days") != 14:
                failures.append(f"2: days field wrong: {data.get('days')!r}")

        # 3. Snooze active -> silent.
        r = _run_check(project)
        if "[library-check]" in r.stdout:
            failures.append(f"3: expected silent under snooze, got: {r.stdout!r}")

        # 4. Expire snooze -> reminder again.
        data = json.loads(snooze_path.read_text())
        data["until"] = "2020-01-01T00:00:00+00:00"
        snooze_path.write_text(json.dumps(data))
        r = _run_check(project)
        if "[library-check]" not in r.stdout:
            failures.append(f"4: expected reminder after expiry, got: {r.stdout!r}")

        # 5. Env opt-out silences it.
        r = _run_check(project, {"NO_LIBRARY_CHECK": "1"})
        if "[library-check]" in r.stdout:
            failures.append(f"5: expected silent with env opt-out, got: {r.stdout!r}")

        # 6. Sentinel file silences it.
        sentinel = project / ".claude" / "no-library-check"
        sentinel.touch()
        r = _run_check(project)
        if "[library-check]" in r.stdout:
            failures.append(f"6: expected silent with sentinel, got: {r.stdout!r}")
        sentinel.unlink()

        # 7. No manifest -> silent.
        bare = _make_project(tmp_path / "case7", with_manifest=False)
        r = _run_check(bare)
        if "[library-check]" in r.stdout:
            failures.append(f"7: expected silent without manifest, got: {r.stdout!r}")

        # 8. Snooze --days override.
        bare2 = _make_project(tmp_path / "case8")
        r = _run_snooze(bare2, "--days", "30")
        data = json.loads((bare2 / ".claude" / ".library-check-snooze.json").read_text())
        if data.get("days") != 30:
            failures.append(f"8: --days 30 not honored: {data.get('days')!r}")

        # 9. Snooze rejects invalid --days (out of range).
        bare3 = _make_project(tmp_path / "case9")
        r = _run_snooze(bare3, "--days", "0")
        if (bare3 / ".claude" / ".library-check-snooze.json").is_file():
            failures.append("9: snooze accepted --days 0 (should reject)")
        r = _run_snooze(bare3, "--days", "999")
        if (bare3 / ".claude" / ".library-check-snooze.json").is_file():
            failures.append("9: snooze accepted --days 999 (should reject)")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
