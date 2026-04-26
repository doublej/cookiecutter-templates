#!/usr/bin/env python3
"""Offline test for .claude/scripts/check_template_update.py.

Builds a fake rendered project + fake upstream template in a tempdir, runs the
check script, and asserts stderr contains `[template-update]`. Then bumps the
local version to match upstream and re-runs, asserting silence. Finally
confirms the opt-out env var and sentinel file suppress the notice.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _fake_upstream(root: Path, template: str, version: str) -> Path:
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "tools" / "sync_manifest.json").write_text("{}\n")
    tmpl_dir = root / template
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "cookiecutter.json").write_text(json.dumps({"_version": version}) + "\n")
    return root


def _fake_project(root: Path, template: str, local_version: str, source_path: Path) -> Path:
    project = root / "proj"
    script_dst = project / ".claude" / "scripts"
    script_dst.mkdir(parents=True, exist_ok=True)
    src_dir = ROOT / "python/fastapi/{{cookiecutter.project_slug}}/.claude/scripts"
    shutil.copy(src_dir / "check_template_update.py", script_dst / "check_template_update.py")
    shutil.copy(src_dir / "_diag.py", script_dst / "_diag.py")
    (project / ".template-meta.json").write_text(json.dumps({
        "template": template,
        "template_version": local_version,
        "template_source": {"type": "local", "path": str(source_path)},
        "context": {},
    }) + "\n")
    return project


def _diag_records(upstream_root: Path, template: str) -> list[dict]:
    diag_dir = upstream_root / "_diagnostics" / template
    if not diag_dir.is_dir():
        return []
    records = []
    for path in sorted(diag_dir.glob("*.jsonl")):
        for raw in path.read_text().splitlines():
            raw = raw.strip()
            if raw:
                records.append(json.loads(raw))
    return records


def _run(project: Path, env_extra: dict | None = None):
    import os
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, ".claude/scripts/check_template_update.py"],
        cwd=project, capture_output=True, text=True, env=env,
    )


def main() -> None:
    failures: list[str] = []
    template = "python/fastapi"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        upstream = _fake_upstream(tmp_path / "upstream", template, "1.1.0")
        project = _fake_project(tmp_path, template, "1.0.0", upstream)

        # 1. Upstream > local -> notice.
        r = _run(project)
        if "[template-update]" not in r.stdout:
            failures.append(f"expected [template-update] in stdout, got: {r.stdout!r}")
        if r.returncode != 0:
            failures.append(f"expected exit 0, got {r.returncode}")

        # 2. Bump local to match -> silent.
        meta_path = project / ".template-meta.json"
        meta = json.loads(meta_path.read_text())
        meta["template_version"] = "1.1.0"
        meta_path.write_text(json.dumps(meta) + "\n")
        r = _run(project)
        if "[template-update]" in r.stdout:
            failures.append(f"expected silent when versions match, got: {r.stdout!r}")

        # 3. Upstream advances again, then env opt-out silences it.
        meta["template_version"] = "1.0.0"
        meta_path.write_text(json.dumps(meta) + "\n")
        r = _run(project, {"NO_TEMPLATE_UPDATE_CHECK": "1"})
        if "[template-update]" in r.stdout:
            failures.append(f"expected silent with env opt-out, got: {r.stdout!r}")

        # 4. Sentinel file silences it.
        (project / ".claude" / "no-template-update-check").touch()
        r = _run(project)
        if "[template-update]" in r.stdout:
            failures.append(f"expected silent with sentinel file, got: {r.stdout!r}")
        (project / ".claude" / "no-template-update-check").unlink()

        # 5. Missing meta -> silent.
        meta_path.unlink()
        r = _run(project)
        if "[template-update]" in r.stdout:
            failures.append(f"expected silent without meta, got: {r.stdout!r}")

        # 6. Diagnostic records: each prior run that had a meta should have logged.
        recs = _diag_records(upstream, template)
        statuses = [r["status"] for r in recs]
        # runs 1 (ok), 2 (noop up-to-date), 3 (noop env-opt-out is suppressed pre-meta? no — it
        # is suppressed before reading meta, so opt-out short-circuits before _diag could read meta.
        # Diag respects opt-out env separately (NO_TEMPLATE_DIAG); NO_TEMPLATE_UPDATE_CHECK still
        # logs a noop=env-opt-out before returning).
        if "ok" not in statuses:
            failures.append(f"expected at least one ok diag record, got statuses={statuses}")
        if statuses.count("noop") < 2:
            failures.append(f"expected >=2 noop diag records, got statuses={statuses}")
        for rec in recs:
            for key in ("ts", "template", "hook", "status", "duration_ms", "project_path"):
                if key not in rec:
                    failures.append(f"diag record missing {key}: {rec}")
                    break

        # 7. NO_TEMPLATE_DIAG silences phone-home even when the hook itself runs.
        meta_path.write_text(json.dumps({
            "template": template,
            "template_version": "1.0.0",
            "template_source": {"type": "local", "path": str(upstream)},
            "context": {},
        }) + "\n")
        before = len(_diag_records(upstream, template))
        r = _run(project, {"NO_TEMPLATE_DIAG": "1"})
        after = len(_diag_records(upstream, template))
        if after != before:
            failures.append(f"NO_TEMPLATE_DIAG should suppress writes, before={before} after={after}")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
