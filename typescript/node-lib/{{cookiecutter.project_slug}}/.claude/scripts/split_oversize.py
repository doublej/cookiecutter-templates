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

try:
    import split_members
except Exception:
    split_members = None


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
IMPORT_RE = re.compile(r"^import\b(?!\s*\()")
AMBIENT_RE = re.compile(r"^(?:export\s+)?declare\s+(?:module|global)\b")
# A movable top-level statement: a bare call (or tagged template) like `describe(...)`.
CALL_STMT_RE = re.compile(r"^[A-Za-z_$][\w$]*(?:\.[\w$]+)*\s*[(`]")
# Mock hoisting (vitest/jest) is file-scoped; moving any statement would break it.
MOCK_RE = re.compile(r"\b(?:vi|jest)\.mock\s*\(")
# Simple destructuring declarations only: one flat pattern, no nesting or defaults.
DESTRUCT_RE = re.compile(
    r"^(?P<export>export\s+)?(?:declare\s+)?(?P<kind>const|let|var)\s*"
    r"(?P<pat>\{[^{}\[\]()=]*\}|\[[^{}\[\]()=]*\])\s*="
)
CALLABLE_RE = re.compile(r"=>|=\s*(?:async\s+)?(?:function\b|[(<])")
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
IMPORT_NOISE = {"import", "type", "as", "from"}
REGEX_PRECEDERS = set("=(,:[!&|?{};+-*%<>~^")
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
                 default: bool, callable_: bool = False, aliases: list[str] | None = None):
        self.name = name
        self.kind = kind
        self.start = start
        self.decl = decl
        self.end = end
        self.exported = exported
        self.default = default
        # A destructuring declaration binds several names; `name` is the first one.
        self.aliases = aliases or []
        # `const f = () => …` is a function wearing a const's clothes; naming must not treat
        # it as data.
        self.callable = callable_ or kind == "function"

    @property
    def all_names(self) -> list[str]:
        return [self.name] + self.aliases

    @property
    def lines(self) -> int:
        return self.end - self.start + 1

    @property
    def is_data(self) -> bool:
        return self.kind in VALUE_KINDS and not self.callable


# --------------------------------------------------------------------------
# Scanning: strip strings/comments, track bracket depth
# --------------------------------------------------------------------------


def _starts_regex(code_so_far: list[str]) -> bool:
    """Distinguish a regex literal from a division, by what precedes the slash."""
    prev = next((ch for ch in reversed(code_so_far) if not ch.isspace()), "")
    return prev == "" or prev in REGEX_PRECEDERS


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
                out.append("`")
                i += 1
            elif line.startswith("${", i):
                state["stack"].append("{")
                i += 2
            else:
                if line.startswith("/*", i) or line.startswith("*/", i):
                    state["marker_in_string"] = True
                i += 1
            continue
        if line.startswith("//", i):
            if "/*" in line[i + 2 :] or "*/" in line[i + 2 :]:
                state["marker_in_string"] = True
            break
        if line.startswith("/*", i):
            state["comment"] = True
            i += 2
            continue
        if c in "'\"":
            # Keep the delimiters: a line ending in `= 'x'` must not look like a
            # dangling `=` continuation once the string body is stripped.
            out.append(c)
            i += 1
            while i < n and line[i] != c:
                if line.startswith("/*", i) or line.startswith("*/", i):
                    state["marker_in_string"] = True
                i += 2 if line[i] == "\\" else 1
            if i < n:
                out.append(c)
            i += 1
            continue
        if c == "`":
            state["stack"].append("`")
            out.append(c)
            i += 1
            continue
        if c == "/" and _starts_regex(out):
            # A regex literal's braces are not code braces: /{/ would corrupt the depth.
            out.append(c)
            i += 1
            in_class = False
            while i < n:
                ch = line[i]
                if line.startswith("*/", i):
                    state["marker_in_string"] = True
                if ch == "\\":
                    i += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    out.append(ch)
                    i += 1
                    break
                i += 1
            continue
        if c in "{([":
            state["stack"].append(c)
        elif c in "})]" and state["stack"]:
            state["stack"].pop()
        out.append(c)
        i += 1
    return "".join(out)


