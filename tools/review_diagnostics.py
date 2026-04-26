#!/usr/bin/env python3
"""Aggregate the JSONL records written by deployed-template hooks.

Each hook in a generated project's `.claude/scripts/_diag.py` appends a line to
`<repo>/_diagnostics/<template>/<YYYY-MM>.jsonl`. This script summarises that
corpus so we can spot silent breakage across the fleet.

Usage:
    uv run tools/review_diagnostics.py
    uv run tools/review_diagnostics.py --since 7d
    uv run tools/review_diagnostics.py --errors-only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAG_DIR = ROOT / "_diagnostics"

_SINCE_RE = re.compile(r"^(\d+)([hdwm])$")
_UNIT_TO_DELTA = {
    "h": lambda n: timedelta(hours=n),
    "d": lambda n: timedelta(days=n),
    "w": lambda n: timedelta(weeks=n),
    "m": lambda n: timedelta(days=30 * n),
}


def parse_since(spec: str | None) -> datetime | None:
    if not spec:
        return None
    m = _SINCE_RE.match(spec)
    if not m:
        raise SystemExit(f"--since must look like 7d / 24h / 2w / 1m, got {spec!r}")
    n, unit = int(m.group(1)), m.group(2)
    return datetime.now(timezone.utc) - _UNIT_TO_DELTA[unit](n)


def iter_records(since: datetime | None):
    if not DIAG_DIR.is_dir():
        return
    for path in sorted(DIAG_DIR.rglob("*.jsonl")):
        for raw in path.read_text(errors="replace").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if since:
                ts = rec.get("ts")
                if not ts:
                    continue
                try:
                    when = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                if when < since:
                    continue
            yield rec


def summarise(records, errors_only: bool) -> str:
    by_key: dict[tuple[str, str, str], dict] = defaultdict(lambda: {
        "count": 0,
        "ok": 0,
        "noop": 0,
        "error": 0,
        "projects": set(),
        "last_ts": "",
        "errors": defaultdict(int),
        "noop_reasons": defaultdict(int),
    })
    for rec in records:
        key = (rec.get("template", "?"), rec.get("hook", "?"), rec.get("template_version", "?"))
        bucket = by_key[key]
        bucket["count"] += 1
        status = rec.get("status", "?")
        if status in bucket:
            bucket[status] += 1
        bucket["projects"].add(rec.get("project_path", "?"))
        ts = rec.get("ts", "")
        if ts > bucket["last_ts"]:
            bucket["last_ts"] = ts
        if status == "error":
            bucket["errors"][rec.get("error", "?")] += 1
        elif status == "noop":
            reason = (rec.get("meta") or {}).get("reason", "?")
            bucket["noop_reasons"][reason] += 1

    if not by_key:
        return "_diagnostics is empty (no records yet)."

    lines: list[str] = ["# Diagnostic review", ""]
    totals = {"count": 0, "ok": 0, "noop": 0, "error": 0}
    for bucket in by_key.values():
        for k in totals:
            totals[k] += bucket[k]
    err_rate = (totals["error"] / totals["count"] * 100) if totals["count"] else 0.0
    lines.append(
        f"**Totals:** {totals['count']} records · {totals['ok']} ok · "
        f"{totals['noop']} noop · {totals['error']} error ({err_rate:.1f}%)"
    )
    lines.append("")

    for (template, hook, version), b in sorted(by_key.items()):
        if errors_only and b["error"] == 0:
            continue
        rate = (b["error"] / b["count"] * 100) if b["count"] else 0.0
        flag = " ⚠️" if rate > 5 else ""
        lines.append(f"## {template} :: {hook} (v{version}){flag}")
        lines.append(
            f"- {b['count']} runs · {b['ok']} ok · {b['noop']} noop · "
            f"{b['error']} error ({rate:.1f}%) · "
            f"{len(b['projects'])} project(s) · last {b['last_ts']}"
        )
        if b["errors"]:
            lines.append("- top errors:")
            for msg, n in sorted(b["errors"].items(), key=lambda kv: -kv[1])[:5]:
                lines.append(f"  - {n}× `{msg.splitlines()[0][:160]}`")
        if b["noop_reasons"] and not errors_only:
            top = ", ".join(
                f"{r}={n}" for r, n in sorted(b["noop_reasons"].items(), key=lambda kv: -kv[1])[:5]
            )
            lines.append(f"- noop reasons: {top}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="filter to records newer than e.g. 24h, 7d, 2w, 1m")
    parser.add_argument("--errors-only", action="store_true", help="hide buckets with zero errors")
    args = parser.parse_args()

    since = parse_since(args.since)
    sys.stdout.write(summarise(iter_records(since), args.errors_only))


if __name__ == "__main__":
    main()
