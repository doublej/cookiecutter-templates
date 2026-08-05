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
import re
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

# ping <-> pong are mutually recursive functions: SCC grouping must keep them in one
# part, so the file splits cleanly instead of refusing on a part cycle.
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

# Mutual recursion between a const arrow and a function, too big for one part: a
# const's initializer runs at module evaluation, so this cycle cannot be split and
# cannot be exempted — the tool must refuse.
MIXED_CYCLE = """export interface Shared {
  depth: number
}

export const ping = (s: Shared): string => {
  if (s.depth <= 0) {
    return 'done'
  }
  return pong({ depth: s.depth - 1 })
}

export function pong(s: Shared): string {
  if (s.depth <= 0) {
    return 'done'
  }
  if (s.depth > 100) {
    return 'far'
  }
  if (s.depth > 50) {
    return 'mid'
  }
  return ping({ depth: s.depth - 1 })
}
"""

# A regex literal holding an unbalanced brace: naive depth counting swallows the rest of
# the file and reports one big cluster.
REGEX_BRACE = """export function alpha(text: string): string {
  return text.replace(/{/g, '')
}

export function beta(text: string): string {
  return alpha(text).trim()
}

export function gamma(text: string): string {
  return beta(text).toUpperCase()
}

export function delta(text: string): string {
  return gamma(text).padEnd(4)
}

export function epsilon(text: string): string {
  return delta(text).slice(0, 3)
}
"""

# An overload set is one symbol spelled across several declarations.
OVERLOADS = """export interface Shape {
  kind: string
}

const BRACE_RE = /[{}]/g

export function strip(text: string): string {
  return text.replace(BRACE_RE, '')
}

export function pad(text: string): string {
  return ` ${strip(text)} `
}

export function overload(value: string): string
export function overload(value: number): number
export function overload(value: string | number): string | number {
  return value
}

export function useOverload(s: Shape): string {
  return `${s.kind}${overload('x')}`
}
"""

# One oversized class of PUBLIC one-line methods — member extraction must refuse:
# even delegating stubs are as long as the bodies they replace, so the facade
# cannot shrink below the limit.
GIANT_CLASS = "const TAG = 'giant'\n\nexport class Giant {\n" + "".join(
    f"  step{i}(): string {{\n    return `${{TAG}}-{i}`\n  }}\n" for i in range(12)
) + "}\n"

# Public methods with real bodies: pass 1 keeps them all ("public API"), pass 2
# moves the bodies behind delegating stubs so the type surface stays identical.
STUB_CLASS = """export class Api {
  private base = '/v1'

  fetchUsers(limit: number): string {
    const parts = [this.base]
    parts.push('users')
    parts.push(String(limit))
    parts.push('a')
    parts.push('b')
    return parts.join('/')
  }

  fetchPosts(limit: number, offset?: number): string {
    const parts = [this.base]
    parts.push('posts')
    parts.push(String(limit))
    parts.push(String(offset ?? 0))
    parts.push('c')
    return parts.join('/')
  }

  fetchTags(...names: string[]): string {
    const parts = [this.base]
    parts.push('tags')
    parts.push(...names)
    parts.push('d')
    parts.push('e')
    return parts.join('/')
  }
}
"""

# A block reading import.meta (and its dependents) must stay in the barrel;
# everything else still moves out.
META_PIN = """import { fileURLToPath } from 'node:url'

const selfPath = fileURLToPath(import.meta.url)

export function locate(name: string): string {
  return selfPath + name
}

export function alpha(n: number): number {
  return n + 1
}

export function beta(n: number): number {
  return alpha(n) * 2
}

export function gamma(n: number): number {
  return n - 1
}

export function delta(n: number): number {
  return gamma(n) * 3
}
"""