def _scan(lines: list[str]) -> tuple[list[str], list[bool], list[bool], bool]:
    """Per-line code-only text, whether each line starts at top level, whether it
    starts inside a template literal, and whether any string embeds /* or */."""
    state: dict = {"stack": [], "comment": False, "marker_in_string": False}
    code, at_top, in_template = [], [], []
    for line in lines:
        at_top.append(not state["stack"] and not state["comment"])
        in_template.append("`" in state["stack"])
        code.append(_scan_line(line, state))
    return code, at_top, in_template, state["marker_in_string"]


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


def _destructured_names(pattern: str) -> list[str]:
    """Names bound by a flat destructuring pattern: `{ a, b: c, ...rest }` -> a, c, rest.
    An identifier immediately followed by `:` is a source key, not a binding."""
    out: list[str] = []
    for m in IDENT_RE.finditer(pattern):
        rest = pattern[m.end():].lstrip()
        if not rest.startswith(":"):
            out.append(m.group())
    return out


def _parse(
    lines: list[str],
) -> tuple[list[tuple[int, int, set[str]]], list[Block], list[tuple[int, int]], list[tuple[int, int]]]:
    """Split a file into header imports, top-level blocks, ambient declare-blocks,
    and remaining top-level statements (as line ranges)."""
    code, at_top, _, _ = _scan(lines)
    imports: list[tuple[int, int, set[str]]] = []
    blocks: list[Block] = []
    ambients: list[tuple[int, int]] = []
    statements: list[tuple[int, int]] = []
    i, n = 0, len(lines)
    while i < n:
        stripped = code[i].strip()
        if not stripped:
            i += 1
            continue
        end = _statement_end(i, code, at_top)
        # Imports are hoisted, so they count as header imports wherever they appear.
        if IMPORT_RE.match(stripped):
            imports.append((i, end, _import_bindings(lines, i, end)))
        else:
            m = DECL_RE.match(stripped)
            d = DESTRUCT_RE.match(stripped) if not m else None
            if m or d:
                start = i
                while start > 0:
                    prev_raw, prev_code = lines[start - 1].strip(), code[start - 1].strip()
                    if prev_raw and (not prev_code or prev_code.startswith("@")):
                        start -= 1
                    else:
                        break
                if m:
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
                    bound = _destructured_names(d.group("pat"))
                    if bound:
                        blocks.append(
                            Block(
                                name=bound[0],
                                kind=d.group("kind"),
                                start=start,
                                decl=i,
                                end=end,
                                exported=bool(d.group("export")),
                                default=False,
                                aliases=bound[1:],
                            )
                        )
                    else:
                        statements.append((i, end))
            elif AMBIENT_RE.match(stripped):
                ambients.append((i, end))
            else:
                statements.append((i, end))
        i = end + 1
    return imports, _coalesce(blocks), ambients, statements


def _coalesce(blocks: list[Block]) -> list[Block]:
    """Fuse adjacent same-name declarations — overload sets, interface+namespace merging.

    They are one symbol: splitting them across modules would both break the type and
    emit the name twice in the barrel.
    """
    out: list[Block] = []
    for b in blocks:
        if out and out[-1].name == b.name:
            prev = out[-1]
            prev.end = b.end
            prev.exported = prev.exported or b.exported
            prev.default = prev.default or b.default
            prev.callable = prev.callable or b.callable
            continue
        out.append(b)
    return out


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------


def _references(block: Block, code: list[str], names: list[str], name_of: dict[str, str]) -> set[str]:
    """Primary names of the blocks this block's body mentions (via any bound name)."""
    body = "\n".join(code[block.start : block.end + 1])
    return {
        name_of[n] for n in names
        if name_of[n] != block.name and re.search(rf"\b{re.escape(n)}\b", body)
    }


