#!/usr/bin/env python3
"""Offline test for the node-lib split_oversize.py PoC.

Builds fake rendered projects in a tempdir and exercises the analyzer through
every path that matters: opt-outs, missing config, nothing-to-split, a clean
proposal, --json, both placement layouts, --apply's output (barrel keeps the
public surface byte-for-byte, private symbols stay out of it), and each refusal
(cycle, dirty worktree, still-oversized part). No network calls, no bun/tsc.

Fixtures are modelled on real pre-split commits from local repos.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "typescript/node-lib/{{cookiecutter.project_slug}}/.claude/scripts/split_oversize.py"

QUALITY = {"loc": {"warn": 12, "error": 20}, "dir": {"max_files": 6}, "globs": ["src/**/*.ts"]}

# Three independent clusters: types, a parse/render cluster, a consumer class.
SPLITTABLE = """import { readFileSync } from 'node:fs'

export interface Config {
  name: string
  retries: number
}

export type Mode = 'fast' | 'safe'

const DEFAULTS: Config = { name: 'unnamed', retries: 3 }

function normalize(raw: Record<string, unknown>): Config {
  const name = typeof raw.name === 'string' ? raw.name : DEFAULTS.name
  const retries = typeof raw.retries === 'number' ? raw.retries : DEFAULTS.retries
  return { name, retries }
}

export function parseConfig(path: string): Config {
  return normalize(JSON.parse(readFileSync(path, 'utf8')) as Record<string, unknown>)
}

export function renderConfig(cfg: Config): string {
  return `${cfg.name}/${cfg.retries}`
}

export class Runner {
  constructor(private readonly cfg: Config) {}
  describe(): string {
    return renderConfig(this.cfg)
  }
}
"""

# One cluster too big for loc.error, so it gets binned — and ping <-> pong straddle the
# bin boundary, which is the only way two parts can end up importing each other.
CYCLIC = """export interface Shared {
  depth: number
}

export function ping(s: Shared): string {
  return s.depth > 0 ? pong({ depth: s.depth - 1 }) : 'done'
}

export function alpha(s: Shared): string {
  return ping(s)
}

export function beta(s: Shared): string {
  return alpha(s)
}

export function gamma(s: Shared): string {
  return beta(s)
}

export function pong(s: Shared): string {
  return s.depth > 0 ? ping({ depth: s.depth - 1 }) : 'done'
}