# One oversized class dominated by PRIVATE methods — the member splitter's home turf.
# Covers: this -> self in bodies and template literals, this.x() -> x(this, ...),
# a no-`this` method that gets no self parameter, constructor parameter properties,
# and de-privatized fields.
MEMBER_CLASS = """import { readFileSync } from 'node:fs'

interface Job {
  id: string
  tries: number
}

const MAX_TRIES = 3

export class Engine {
  private jobs: Job[] = []
  private counter = 0

  constructor(private readonly label: string) {}

  run(id: string): string {
    this.enqueue(id)
    return this.describe()
  }

  private enqueue(id: string) {
    const job: Job = { id: this.stamp(id), tries: 0 }
    this.jobs.push(job)
    this.bump()
  }

  private stamp(id: string): string {
    return id.toUpperCase()
  }

  private bump() {
    this.counter++
    if (this.counter > MAX_TRIES) {
      this.reset()
    }
  }

  private reset() {
    this.counter = 0
    this.jobs = []
  }

  private describe(): string {
    return `${this.label}: ${this.jobs.length} jobs (${readFileSync('/dev/null', 'utf8')})`
  }
}
"""

# A class where nothing is safely movable: a getter, a nested `this` scope,
# and inherited member access on an `extends` class.
UNSAFE_CLASS = """class Base {
  protected shared = 1
}

export class Stuck extends Base {
  private total = 0

  get sum(): number {
    return this.total
  }

  private tick(): number {
    this.total += this.shared
    return this.total
  }

  private legacy(): number {
    const f = function (this: Stuck): number {
      return this.total
    }
    return f.call(this)
  }

  private handler(): number {
    return this.shared + this.legacy()
  }
}
"""

# A giant annotated array literal — the data sub-case.
DATA_ARRAY = """export interface Row {
  id: string
  label: string
}

export const ROWS: Row[] = [
""" + "".join(
    f"  {{\n    id: 'r{i}',\n    label: 'row {i}',\n  }},\n" for i in range(6)
) + """]

export function findRow(id: string): Row | undefined {
  return ROWS.find((r) => r.id === id)
}
"""

# The same array without an annotation — parts would re-infer element types.
DATA_NO_ANNOTATION = "export const BIG = [\n" + "".join(
    f"  {{\n    id: 'r{i}',\n    label: 'row {i}',\n  }},\n" for i in range(6)
) + "]\n"