def _sccs(blocks: list[Block], refs: dict[str, set[str]]) -> list[list[Block]]:
    """Strongly connected components of the *directed* reference graph, returned in
    dependency-first topological order (ties broken by source position).

    A shared type referenced by everything no longer fuses the whole file into one
    component — only genuine mutual recursion stays together. Packing contiguous
    runs of this order cannot produce an import cycle between parts, because every
    cross-part edge points at an earlier part.
    """
    by_name = {b.name: b for b in blocks}
    order = [b.name for b in blocks]
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = 0

    for root in order:
        if root in index:
            continue
        work = [(root, iter(sorted(refs[root])))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(sorted(refs[nxt]))))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                sccs.append(comp)

    # Condense and topo-sort so every SCC comes after everything it references.
    comp_of = {n: i for i, comp in enumerate(sccs) for n in comp}
    out_edges: list[set[int]] = [set() for _ in sccs]
    for i, comp in enumerate(sccs):
        for n in comp:
            for r in refs[n]:
                if comp_of[r] != i:
                    out_edges[i].add(comp_of[r])
    remaining = {i: len(out_edges[i]) for i in range(len(sccs))}
    dependents: list[set[int]] = [set() for _ in sccs]
    for i, deps in enumerate(out_edges):
        for d in deps:
            dependents[d].add(i)
    import heapq

    pos = {i: min(by_name[n].start for n in comp) for i, comp in enumerate(sccs)}
    ready = [(pos[i], i) for i in remaining if remaining[i] == 0]
    heapq.heapify(ready)
    ordered: list[list[Block]] = []
    while ready:
        _, i = heapq.heappop(ready)
        ordered.append(sorted((by_name[n] for n in sccs[i]), key=lambda b: b.start))
        for dep in dependents[i]:
            remaining[dep] -= 1
            if remaining[dep] == 0:
                heapq.heappush(ready, (pos[dep], dep))
    return ordered