export function delta(s: Shared): string {
  return pong(s)
}
"""

# One oversized class — the common real-world case a mechanical split cannot fix.
GIANT_CLASS = "const TAG = 'giant'\n\nexport class Giant {\n" + "".join(
    f"  step{i}(): string {{\n    return `${{TAG}}-{i}`\n  }}\n" for i in range(12)
) + "}\n"


def _project(root: Path, name: str, files: dict[str, str], quality: dict | None = QUALITY) -> Path:
    project = root / name
    (project / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(SRC, project / ".claude" / "scripts" / "split_oversize.py")
    shutil.copy(SRC.parent / "_diag.py", project / ".claude" / "scripts" / "_diag.py")
    if quality is not None:
        (project / ".quality.json").write_text(json.dumps(quality))
    for rel, body in files.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    return project


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["NO_TEMPLATE_DIAG"] = "1"
    return subprocess.run(
        [sys.executable, ".claude/scripts/split_oversize.py", *args],
        cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, check=False)


def main() -> None:
    f: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            f.append(msg)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. Missing .quality.json -> silent noop, exit 0.
        p = _project(tmp_path, "no-config", {"src/big.ts": SPLITTABLE}, quality=None)
        r = _run(p)
        check(r.returncode == 0, f"1: exit {r.returncode}")
        check(r.stdout.strip() == "", f"1: expected silence, got {r.stdout!r}")

        # 2. Everything under the limit -> nothing to split.
        p = _project(tmp_path, "small", {"src/ok.ts": "export const a = 1\n"})
        r = _run(p)
        check("nothing to split" in r.stdout, f"2: got {r.stdout!r}")

        # 3. Opt-outs silence it even with an oversized file.
        p = _project(tmp_path, "optout", {"src/big.ts": SPLITTABLE})
        env_run = subprocess.run(
            [sys.executable, ".claude/scripts/split_oversize.py"], cwd=p, capture_output=True,
            text=True, env={**os.environ, "NO_LOC_FIX": "1", "NO_TEMPLATE_DIAG": "1"},
        )
        check(env_run.stdout.strip() == "", f"3: env opt-out leaked {env_run.stdout!r}")
        (p / ".claude" / "no-loc-fix").touch()
        r = _run(p)
        check(r.stdout.strip() == "", f"3: sentinel opt-out leaked {r.stdout!r}")

        # 4. Oversized file -> proposal, sibling layout (src/ has room).
        p = _project(tmp_path, "propose", {"src/big.ts": SPLITTABLE})
        r = _run(p)
        check("[loc-fix] src/big.ts" in r.stdout, f"4: no header in {r.stdout!r}")
        check("layout: siblings" in r.stdout, f"4: expected sibling layout, got {r.stdout!r}")
        check("blocked:" not in r.stdout, f"4: unexpected blocker in {r.stdout!r}")

        # 5. --json carries the expected keys.
        r = _run(p, "--json")
        data = json.loads(r.stdout)
        check(len(data["files"]) == 1, f"5: expected 1 file, got {data}")
        entry = data["files"][0]
        for key in ("file", "lines", "limit", "layout", "layout_reason", "groups", "barrel", "blockers"):
            check(key in entry, f"5: missing key {key}")
        check(entry["barrel"] == ["Config", "Mode", "Runner", "parseConfig", "renderConfig"],
              f"5: barrel names wrong: {entry['barrel']}")
        check(all("path" in g and "blocks" in g and "lines" in g for g in entry["groups"]),
              "5: group entries incomplete")
        check("_internal" not in entry, "5: internal state leaked into --json")

        # 6. No room in the directory -> subdirectory layout.
        packed = {"src/big.ts": SPLITTABLE}
        for i in range(5):
            packed[f"src/filler{i}.ts"] = f"export const filler{i} = {i}\n"
        p = _project(tmp_path, "packed", packed)
        r = _run(p)
        check("layout: subdirectory" in r.stdout, f"6: expected subdirectory layout, got {r.stdout!r}")
        check("src/big/" in r.stdout, f"6: parts not nested: {r.stdout!r}")

        # 7. --apply writes the parts and a barrel with exactly the original public names.
        p = _project(tmp_path, "apply", {"src/big.ts": SPLITTABLE})
        r = _run(p, "--apply", "src/big.ts")
        check("split src/big.ts" in r.stdout, f"7: apply did not report: {r.stdout!r}")
        barrel = (p / "src" / "big.ts").read_text()
        exported = set()
        for line in barrel.splitlines():
            if line.startswith("export"):
                exported.update(n.strip() for n in line.split("{")[1].split("}")[0].split(","))
        check(exported == {"Config", "Mode", "Runner", "parseConfig", "renderConfig"},
              f"7: barrel surface changed: {sorted(exported)}")
        for private in ("DEFAULTS", "normalize"):
            check(private not in barrel, f"7: private symbol {private} leaked into the barrel")
        check("export *" not in barrel, "7: barrel used a star re-export")
        parts = sorted(q.name for q in (p / "src").glob("big-*.ts"))
        check(len(parts) >= 2, f"7: expected sibling parts, got {parts}")
        bodies = "\n".join((p / "src" / q).read_text() for q in parts)
        check("'./big-" in bodies and ".js'" in bodies, "7: cross-module imports missing .js extension")
        check("export function normalize" in bodies or "function normalize" in bodies,
              "7: normalize did not survive the split")
        # Every original declaration must still exist exactly once across the parts.
        for name in ("Config", "Mode", "DEFAULTS", "normalize", "parseConfig", "renderConfig", "Runner"):
            check(bodies.count(f" {name}") + bodies.count(f"{name} ") > 0, f"7: {name} lost in the split")

        # 8. Re-running on the applied project is a clean noop (parts are under the limit).
        r = _run(p)
        check("nothing to split" in r.stdout, f"8: split output still oversized: {r.stdout!r}")

        # 9. Cyclic groups refuse to apply.
        p = _project(tmp_path, "cyclic", {"src/cyc.ts": CYCLIC})
        r = _run(p, "--apply", "src/cyc.ts")
        check("reference cycle" in r.stdout, f"9: cycle not detected: {r.stdout!r}")
        check("not applied" in r.stdout, f"9: applied despite cycle: {r.stdout!r}")
        check(not list((p / "src").glob("cyc-*.ts")), "9: wrote files despite the cycle")

        # 10. A part that would still bust loc.error refuses to apply.
        p = _project(tmp_path, "giant", {"src/giant.ts": GIANT_CLASS})
        r = _run(p, "--apply", "src/giant.ts")
        check("would still be" in r.stdout, f"10: oversized part not flagged: {r.stdout!r}")
        check("not applied" in r.stdout, f"10: applied an oversized part: {r.stdout!r}")

        # 11. Dirty worktree refuses without --force, proceeds with it.
        p = _project(tmp_path, "dirty", {"src/big.ts": SPLITTABLE})
        _git(p, "init", "-q")
        _git(p, "config", "user.email", "test@example.com")
        _git(p, "config", "user.name", "test")
        _git(p, "add", "-A")
        _git(p, "commit", "-qm", "init")
        (p / "src" / "big.ts").write_text(SPLITTABLE + "\n// edited\n")
        r = _run(p, "--apply", "src/big.ts")
        check("uncommitted changes" in r.stdout, f"11: dirty file not refused: {r.stdout!r}")
        check(not list((p / "src").glob("big-*.ts")), "11: wrote files despite a dirty worktree")
        r = _run(p, "--apply", "src/big.ts", "--force")
        check(list((p / "src").glob("big-*.ts")), f"11: --force did not apply: {r.stdout!r}")

        # 12. Diagnostics: records land upstream, NO_TEMPLATE_DIAG suppresses them.
        p = _project(tmp_path, "diag", {"src/big.ts": SPLITTABLE})
        fake_repo = tmp_path / "upstream"
        fake_repo.mkdir()
        (p / ".template-meta.json").write_text(json.dumps({
            "template": "typescript/node-lib", "template_version": "0.0.0",
            "template_source": {"path": str(fake_repo)},
        }))
        subprocess.run([sys.executable, ".claude/scripts/split_oversize.py"], cwd=p,
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items()
                                                            if k != "NO_TEMPLATE_DIAG"})
        logs = list((fake_repo / "_diagnostics" / "typescript/node-lib").glob("*.jsonl"))
        check(bool(logs), "12: no diagnostic record written")
        if logs:
            record = json.loads(logs[0].read_text().splitlines()[0])
            for key in ("ts", "template", "template_version", "project_path", "hook", "status", "duration_ms"):
                check(key in record, f"12: diagnostic missing {key}")
            check(record["hook"] == "split_oversize", f"12: wrong hook id {record.get('hook')}")
            before = logs[0].read_text().count("\n")
            _run(p)  # _run sets NO_TEMPLATE_DIAG=1
            check(logs[0].read_text().count("\n") == before, "12: NO_TEMPLATE_DIAG did not suppress logging")

    if f:
        print("FAIL")
        for msg in f:
            print(f"  - {msg}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
