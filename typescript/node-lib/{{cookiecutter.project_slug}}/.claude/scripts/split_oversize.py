#!/usr/bin/env python3
"""Propose — and optionally apply — a split for oversized TypeScript modules.

`just loc-check` says which files are too long; this says how to cut them. It
reads the thresholds from .quality.json, parses each oversized `.ts` file into
top-level declarations, groups them by reference graph, picks a layout that also
satisfies `just dir-check`, and prints a numbered proposal.

Nothing is written unless --apply is passed. The proposal is advisory: reject it
and restructure by hand whenever the seams it found are not the real ones (see
.claude/SPLITTING.md).

Usage:
    python3 .claude/scripts/split_oversize.py               # print proposals
    python3 .claude/scripts/split_oversize.py --json        # machine-readable
    python3 .claude/scripts/split_oversize.py --apply src/foo.ts
    python3 .claude/scripts/split_oversize.py --apply src/foo.ts --force

Each invocation also phones home via _diag.log() so the upstream repo can audit
hook health on a schedule.

Opt-out:
  - env NO_LOC_FIX=1
  - sentinel file .claude/no-loc-fix
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOOK = "split_oversize"

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _diag
except Exception:
    _diag = None


def _diag_log(status: str, duration_ms: int, meta: dict | None = None, error: BaseException | None = None) -> None:
    if _diag is None:
        return
    try:
        _diag.log(HOOK, status, duration_ms, meta=meta, error=error)
    except Exception:
        return


TYPE_KINDS = {"interface", "type", "enum"}
VALUE_KINDS = {"const", "let", "var"}
DECL_RE = re.compile(
    r"^(?P<export>export\s+)?(?P<default>default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(?P<kind>function|class|const|let|var|interface|type|enum)\b\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)"
)
IMPORT_RE = re.compile(r"^import\b")
CALLABLE_RE = re.compile(r"=>|=\s*(?:async\s+)?(?:function\b|[(<])")
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
IMPORT_NOISE = {"import", "type", "as", "from"}
CONTINUES_AFTER = set("=+-*/%<>&|^?:,.(")
CONTINUES_BEFORE = set("|&?:.,+)]}")

# Emitted verbatim into TypeScript; %-formatting keeps braces out of Jinja's way.
IMPORT_FMT = "import { %s } from '%s'"
IMPORT_TYPE_FMT = "import type { %s } from '%s'"
EXPORT_FMT = "export { %s } from '%s'"
EXPORT_TYPE_FMT = "export type { %s } from '%s'"


class Block:
    """One top-level declaration, including its leading comments/decorators."""

    def __init__(self, name: str, kind: str, start: int, decl: int, end: int, exported: bool,
                 default: bool, callable_: bool = False):
        self.name = name
        self.kind = kind
        self.start = start
        self.decl = decl
        self.end = end
        self.exported = exported
        self.default = default
        # `const f = () => …` is a function wearing a const's clothes; naming must not treat
        # it as data.
        self.callable = callable_ or kind == "function"

    @property
    def lines(self) -> int:
        return self.end - self.start + 1

    @property
    def is_data(self) -> bool:
        return self.kind in VALUE_KINDS and not self.callable


# --------------------------------------------------------------------------
# Scanning: strip strings/comments, track bracket depth
# --------------------------------------------------------------------------


def _scan_line(line: str, state: dict) -> str:
    """Return the line with comments and string bodies removed; mutate state."""
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if state["comment"]:
            if line.startswith("*/", i):
                state["comment"] = False
                i += 2
            else:
                i += 1
            continue
        if state["stack"] and state["stack"][-1] == "`":
            if c == "\\":
                i += 2
            elif c == "`":
                state["stack"].pop()
                i += 1
            elif line.startswith("${", i):
                state["stack"].append("{")
                i += 2
            else:
                i += 1
            continue
        if line.startswith("//", i):
            break
        if line.startswith("/*", i):
            state["comment"] = True
            i += 2
            continue
        if c in "'\"":
            i += 1
            while i < n and line[i] != c:
                i += 2 if line[i] == "\\" else 1
            i += 1
            continue
        if c == "`":
            state["stack"].append("`")
            i += 1
            continue
        if c in "{([":
            state["stack"].append(c)
        elif c in "})]" and state["stack"]:
            state["stack"].pop()
        out.append(c)
        i += 1
    return "".join(out)


def _scan(lines: list[str]) -> tuple[list[str], list[bool]]:
    """Return per-line code-only text and whether each line starts at top level."""
    state: dict = {"stack": [], "comment": False}
    code, at_top = [], []
    for line in lines:
        at_top.append(not state["stack"] and not state["comment"])
        code.append(_scan_line(line, state))
    return code, at_top


def _statement_end(start: int, code: list[str], at_top: list[bool]) -> int:
    """Last line index of the statement beginning at `start` (Biome omits semicolons)."""
    n = len(code)
    for j in range(start, n):
        if j + 1 < n and not at_top[j + 1]:
            continue
        cur = code[j].rstrip()
        if not cur:
            return j
        if cur[-1] in CONTINUES_AFTER:
            continue
        nxt = code[j + 1].strip() if j + 1 < n else ""
        if nxt and (nxt[0] in CONTINUES_BEFORE or nxt.startswith(("extends ", "implements "))):
            continue
        return j
    return n - 1


def _import_bindings(lines: list[str], start: int, end: int) -> set[str]:
    text = " ".join(lines[start : end + 1])
    head = text.split(" from ")[0]
    return {m.group() for m in IDENT_RE.finditer(head)} - IMPORT_NOISE


def _parse(lines: list[str]) -> tuple[list[tuple[int, int, set[str]]], list[Block], list[int]]:
    """Split a file into header imports, top-level blocks and unassigned lines."""
    code, at_top = _scan(lines)
    imports: list[tuple[int, int, set[str]]] = []
    blocks: list[Block] = []
    leftovers: list[int] = []
    i, n = 0, len(lines)
    while i < n:
        stripped = code[i].strip()
        if not stripped:
            i += 1
            continue
        end = _statement_end(i, code, at_top)
        if IMPORT_RE.match(stripped) and not blocks:
            imports.append((i, end, _import_bindings(lines, i, end)))
        else:
            m = DECL_RE.match(stripped)
            if m:
                start = i
                while start > 0:
                    prev_raw, prev_code = lines[start - 1].strip(), code[start - 1].strip()
                    if prev_raw and (not prev_code or prev_code.startswith("@")):
                        start -= 1
                    else:
                        break
                blocks.append(
                    Block(
                        name=m.group("name"),
                        kind=m.group("kind"),
                        start=start,
                        decl=i,
                        end=end,
                        exported=bool(m.group("export")),
                        default=bool(m.group("default")),
                        callable_=bool(CALLABLE_RE.search(stripped)),
                    )
                )
            else:
                leftovers.extend(range(i, end + 1))
        i = end + 1
    return imports, blocks, leftovers


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------


def _references(block: Block, code: list[str], names: list[str]) -> set[str]:
    body = "\n".join(code[block.start : block.end + 1])
    return {n for n in names if n != block.name and re.search(rf"\b{re.escape(n)}\b", body)}


def _components(blocks: list[Block], refs: dict[str, set[str]]) -> list[list[Block]]:
    parent = {b.name: b.name for b in blocks}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for b in blocks:
        for r in refs[b.name]:
            ra, rb = find(b.name), find(r)
            if ra != rb:
                parent[ra] = rb
    buckets: dict[str, list[Block]] = {}
    for b in blocks:
        buckets.setdefault(find(b.name), []).append(b)
    return sorted(buckets.values(), key=lambda g: g[0].start)


def _subdivide(group: list[Block], limit: int) -> list[list[Block]]:
    """Break a component that is still too large: types first, then size-balanced bins."""
    types = [b for b in group if b.kind in TYPE_KINDS]
    rest = [b for b in group if b.kind not in TYPE_KINDS]
    out = [types] if types else []
    bin_: list[Block] = []
    size = 0
    for b in rest:
        if bin_ and size + b.lines > limit:
            out.append(bin_)
            bin_, size = [], 0
        bin_.append(b)
        size += b.lines
    if bin_:
        out.append(bin_)
    return out or [group]


def _merge_leaf_groups(groups: list[list[Block]], refs: dict[str, set[str]]) -> list[list[Block]]:
    """Fold the pure type/constant groups together — they are leaves, so this cannot cycle."""
    owner = {b.name: i for i, g in enumerate(groups) for b in g}

    def is_leaf(i: int, g: list[Block], match) -> bool:
        return all(match(b) for b in g) and all(owner[r] == i for b in g for r in refs[b.name])

    used: set[int] = set()
    merged: list[list[Block]] = []
    for match in (lambda b: b.kind in TYPE_KINDS, lambda b: b.is_data):
        pool = [i for i, g in enumerate(groups) if i not in used and is_leaf(i, g, match)]
        if len(pool) > 1:
            merged.append(sorted((b for i in pool for b in groups[i]), key=lambda b: b.start))
            used.update(pool)
    rest = [g for i, g in enumerate(groups) if i not in used]
    return sorted(merged + rest, key=lambda g: g[0].start)


def _kebab(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "part"


def _group_name(group: list[Block], taken: set[str]) -> str:
    if all(b.kind in TYPE_KINDS for b in group):
        base = "types"
    elif all(b.is_data for b in group) and len(group) > 1:
        base = "constants"
    else:
        lead = next((b for b in group if b.exported), group[0])
        base = _kebab(lead.name)
    name, i = base, 2
    while name in taken:
        name = f"{base}-{i}"
        i += 1
    taken.add(name)
    return name


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------


def _count_dir_files(root: Path, directory: Path, globs: list[str]) -> int:
    matched = set()
    for g in globs:
        for p in root.glob(g):
            if p.is_file() and p.parent == directory:
                matched.add(p)
    return len(matched)


def _analyze(root: Path, path: Path, cfg: dict) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    code, _ = _scan(lines)
    imports, blocks, leftovers = _parse(lines)
    limit = cfg["loc"]["error"]
    target = cfg["loc"].get("warn", limit)
    result: dict = {
        "file": str(path.relative_to(root)),
        "lines": len(lines),
        "limit": limit,
        "blockers": [],
        "groups": [],
    }
    if not blocks:
        result["blockers"].append("no top-level declarations found — split by hand")
        return result

    names = [b.name for b in blocks]
    refs = {b.name: _references(b, code, names) for b in blocks}
    # A module costs more than its declarations: copied imports, and a blank line between
    # each block. Ignoring that lets a component "fit" in a file that is already too long.
    overhead = sum(end - start + 1 for start, end, _ in imports) + 2
    groups: list[list[Block]] = []
    for comp in _components(blocks, refs):
        total = sum(b.lines for b in comp) + len(comp) + overhead
        groups.extend(_subdivide(comp, max(target - overhead, 1)) if total > limit else [comp])
    groups = _merge_leaf_groups([g for g in groups if g], refs)
    if len(groups) < 2:
        result["blockers"].append(
            "every declaration is in one reference cluster — extract a seam by hand first"
        )
        return result

    # Placement: satisfy dir-check as well as loc-check.
    max_files = cfg["dir"]["max_files"]
    directory = path.parent
    current = _count_dir_files(root, directory, cfg["globs"])
    stem = path.stem
    if current + len(groups) <= max_files:
        layout = "siblings"
        reason = f"{directory.relative_to(root)}/ holds {current} files, max {max_files} — room for {len(groups)} more"
        paths = [directory / (stem + "-{}.ts") for _ in groups]
    else:
        layout = "subdirectory"
        reason = (
            f"{directory.relative_to(root)}/ holds {current} files, max {max_files} — "
            f"no room for {len(groups)} siblings, so nest them and keep {path.name} as the barrel"
        )
        paths = [directory / stem / "{}.ts" for _ in groups]
        if len(groups) > max_files:
            result["blockers"].append(f"{len(groups)} parts exceed dir.max_files ({max_files}) on their own")

    taken: set[str] = set()
    owner: dict[str, int] = {}
    named = []
    for idx, g in enumerate(groups):
        gname = _group_name(g, taken)
        for b in g:
            owner[b.name] = idx
        named.append((gname, g))

    for idx, (gname, g) in enumerate(named):
        module = str(paths[idx]).format(gname)
        rel = Path(module).relative_to(root)
        needs = sorted({r for b in g for r in refs[b.name] if owner[r] != idx})
        result["groups"].append(
            {
                "name": gname,
                "path": str(rel),
                "lines": sum(b.lines for b in g),
                "blocks": [
                    {"name": b.name, "kind": b.kind, "lines": b.lines, "exported": b.exported}
                    for b in g
                ],
                "imports_from_siblings": needs,
                "promoted": sorted(
                    b.name
                    for b in g
                    if not b.exported and any(b.name in refs[o.name] for o in blocks if owner[o.name] != idx)
                ),
            }
        )

    result["layout"] = layout
    result["layout_reason"] = reason
    result["barrel"] = sorted(b.name for b in blocks if b.exported)
    result["cycles"] = _find_cycle(named, refs, owner)
    if result["cycles"]:
        result["blockers"].append(f"reference cycle between parts: {' -> '.join(result['cycles'])}")
    if leftovers:
        first = min(leftovers) + 1
        result["blockers"].append(
            f"top-level statements outside any declaration (line {first}) cannot be placed automatically"
        )
    if any(b.default for b in blocks):
        result["blockers"].append("file has a default export — move it by hand to keep the surface stable")
    existing = [g["path"] for g in result["groups"] if (root / g["path"]).exists()]
    if existing:
        result["blockers"].append(f"target path already exists: {', '.join(existing)}")
    orphans = _orphan_lines(lines, imports, blocks)
    if orphans:
        result["orphan_comments"] = len(orphans)
    result["_internal"] = {"lines": lines, "imports": imports, "blocks": blocks, "refs": refs,
                           "owner": owner, "named": named, "paths": paths, "orphans": orphans}
    # Size each part from the text that would actually be written, not an estimate.
    for idx, g in enumerate(result["groups"]):
        g["lines"] = _render_module(idx, result).count("\n")
        if g["lines"] > limit:
            biggest = max(g["blocks"], key=lambda b: b["lines"])
            result["blockers"].append(
                f"{g['path']} would still be {g['lines']} lines (max {limit}) — "
                f"`{biggest['kind']} {biggest['name']}` is {biggest['lines']} lines on its own, so no "
                f"rearranging of top-level declarations can fix this file. Extract members by hand "
                f"(.claude/SPLITTING.md)"
            )
    return result


def _orphan_lines(lines: list[str], imports: list[tuple[int, int, set[str]]], blocks: list[Block]) -> list[int]:
    """Non-blank lines owned by neither a header import nor a block — stray comments."""
    covered: set[int] = set()
    for start, end, _ in imports:
        covered.update(range(start, end + 1))
    for b in blocks:
        covered.update(range(b.start, b.end + 1))
    return [i for i, line in enumerate(lines) if line.strip() and i not in covered]


def _find_cycle(named: list[tuple[str, list[Block]]], refs: dict[str, set[str]], owner: dict[str, int]) -> list[str]:
    edges: dict[int, set[int]] = {i: set() for i in range(len(named))}
    for i, (_, g) in enumerate(named):
        for b in g:
            for r in refs[b.name]:
                if owner[r] != i:
                    edges[i].add(owner[r])
    color: dict[int, int] = {}
    stack: list[int] = []

    def visit(node: int) -> list[int] | None:
        color[node] = 1
        stack.append(node)
        for nxt in sorted(edges[node]):
            if color.get(nxt) == 1:
                return stack[stack.index(nxt) :] + [nxt]
            if color.get(nxt) is None:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = 2
        return None

    for i in range(len(named)):
        if color.get(i) is None:
            found = visit(i)
            if found:
                return [named[i][0] for i in found]
    return []


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------


def _module_specifier(module_path: Path, from_path: Path) -> str:
    rel = os.path.relpath(module_path.with_suffix(".js"), from_path.parent)
    rel = rel.replace(os.sep, "/")
    return rel if rel.startswith(".") else f"./{rel}"


def _render_module(idx: int, analysis: dict) -> str:
    internal = analysis["_internal"]
    lines, blocks, refs, owner, named, paths = (
        internal["lines"], internal["blocks"], internal["refs"],
        internal["owner"], internal["named"], internal["paths"],
    )
    gname, group = named[idx]
    body_names = {b.name for b in group}
    body_text = "\n".join("\n".join(lines[b.start : b.end + 1]) for b in group)
    kinds = {b.name: b.kind for b in blocks}

    out: list[str] = []
    for start, end, bindings in internal["imports"]:
        if not bindings or bindings & set(re.findall(r"[A-Za-z_$][\w$]*", body_text)):
            out.extend(lines[start : end + 1])

    my_path = Path(str(paths[idx]).format(gname))
    grouped: dict[int, set[str]] = {}
    for b in group:
        for r in refs[b.name]:
            if owner[r] != idx:
                grouped.setdefault(owner[r], set()).add(r)
    for other in sorted(grouped):
        other_name = named[other][0]
        spec = _module_specifier(Path(str(paths[other]).format(other_name)), my_path)
        wanted = sorted(grouped[other])
        types = [n for n in wanted if kinds[n] in TYPE_KINDS]
        values = [n for n in wanted if kinds[n] not in TYPE_KINDS]
        if types:
            out.append(IMPORT_TYPE_FMT % (", ".join(types), spec))
        if values:
            out.append(IMPORT_FMT % (", ".join(values), spec))
    if out:
        out.append("")

    consumed = {r for i, (_, g) in enumerate(named) if i != idx for b in g for r in refs[b.name]}
    for b in group:
        chunk = list(lines[b.start : b.end + 1])
        if not b.exported and b.name in consumed and b.name in body_names:
            offset = b.decl - b.start
            chunk[offset] = f"export {chunk[offset]}"
        out.extend(chunk)
        out.append("")
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def _render_barrel(analysis: dict, path: Path) -> str:
    internal = analysis["_internal"]
    blocks, owner, named, paths = internal["blocks"], internal["owner"], internal["named"], internal["paths"]
    lines, orphans = internal["lines"], internal["orphans"]
    first_decl = min((b.start for b in blocks), default=0)
    out: list[str] = [lines[i] for i in orphans if i < first_decl]
    if out:
        out.append("")
    for idx, (gname, _) in enumerate(named):
        spec = _module_specifier(Path(str(paths[idx]).format(gname)), path)
        exported = [b for b in blocks if b.exported and owner[b.name] == idx]
        types = [b.name for b in exported if b.kind in TYPE_KINDS]
        values = [b.name for b in exported if b.kind not in TYPE_KINDS]
        if values:
            out.append(EXPORT_FMT % (", ".join(values), spec))
        if types:
            out.append(EXPORT_TYPE_FMT % (", ".join(types), spec))
    trailing = [lines[i] for i in orphans if i >= first_decl]
    if trailing:
        out.append("")
        out.extend(trailing)
    return "\n".join(out) + "\n"


def _is_dirty(root: Path, path: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return False
    if proc.returncode != 0:
        return False
    return bool(proc.stdout.strip())


def _apply(root: Path, path: Path, analysis: dict) -> list[str]:
    internal = analysis["_internal"]
    written = []
    for idx, (gname, _) in enumerate(internal["named"]):
        target = Path(str(internal["paths"][idx]).format(gname))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_module(idx, analysis), encoding="utf-8")
        written.append(str(target.relative_to(root)))
    path.write_text(_render_barrel(analysis, path), encoding="utf-8")
    written.append(str(path.relative_to(root)))
    return written


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _public(analysis: dict) -> dict:
    return {k: v for k, v in analysis.items() if not k.startswith("_")}


def _print_proposal(analysis: dict) -> None:
    print(f"[loc-fix] {analysis['file']} — {analysis['lines']} lines (max {analysis['limit']})")
    if analysis.get("layout"):
        print(f"  layout: {analysis['layout']} — {analysis['layout_reason']}")
    for i, g in enumerate(analysis["groups"], 1):
        members = ", ".join(b["name"] + ("" if b["exported"] else "*") for b in g["blocks"])
        print(f"  {i}. {g['path']:<44} {g['lines']:>4} lines  ({members})")
    if analysis["groups"]:
        print(f"  {analysis['file']} becomes a barrel re-exporting: {', '.join(analysis['barrel']) or '(nothing)'}")
        if any(not b["exported"] for g in analysis["groups"] for b in g["blocks"]):
            print("  * = file-private; `export`ed in its new module only when a sibling needs it, never in the barrel")
    if analysis.get("orphan_comments"):
        print(f"  note: {analysis['orphan_comments']} comment line(s) belong to no declaration — kept in the barrel")
    for b in analysis["blockers"]:
        print(f"  blocked: {b}")
    if analysis["groups"] and not analysis["blockers"]:
        print(f"  apply: python3 .claude/scripts/split_oversize.py --apply {analysis['file']}")
        print("  then:  just lint-fix && just check   (apply leaves unused imports for Biome to clean)")


def _load_config(root: Path) -> dict | None:
    cfg_path = root / ".quality.json"
    if not cfg_path.is_file():
        return None
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not all(k in cfg for k in ("loc", "dir", "globs")):
        return None
    return cfg


def _oversized(root: Path, cfg: dict) -> list[Path]:
    limit = cfg["loc"]["error"]
    found = set()
    for pattern in cfg["globs"]:
        for p in root.glob(pattern):
            if not p.is_file() or p.suffix != ".ts" or p.name.endswith(".d.ts"):
                continue
            if p.read_text(encoding="utf-8", errors="replace").count("\n") > limit:
                found.add(p)
    return sorted(found)


def main() -> None:
    started = time.monotonic()

    def elapsed_ms() -> int:
        return int((time.monotonic() - started) * 1000)

    parser = argparse.ArgumentParser(description="Propose splits for oversized TypeScript modules.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--apply", metavar="PATH", help="write the proposed split for one file")
    parser.add_argument("--force", action="store_true", help="apply even if the file has uncommitted changes")
    args = parser.parse_args()

    try:
        if os.environ.get("NO_LOC_FIX"):
            _diag_log("noop", elapsed_ms(), meta={"reason": "env-opt-out"})
            return

        root = Path.cwd()
        if (root / ".claude" / "no-loc-fix").is_file():
            _diag_log("noop", elapsed_ms(), meta={"reason": "sentinel-opt-out"})
            return

        cfg = _load_config(root)
        if cfg is None:
            _diag_log("noop", elapsed_ms(), meta={"reason": "no-quality-config"})
            return

        targets = [root / args.apply] if args.apply else _oversized(root, cfg)
        if not targets:
            if args.json:
                print(json.dumps({"files": []}, indent=2))
            else:
                print("[loc-fix] nothing to split — every file is within .quality.json's loc.error")
            _diag_log("noop", elapsed_ms(), meta={"reason": "no-oversized-files"})
            return

        analyses = []
        for path in targets:
            if not path.is_file():
                print(f"[loc-fix] not found: {args.apply}")
                _diag_log("noop", elapsed_ms(), meta={"reason": "missing-target"})
                return
            analyses.append(_analyze(root, path, cfg))

        if args.apply:
            analysis = analyses[0]
            path = targets[0]
            if analysis["blockers"]:
                _print_proposal(analysis)
                print("  not applied — resolve the blockers above, or split by hand")
                _diag_log("noop", elapsed_ms(), meta={"reason": "blocked", "file": analysis["file"],
                                                      "blockers": analysis["blockers"]})
                return
            if not args.force and _is_dirty(root, path):
                _print_proposal(analysis)
                print(f"  not applied — {analysis['file']} has uncommitted changes (commit them, or pass --force)")
                _diag_log("noop", elapsed_ms(), meta={"reason": "dirty-worktree", "file": analysis["file"]})
                return
            written = _apply(root, path, analysis)
            print(f"[loc-fix] split {analysis['file']} into {len(written) - 1} modules + barrel:")
            for w in written:
                print(f"  {w}")
            print("  next: just lint-fix && just check")
            _diag_log("ok", elapsed_ms(), meta={"action": "apply", "file": analysis["file"], "written": written})
            return

        if args.json:
            print(json.dumps({"files": [_public(a) for a in analyses]}, indent=2))
        else:
            for a in analyses:
                _print_proposal(a)
        _diag_log("ok", elapsed_ms(), meta={"action": "propose", "files": [a["file"] for a in analyses]})
    except Exception as e:
        _diag_log("error", elapsed_ms(), error=e)
        print(f"[loc-fix] analysis failed: {type(e).__name__}: {e}")
        return


if __name__ == "__main__":
    main()