def _pack(sccs: list[list[Block]], cap: int) -> list[list[Block]]:
    """Pack contiguous runs of topo-ordered SCCs into bins of at most `cap` lines.

    An SCC bigger than cap is mutual recursion: if it is functions only it can be
    size-binned (hoisted declarations make the resulting import cycle harmless);
    anything else stays whole and gets flagged by the per-part size check.
    """
    groups: list[list[Block]] = []
    bin_: list[Block] = []
    size = 0

    def flush() -> None:
        nonlocal bin_, size
        if bin_:
            groups.append(bin_)
            bin_, size = [], 0

    for scc in sccs:
        scc_size = sum(b.lines + 1 for b in scc)
        if scc_size > cap:
            flush()
            if all(b.kind == "function" for b in scc):
                cur: list[Block] = []
                cur_size = 0
                for b in scc:
                    if cur and cur_size + b.lines + 1 > cap:
                        groups.append(cur)
                        cur, cur_size = [], 0
                    cur.append(b)
                    cur_size += b.lines + 1
                if cur:
                    groups.append(cur)
            else:
                groups.append(list(scc))
            continue
        if bin_ and size + scc_size > cap:
            flush()
        bin_.extend(scc)
        size += scc_size
    flush()
    return [sorted(g, key=lambda b: b.start) for g in groups]


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
    code, _, in_template, marker_in_string = _scan(lines)
    imports, blocks, ambients, statements = _parse(lines)
    limit = cfg["loc"]["error"]
    target = cfg["loc"].get("warn", limit)
    result: dict = {
        "file": str(path.relative_to(root)),
        "lines": len(lines),
        "limit": limit,
        "blockers": [],
        "groups": [],
    }
    if not blocks and not statements:
        result["blockers"].append("no top-level declarations found — split by hand")
        return result

    # Code generators embed module-source text inside template literals; a line
    # scanner cannot split those with confidence, and naive tooling reading the
    # result would see a changed surface.
    embedded = next(
        (i for i, t in enumerate(in_template)
         if t and re.match(r"\s*(?:export|import)\b", lines[i])),
        None,
    )
    if embedded is not None:
        result["blockers"].append(
            f"a template literal embeds module-source text (line {embedded + 1}) — "
            f"code-generator files must be split by hand"
        )
        return result
    if marker_in_string:
        result["blockers"].append(
            "a string or regex literal contains block-comment syntax (/* or */) — "
            "comment-aware tooling mis-reads reordered output; split by hand"
        )
        return result

    name_of = {nm: b.name for b in blocks for nm in b.all_names}
    all_bound = [nm for b in blocks for nm in b.all_names]
    repeated = sorted({n for n in all_bound if all_bound.count(n) > 1})
    if repeated:
        result["blockers"].append(
            f"the same name is declared in more than one place ({', '.join(repeated)}) — "
            f"move the merged declarations next to each other first"
        )
    refs = {b.name: _references(b, code, all_bound, name_of) for b in blocks}
    # A module costs more than its declarations: copied imports, and a blank line between
    # each block. Ignoring that lets a component "fit" in a file that is already too long.
    overhead = sum(end - start + 1 for start, end, _ in imports) + 2
    # One declaration bigger than any module can hold: no regrouping of top-level
    # declarations can help, so hand over to the member-level splitter.
    biggest_block = max(blocks, key=lambda b: b.lines) if blocks else None
    if blocks and split_members is not None and biggest_block.lines + overhead + 1 > limit:
        return split_members.analyze(root, path, cfg, lines, imports, blocks, biggest_block)

    # Blocks that read import.meta are pinned to the barrel — import.meta is
    # per-module, so their meaning would change in a moved file. Anything that
    # references a pinned block is pinned too, so no part ever needs to import
    # from the barrel (which would cycle).
    pinned_names: set[str] = {
        b.name for b in blocks if "import.meta" in "\n".join(code[b.start : b.end + 1])
    }
    changed = bool(pinned_names)
    while changed:
        changed = False
        for b in blocks:
            if b.name not in pinned_names and refs[b.name] & pinned_names:
                pinned_names.add(b.name)
                changed = True
    movers = [b for b in blocks if b.name not in pinned_names]
    pinned_blocks = [b for b in blocks if b.name in pinned_names]
    if pinned_names:
        name_of = {nm: b.name for b in movers for nm in b.all_names}
        result["pinned"] = sorted(b.name for b in pinned_blocks)

    # Statements between declarations cannot move without reordering side effects.
    # Statements after the last declaration stay in the barrel: the parts (its
    # imports) evaluate first, exactly as the declarations did in the original.
    # Ambient declare-module/global blocks are position-independent and also stay.
    last_block_end = max((b.end for b in movers), default=-1)
    interleaved = [(s, e) for s, e in statements if s <= last_block_end]
    if interleaved:
        first = interleaved[0][0] + 1
        result["blockers"].append(
            f"top-level statements outside any declaration (line {first}) cannot be placed automatically"
        )
    kept_code = "\n".join(
        [code[i] for s, e in statements + ambients for i in range(s, e + 1)]
        + [code[i] for b in pinned_blocks for i in range(b.start, b.end + 1)]
    )
    mutated = sorted({
        nm for b in movers if b.kind in ("let", "var")
        for nm in b.all_names
        if re.search(rf"\b{re.escape(nm)}\s*(?:=(?![=>])|\+\+|--|[-+*/%&|^]=)", kept_code)
    })
    if mutated:
        result["blockers"].append(
            f"top-level statements outside any declaration reassign {', '.join(mutated)} — "
            f"a moved `let` cannot be written through an import binding"
        )
    barrel_needs = {name_of[n] for n in set(IDENT_RE.findall(kept_code)) if n in name_of}

    # When what trails is too big to stay in the barrel, move a prefix of it out as
    # side-effect parts — bare call statements only (`describe(...)`, `run()`), in
    # original order, imported by the barrel in that same order. `vi.mock` hoisting
    # and `import.meta` are per-module semantics that must not change files.
    trailing = [(s, e) for s, e in statements if s > last_block_end]
    call_bins: list[list[tuple[int, int]]] = []
    trailing_total = sum(e - s + 1 for s, e in trailing)
    # Pinned blocks stay in the barrel body, which runs after all imports — a
    # moved call statement would then run *before* them, reordering effects.
    if trailing and not pinned_blocks and (not movers or trailing_total > max(limit - 40, 1)) \
            and not MOCK_RE.search("\n".join(code)):
        movable: list[tuple[int, int]] = []
        for s, e in trailing:
            text = "\n".join(code[s : e + 1])
            if not CALL_STMT_RE.match(code[s].strip()) or "import.meta" in text:
                break
            start = s  # bring the statement's leading comments along
            while start > last_block_end + 1:
                if lines[start - 1].strip() and not code[start - 1].strip():
                    start -= 1
                else:
                    break
            movable.append((start, e))
        cap = max(target - overhead, 1)
        cur: list[tuple[int, int]] = []
        cur_size = 0
        for s, e in movable:
            n_l = e - s + 1
            if cur and cur_size + n_l > cap:
                call_bins.append(cur)
                cur, cur_size = [], 0
            cur.append((s, e))
            cur_size += n_l
        if cur:
            call_bins.append(cur)

    groups = _pack(_sccs(movers, refs), max(target - overhead, 1)) if movers else []
    groups = _merge_leaf_groups([g for g in groups if g], refs)
    # A single part still helps when the barrel keeps pinned content: the file
    # shrinks by everything that moved. Without kept content it would be a rename.
    if len(groups) + len(call_bins) < 2 and not (pinned_blocks and groups):
        if not blocks:
            result["blockers"].append("no top-level declarations found — split by hand")
        elif pinned_blocks and not groups:
            result["blockers"].append(
                "every declaration is pinned to the barrel by an import.meta reference — split by hand"
            )
        else:
            result["blockers"].append(
                "every declaration is in one reference cluster — extract a seam by hand first"
            )
        return result

    # Placement: satisfy dir-check as well as loc-check.
    n_parts = len(groups) + len(call_bins)
    max_files = cfg["dir"]["max_files"]
    directory = path.parent
    current = _count_dir_files(root, directory, cfg["globs"])
    stem = path.stem
    if current + n_parts <= max_files:
        layout = "siblings"
        reason = f"{directory.relative_to(root)}/ holds {current} files, max {max_files} — room for {n_parts} more"
        paths = [directory / (stem + "-{}.ts") for _ in groups]
        call_tpl = directory / (stem + "-{}.ts")
    else:
        layout = "subdirectory"
        reason = (
            f"{directory.relative_to(root)}/ holds {current} files, max {max_files} — "
            f"no room for {n_parts} siblings, so nest them and keep {path.name} as the barrel"
        )
        paths = [directory / stem / "{}.ts" for _ in groups]
        call_tpl = directory / stem / "{}.ts"
        if n_parts > max_files:
            result["blockers"].append(f"{n_parts} parts exceed dir.max_files ({max_files}) on their own")
    call_names = [f"calls-{i + 1}" for i in range(len(call_bins))]
    call_paths = [Path(str(call_tpl).format(nm)) for nm in call_names]

    taken: set[str] = set(call_names)
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
                    if not b.exported and (
                        b.name in barrel_needs
                        or any(b.name in refs[o.name] for o in movers if owner[o.name] != idx)
                    )
                ),
            }
        )

    for i, bin_ in enumerate(call_bins):
        first_code = next((code[k].strip() for s, e in bin_ for k in range(s, e + 1)
                           if code[k].strip()), "statements")
        callee = IDENT_RE.match(first_code)
        result["groups"].append(
            {
                "name": call_names[i],
                "path": str(call_paths[i].relative_to(root)),
                "lines": sum(e - s + 1 for s, e in bin_),
                "blocks": [
                    {"name": (callee.group() if callee else "statements") + "(…)",
                     "kind": "statements",
                     "lines": sum(e - s + 1 for s, e in bin_), "exported": False}
                ],
                "imports_from_siblings": [],
                "promoted": [],
            }
        )

    result["layout"] = layout
    result["layout_reason"] = reason
    result["barrel"] = sorted({nm for b in blocks if b.exported for nm in b.all_names})
    cycle = _find_cycle(named, refs, owner)
    if cycle:
        # A cycle confined to parts holding only hoisted declarations (functions,
        # types) is harmless: nothing dereferences an import during module
        # evaluation. Anything else on the cycle keeps blocking.
        by_gname = dict(named)
        if all(
            b.kind == "function" or b.kind in TYPE_KINDS
            for gname in set(cycle) for b in by_gname[gname]
        ):
            cycle = []
    result["cycles"] = cycle
    if result["cycles"]:
        result["blockers"].append(f"reference cycle between parts: {' -> '.join(result['cycles'])}")
    if any(b.default for b in blocks):
        result["blockers"].append("file has a default export — move it by hand to keep the surface stable")
    existing = [g["path"] for g in result["groups"] if (root / g["path"]).exists()]
    if existing:
        result["blockers"].append(f"target path already exists: {', '.join(existing)}")
    moved_set = {i for bin_ in call_bins for s, e in bin_ for i in range(s, e + 1)}
    # Pinned blocks are "uncovered" on purpose: their lines stay in the barrel.
    orphans = [i for i in _orphan_lines(lines, imports, movers) if i not in moved_set]
    pinned_lines = {i for b in pinned_blocks for i in range(b.start, b.end + 1)}
    stray = [i for i in orphans if i not in pinned_lines]
    if stray:
        result["orphan_comments"] = len(stray)
    kinds = {nm: b.kind for b in blocks for nm in b.all_names}
    result["_internal"] = {"lines": lines, "imports": imports, "blocks": movers, "refs": refs,
                           "owner": owner, "named": named, "paths": paths, "orphans": orphans,
                           "code": code, "name_of": name_of, "kinds": kinds,
                           "barrel_needs": barrel_needs, "call_bins": call_bins,
                           "call_paths": call_paths}
    # Size each part from the text that would actually be written, not an estimate.
    for idx, g in enumerate(result["groups"]):
        if idx < len(named):
            g["lines"] = _render_module(idx, result).count("\n")
            if g["lines"] > limit:
                biggest = max(g["blocks"], key=lambda b: b["lines"])
                result["blockers"].append(
                    f"{g['path']} would still be {g['lines']} lines (max {limit}) — "
                    f"`{biggest['kind']} {biggest['name']}` is {biggest['lines']} lines on its own, so no "
                    f"rearranging of top-level declarations can fix this file. Extract members by hand "
                    f"(.claude/SPLITTING.md)"
                )
        else:
            g["lines"] = _render_call_part(idx - len(named), result).count("\n")
            if g["lines"] > limit:
                result["blockers"].append(
                    f"{g['path']} would still be {g['lines']} lines (max {limit}) — one statement "
                    f"block is too big on its own; split inside it by hand"
                )
    # The barrel itself must obey the limit — trailing statements and ambient
    # blocks it keeps count against it.
    barrel_size = _render_barrel(result, path).count("\n")
    result["barrel_lines"] = barrel_size
    if barrel_size > limit:
        result["blockers"].append(
            f"{result['file']} would still be {barrel_size} lines (max {limit}) as the barrel — "
            f"what it keeps (trailing statements, ambient declarations, import.meta-pinned "
            f"declarations) is too big to stay"
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
    block_by_name = {b.name: b for b in blocks}

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
        types: list[str] = []
        values: list[str] = []
        for r in sorted(grouped[other]):
            blk = block_by_name[r]
            # A destructuring block binds several names; import only the ones used here.
            used = [nm for nm in blk.all_names if re.search(rf"\b{re.escape(nm)}\b", body_text)] or [r]
            (types if blk.kind in TYPE_KINDS else values).extend(used)
        if types:
            out.append(IMPORT_TYPE_FMT % (", ".join(dict.fromkeys(types)), spec))
        if values:
            out.append(IMPORT_FMT % (", ".join(dict.fromkeys(values)), spec))
    if out:
        out.append("")

    consumed = {r for i, (_, g) in enumerate(named) if i != idx for b in g for r in refs[b.name]}
    consumed |= internal["barrel_needs"]
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
    lines, orphans, code = internal["lines"], internal["orphans"], internal["code"]
    name_of, kinds = internal["name_of"], internal["kinds"]
    first_decl = min((b.start for b in blocks), default=0)
    out: list[str] = [lines[i] for i in orphans if i < first_decl]
    if out:
        out.append("")

    # Content the barrel keeps (trailing statements, ambient blocks) may reference
    # moved declarations — a re-export does not bind locally, so import them too.
    # It may equally reference the file's original imports, so keep those; and an
    # import no part claimed (unused binding) must survive here rather than vanish.
    kept_idents: set[str] = set()
    for i in orphans:
        kept_idents.update(IDENT_RE.findall(code[i]))
    claimed: set[str] = set()
    for _, g in named:
        for b in g:
            claimed.update(IDENT_RE.findall("\n".join(code[b.start : b.end + 1])))
    for bin_ in internal.get("call_bins", []):
        for s, e in bin_:
            for k in range(s, e + 1):
                claimed.update(IDENT_RE.findall(code[k]))
    for start, end, bindings in internal["imports"]:
        if bindings and (bindings & kept_idents or not bindings & claimed):
            out.extend(lines[k] for k in range(start, end + 1))
    by_part: dict[int, tuple[list[str], list[str]]] = {}
    for ident in sorted(kept_idents):
        primary = name_of.get(ident)
        if primary is None:
            continue
        types, values = by_part.setdefault(owner[primary], ([], []))
        (types if kinds[ident] in TYPE_KINDS else values).append(ident)
    for idx in sorted(by_part):
        gname = named[idx][0]
        spec = _module_specifier(Path(str(paths[idx]).format(gname)), path)
        types, values = by_part[idx]
        if types:
            out.append(IMPORT_TYPE_FMT % (", ".join(dict.fromkeys(types)), spec))
        if values:
            out.append(IMPORT_FMT % (", ".join(dict.fromkeys(values)), spec))

    for idx, (gname, _) in enumerate(named):
        spec = _module_specifier(Path(str(paths[idx]).format(gname)), path)
        exported = [b for b in blocks if b.exported and owner[b.name] == idx]
        types = list(dict.fromkeys(nm for b in exported if b.kind in TYPE_KINDS for nm in b.all_names))
        values = list(dict.fromkeys(nm for b in exported if b.kind not in TYPE_KINDS for nm in b.all_names))
        if values:
            out.append(EXPORT_FMT % (", ".join(values), spec))
        if types:
            out.append(EXPORT_TYPE_FMT % (", ".join(types), spec))
    # Side-effect imports: the moved statement parts, in original order, after the
    # declaration parts above — so everything still runs in source order.
    for cp in internal.get("call_paths", []):
        out.append("import '%s'" % _module_specifier(cp, path))
    trailing = [lines[i] for i in orphans if i >= first_decl]
    if trailing:
        out.append("")
        out.extend(trailing)
    return "\n".join(out) + "\n"


def _render_call_part(idx: int, analysis: dict) -> str:
    """A module holding a run of moved top-level statements, imported for effect."""
    internal = analysis["_internal"]
    lines, code = internal["lines"], internal["code"]
    blocks = internal["blocks"]
    name_of, kinds, owner = internal["name_of"], internal["kinds"], internal["owner"]
    named, paths = internal["named"], internal["paths"]
    bin_ = internal["call_bins"][idx]
    my_path = internal["call_paths"][idx]

    idents: set[str] = set()
    for s, e in bin_:
        for i in range(s, e + 1):
            idents.update(IDENT_RE.findall(code[i]))

    out: list[str] = []
    for start, end, bindings in internal["imports"]:
        if not bindings or bindings & idents:
            out.extend(lines[start : end + 1])
    by_part: dict[int, tuple[list[str], list[str]]] = {}
    for ident in sorted(idents):
        primary = name_of.get(ident)
        if primary is None:
            continue
        types, values = by_part.setdefault(owner[primary], ([], []))
        (types if kinds[ident] in TYPE_KINDS else values).append(ident)
    for oidx in sorted(by_part):
        gname = named[oidx][0]
        spec = _module_specifier(Path(str(paths[oidx]).format(gname)), my_path)
        types, values = by_part[oidx]
        if types:
            out.append(IMPORT_TYPE_FMT % (", ".join(dict.fromkeys(types)), spec))
        if values:
            out.append(IMPORT_FMT % (", ".join(dict.fromkeys(values)), spec))
    if out:
        out.append("")
    for s, e in bin_:
        out.extend(lines[s : e + 1])
        out.append("")
    while out and not out[-1].strip():
        out.pop()
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
    if analysis.get("strategy") and split_members is not None:
        return split_members.apply(root, path, analysis)
    internal = analysis["_internal"]
    written = []
    for idx, (gname, _) in enumerate(internal["named"]):
        target = Path(str(internal["paths"][idx]).format(gname))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_module(idx, analysis), encoding="utf-8")
        written.append(str(target.relative_to(root)))
    for idx, target in enumerate(internal.get("call_paths", [])):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_call_part(idx, analysis), encoding="utf-8")
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
    if analysis.get("strategy") and split_members is not None:
        split_members.print_proposal(analysis)
        return
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
    if analysis.get("pinned"):
        print(f"  pinned to the barrel (import.meta is per-module): {', '.join(analysis['pinned'])}")
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
            tail = "facade" if analysis.get("strategy") else "barrel"
            print(f"[loc-fix] split {analysis['file']} into {len(written) - 1} modules + {tail}:")
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