def _project(root: Path, name: str, files: dict[str, str], quality: dict | None = QUALITY) -> Path:
    project = root / name
    (project / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(SRC, project / ".claude" / "scripts" / "split_oversize.py")
    shutil.copy(SRC.parent / "split_members.py", project / ".claude" / "scripts" / "split_members.py")
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
            if line.startswith("export") and "{" in line:
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

        # 9a. Mutually recursive functions are one SCC: same part, applies cleanly.
        p = _project(tmp_path, "cyclic", {"src/cyc.ts": CYCLIC})
        r = _run(p, "--json")
        entry = json.loads(r.stdout)["files"][0]
        check(not entry["blockers"], f"9a: function recursion should not block: {entry['blockers']}")
        homes = [g["path"] for g in entry["groups"]
                 if any(b["name"] in ("ping", "pong") for b in g["blocks"])]
        check(len(set(homes)) == 1, f"9a: ping/pong split across parts: {homes}")
        r = _run(p, "--apply", "src/cyc.ts")
        check("split src/cyc.ts" in r.stdout, f"9a: did not apply: {r.stdout!r}")

        # 9b. Mutual recursion involving a const arrow cannot be split or exempted.
        p = _project(tmp_path, "mixed-cycle", {"src/mix.ts": MIXED_CYCLE})
        r = _run(p, "--apply", "src/mix.ts")
        check("would still be" in r.stdout, f"9b: mixed cycle not refused: {r.stdout!r}")
        check("not applied" in r.stdout, f"9b: applied a mixed cycle: {r.stdout!r}")
        check(not list((p / "src").glob("mix-*.ts")), "9b: wrote files despite refusal")

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

        # 13. A regex literal's braces are not code braces.
        p = _project(tmp_path, "regex", {"src/re.ts": REGEX_BRACE},
                     quality={"loc": {"warn": 12, "error": 18}, "dir": {"max_files": 6},
                              "globs": ["src/**/*.ts"]})
        r = _run(p)
        check("one reference cluster" not in r.stdout, f"13: regex swallowed the file: {r.stdout!r}")
        check("layout:" in r.stdout, f"13: no proposal produced: {r.stdout!r}")

        # 14. An overload set stays whole and is exported exactly once.
        p = _project(tmp_path, "overloads", {"src/ov.ts": OVERLOADS},
                     quality={"loc": {"warn": 12, "error": 18}, "dir": {"max_files": 6},
                              "globs": ["src/**/*.ts"]})
        r = _run(p, "--json")
        entry = json.loads(r.stdout)["files"][0]
        check(entry["barrel"].count("overload") == 1,
              f"14: overload exported {entry['barrel'].count('overload')}x: {entry['barrel']}")
        homes = [g["path"] for g in entry["groups"] if any(b["name"] == "overload" for b in g["blocks"])]
        check(len(homes) == 1, f"14: overload split across parts: {homes}")
        r = _run(p, "--apply", "src/ov.ts")
        barrel = (p / "src" / "ov.ts").read_text()
        barrel_names = [n.strip() for grp in re.findall(r"export (?:type )?\{([^}]*)\}", barrel)
                        for n in grp.split(",")]
        check(barrel_names.count("overload") == 1, f"14: barrel repeats overload: {barrel!r}")
        part = next(q for q in (p / "src").glob("ov-*.ts") if "overload" in q.read_text())
        check(part.read_text().count("export function overload") == 3,
              "14: overload signatures did not travel together")

        # 15. Giant private-method class -> member extraction proposal and apply.
        member_quality = {"loc": {"warn": 22, "error": 30}, "dir": {"max_files": 6},
                          "globs": ["src/**/*.ts"]}
        p = _project(tmp_path, "members", {"src/engine.ts": MEMBER_CLASS}, quality=member_quality)
        r = _run(p)
        check("strategy: member extraction" in r.stdout, f"15: no member strategy: {r.stdout!r}")
        check("kept in class: run — public API" in r.stdout, f"15: public method not kept: {r.stdout!r}")
        r = _run(p, "--json")
        entry = json.loads(r.stdout)["files"][0]
        check(entry.get("strategy") == "members", f"15: json strategy wrong: {entry.get('strategy')}")
        check("_internal" not in entry, "15: internal state leaked into --json")
        check("facade" in entry and entry["facade"]["lines"] <= 30, f"15: facade sizing: {entry.get('facade')}")
        r = _run(p, "--apply", "src/engine.ts")
        check("modules + facade" in r.stdout, f"15: apply did not report a facade: {r.stdout!r}")
        facade = (p / "src" / "engine.ts").read_text()
        check("export class Engine" in facade, "15: class lost from the facade")
        check("enqueue(this, id)" in facade, f"15: facade call not rewritten: {facade!r}")
        check("describe(this)" in facade, "15: facade call to describe not rewritten")
        check("public readonly label" in facade, "15: constructor parameter property not widened")
        check("private jobs" not in facade, "15: touched field kept its private modifier")
        parts = "\n".join(q.read_text() for q in (p / "src").glob("engine-*.ts"))
        check("export function enqueue(self: Engine" in parts, f"15: no self-taking function: {parts!r}")
        check("id: stamp(id)" in parts, "15: no-this method call should not pass self")
        check("stamp(self" not in parts, "15: no-this method wrongly given self")
        check("bump(self)" in parts, "15: sibling call not rewritten to bump(self)")
        check("self.label" in parts, "15: template-literal `this` not rewritten to self")
        check("import type { Engine } from './engine.js'" in parts, "15: class type import missing")
        r = _run(p)
        check("nothing to split" in r.stdout, f"15: applied output still oversized: {r.stdout!r}")

        # 16. Nothing safely movable -> honest refusal, nothing written.
        p = _project(tmp_path, "unsafe", {"src/stuck.ts": UNSAFE_CLASS},
                     quality={"loc": {"warn": 12, "error": 18}, "dir": {"max_files": 6},
                              "globs": ["src/**/*.ts"]})
        r = _run(p, "--apply", "src/stuck.ts")
        check("none of its members can be extracted safely" in r.stdout,
              f"16: unsafe class not refused: {r.stdout!r}")
        check("not applied" in r.stdout, f"16: applied an unsafe class: {r.stdout!r}")
        check(not list((p / "src").glob("stuck-*.ts")) and not (p / "src" / "stuck").exists(),
              "16: wrote files despite refusal")

        # 17. Giant annotated array -> element split with spread reassembly.
        data_quality = {"loc": {"warn": 16, "error": 24}, "dir": {"max_files": 6},
                        "globs": ["src/**/*.ts"]}
        p = _project(tmp_path, "data", {"src/rows.ts": DATA_ARRAY}, quality=data_quality)
        r = _run(p)
        check("strategy: data extraction" in r.stdout, f"17: no data strategy: {r.stdout!r}")
        r = _run(p, "--apply", "src/rows.ts")
        check("modules + facade" in r.stdout, f"17: apply failed: {r.stdout!r}")
        facade = (p / "src" / "rows.ts").read_text()
        check("export const ROWS: Row[] = [" in facade, f"17: reassembly lost annotation: {facade!r}")
        check("...ROWS_1," in facade, "17: spread reassembly missing")
        check("export function findRow" in facade, "17: helper lost from the facade")
        parts = sorted((p / "src").glob("rows-data-*.ts")) or sorted((p / "src" / "rows").glob("*.ts"))
        check(len(parts) >= 2, f"17: expected data parts, got {parts}")
        bodies = "\n".join(q.read_text() for q in parts)
        check("export const ROWS_1: Row[] = [" in bodies, f"17: part lost element typing: {bodies!r}")
        check("import type { Row }" in bodies, "17: part missing the element type import")
        r = _run(p)
        check("nothing to split" in r.stdout, f"17: applied data still oversized: {r.stdout!r}")

        # 18. Un-annotated giant array -> refused (element literal types would widen).
        p = _project(tmp_path, "data-noann", {"src/big.ts": DATA_NO_ANNOTATION}, quality=data_quality)
        r = _run(p, "--apply", "src/big.ts")
        check("annotation" in r.stdout, f"18: missing annotation not flagged: {r.stdout!r}")
        check("not applied" in r.stdout, f"18: applied without annotation: {r.stdout!r}")

        # 19. All-public class with real bodies -> delegating stubs keep the surface.
        p = _project(tmp_path, "stubs", {"src/api.ts": STUB_CLASS},
                     quality={"loc": {"warn": 14, "error": 20}, "dir": {"max_files": 6},
                              "globs": ["src/**/*.ts"]})
        r = _run(p)
        check("stubbed:" in r.stdout, f"19: no stub proposal: {r.stdout!r}")
        r = _run(p, "--apply", "src/api.ts")
        check("modules + facade" in r.stdout, f"19: apply failed: {r.stdout!r}")
        facade = (p / "src" / "api.ts").read_text()
        check("fetchUsers(limit: number): string {" in facade, "19: stub signature changed")
        check("return fetchUsers(this, limit)" in facade, f"19: stub does not delegate: {facade!r}")
        check("return fetchTags(this, ...names)" in facade, "19: rest parameter not forwarded")
        check("private base" not in facade, "19: touched field kept its private modifier")
        parts = "\n".join(q.read_text() for q in (p / "src").glob("api-*.ts"))
        check("export function fetchUsers(self: Api" in parts, f"19: no self-taking function: {parts!r}")
        r = _run(p)
        check("nothing to split" in r.stdout, f"19: applied output still oversized: {r.stdout!r}")

        # 20. import.meta block (and its dependents) pinned to the barrel; rest moves.
        p = _project(tmp_path, "metapin", {"src/loc.ts": META_PIN},
                     quality={"loc": {"warn": 12, "error": 20}, "dir": {"max_files": 6},
                              "globs": ["src/**/*.ts"]})
        r = _run(p)
        check("pinned to the barrel" in r.stdout, f"20: no pin note: {r.stdout!r}")
        check("selfPath" in r.stdout and "locate" in r.stdout, f"20: pin closure wrong: {r.stdout!r}")
        r = _run(p, "--apply", "src/loc.ts")
        barrel = (p / "src" / "loc.ts").read_text()
        check("fileURLToPath(import.meta.url)" in barrel, f"20: pinned block left the barrel: {barrel!r}")
        check("export function locate" in barrel, "20: pinned dependent left the barrel")
        parts = "\n".join(q.read_text() for q in (p / "src").glob("loc-*.ts"))
        check(parts and "import.meta" not in parts, f"20: import.meta moved into a part: {parts!r}")
        check("export function alpha" in parts, "20: movers did not move")
        r = _run(p)
        check("nothing to split" in r.stdout, f"20: applied output still oversized: {r.stdout!r}")

    if f:
        print("FAIL")
        for msg in f:
            print(f"  - {msg}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
