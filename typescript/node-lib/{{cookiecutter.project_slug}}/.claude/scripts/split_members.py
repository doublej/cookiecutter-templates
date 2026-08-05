#!/usr/bin/env python3
"""Member-level split for a file dominated by one giant declaration.

split_oversize.py groups top-level declarations; when a single class or data
literal is bigger than loc.error on its own, no regrouping can help. This
module handles that case and is imported by split_oversize.py, sharing its
CLI, opt-outs and diag logging. Proposal-first; writes happen only via --apply.

Strategy (mirrors how the oversized classes in real repos were split by hand):

- class: private instance methods become free functions taking the instance as
  a first parameter (`function foo(self: TheClass, ...)`) in part modules; the
  class stays in the original file as a facade holding fields, public methods
  and anything a line scanner cannot move. Private members the parts touch
  lose their `private` modifier (the package barrel is unchanged). File-private
  types and constants the parts reference move to `types` / `constants` parts.
- data: a `const X: T[] = [...]` array literal splits by elements into part
  arrays; the facade reassembles them with spreads under the original name and
  annotation, so element contextual typing is preserved.

What stays in the class (each is a named reason, never a silent guess):
public members, constructors, fields, decorated members, getters/setters,
statics, overload sets, `super` users, `#private` touchers, methods declaring
their own `this` scope, dynamic imports, inherited-member access on an
`extends` class, and methods referenced without a call.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

TYPE_KINDS = {"interface", "type", "enum"}
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
CONTINUES_AFTER = set("=+-*/%<>&|^?:,.(")
CONTINUES_BEFORE = set("|&?:.,+)]}")
REGEX_PRECEDERS = set("=(,:[!&|?{};+-*%<>~^")

# Emitted verbatim into TypeScript; %-formatting keeps braces out of Jinja's way.
IMPORT_FMT = "import { %s } from '%s'"
IMPORT_TYPE_FMT = "import type { %s } from '%s'"

MODIFIERS = ("public", "private", "protected", "readonly", "static", "abstract", "override", "async")
MEMBER_RE = re.compile(
    r"^(?P<mods>(?:(?:public|private|protected|readonly|static|abstract|override|async)\s+)*)"
    r"(?P<acc>(?:get|set)\s+)?(?P<star>\*\s*)?"
    r"(?P<name>#?[A-Za-z_$][\w$]*|\[[^\]]+\])"
)
ARRAY_ANNOTATION_RE = re.compile(
    r"^(?:readonly\s+)?(?P<elem>[A-Za-z_$][\w$.]*)\s*\[\s*\]$"
    r"|^Array<\s*(?P<elem2>[A-Za-z_$][\w$.]*)\s*>$"
)


# --------------------------------------------------------------------------
# Masking: same-length lines with comments/string bodies blanked to spaces.
# Template-literal interpolation stays visible because `this` lives there too.
# --------------------------------------------------------------------------


def _starts_regex(code_so_far: list[str]) -> bool:
    joined = "".join(code_so_far)
    prev = next((ch for ch in reversed(joined) if not ch.isspace()), "")
    return prev == "" or prev in REGEX_PRECEDERS


def _mask(lines: list[str]) -> tuple[list[str], list[int], list[bool]]:
    """Return (masked lines, bracket depth at line start, starts-inside-template)."""
    masked: list[str] = []
    depth_at: list[int] = []
    in_template: list[bool] = []
    stack: list[str] = []
    comment = False
    for line in lines:
        depth_at.append(sum(1 for c in stack if c != "`"))
        in_template.append(bool(stack) and stack[-1] == "`")
        out: list[str] = []
        i, n = 0, len(line)
        while i < n:
            c = line[i]
            if comment:
                if line.startswith("*/", i):
                    comment = False
                    out.append("  ")
                    i += 2
                else:
                    out.append(" ")
                    i += 1
                continue
            if stack and stack[-1] == "`":
                if c == "\\":
                    out.append("  ")
                    i += 2
                elif c == "`":
                    stack.pop()
                    out.append("`")
                    i += 1
                elif line.startswith("${", i):
                    stack.append("{")
                    out.append("${")
                    i += 2
                else:
                    out.append(" ")
                    i += 1
                continue
            if line.startswith("//", i):
                out.append(" " * (n - i))
                break
            if line.startswith("/*", i):
                comment = True
                out.append("  ")
                i += 2
                continue
            if c in "'\"":
                out.append(c)
                i += 1
                while i < n and line[i] != c:
                    step = 2 if line[i] == "\\" else 1
                    out.append(" " * step)
                    i += step
                if i < n:
                    out.append(c)
                    i += 1
                continue
            if c == "`":
                stack.append("`")
                out.append("`")
                i += 1
                continue
            if c == "/" and _starts_regex(out):
                out.append("/")
                i += 1
                in_class = False
                while i < n:
                    ch = line[i]
                    if ch == "\\":
                        out.append("  ")
                        i += 2
                        continue
                    if ch == "[":
                        in_class = True
                    elif ch == "]":
                        in_class = False
                    elif ch == "/" and not in_class:
                        out.append("/")
                        i += 1
                        break
                    out.append(" ")
                    i += 1
                continue
            if c in "{([":
                stack.append(c)
            elif c in "})]" and stack and stack[-1] != "`":
                stack.pop()
            out.append(c)
            i += 1
        text = "".join(out)
        # Escape handling at line end can overrun; clamp back to the raw length.
        masked.append(text[:n].ljust(n))
    return masked, depth_at, in_template


# --------------------------------------------------------------------------
# Class member parsing
# --------------------------------------------------------------------------


class Member:
    def __init__(self, name: str, kind: str, start: int, decl: int, end: int):
        self.name = name
        self.kind = kind  # method | field | ctor
        self.start = start  # including leading comments/decorators
        self.decl = decl
        self.end = end
        self.mods: set[str] = set()
        self.accessor = False
        self.decorated = False
        self.overloaded = False
        self.uses_this = False
        self.refs: set[str] = set()
        self.keep_reason: str | None = None
        self.stub = False  # public method extracted behind a delegating stub

    @property
    def lines(self) -> int:
        return self.end - self.start + 1

    @property
    def visible(self) -> bool:
        return not ({"private", "protected"} & self.mods)


def _member_end(start: int, masked: list[str], depth_at: list[int], body_depth: int, last: int) -> int:
    j = start
    while j < last:
        if depth_at[j + 1] > body_depth:
            j += 1
            continue
        cur = masked[j].rstrip()
        if cur and cur[-1] in CONTINUES_AFTER:
            j += 1
            continue
        nxt = masked[j + 1].strip()
        if nxt and nxt[0] in CONTINUES_BEFORE:
            j += 1
            continue
        return j
    return last


def _coalesce(members: list[Member]) -> list[Member]:
    out: list[Member] = []
    for m in members:
        if out and out[-1].name == m.name and out[-1].kind == m.kind == "method":
            prev = out[-1]
            prev.end = m.end
            prev.uses_this = prev.uses_this or m.uses_this
            prev.refs |= m.refs
            prev.overloaded = True
            continue
        out.append(m)
    return out


def _parse_members(
    lines: list[str], masked: list[str], depth_at: list[int],
    body_start: int, body_close: int, body_depth: int,
) -> list[Member]:
    members: list[Member] = []
    i = body_start
    while i < body_close:
        stripped = masked[i].strip()
        if not stripped or depth_at[i] != body_depth:
            i += 1
            continue
        end = _member_end(i, masked, depth_at, body_depth, body_close - 1)
        header = " ".join(masked[k].strip() for k in range(i, min(i + 4, end + 1)))
        m = MEMBER_RE.match(header)
        if not m:
            i = end + 1
            continue
        name = m.group("name")
        rest = header[m.end():].lstrip()
        if name == "constructor":
            kind = "ctor"
        elif rest.startswith("(") or rest.startswith("<"):
            kind = "method"
        else:
            kind = "field"
        start = i
        decorated = False
        while start > body_start:
            prev_raw = lines[start - 1].strip()
            prev_code = masked[start - 1].strip()
            if prev_raw and not prev_code:
                start -= 1
            elif prev_code.startswith("@"):
                start -= 1
                decorated = True
            else:
                break
        member = Member(name, kind, start, i, end)
        member.mods = {w for w in m.group("mods").split() if w in MODIFIERS}
        member.accessor = bool(m.group("acc")) or bool(m.group("star"))
        member.decorated = decorated
        body = "\n".join(masked[i : end + 1])
        member.uses_this = bool(re.search(r"\bthis\b", body))
        member.refs = set(re.findall(r"\bthis\s*\.\s*(#?[A-Za-z_$][\w$]*)", body))
        members.append(member)
        i = end + 1
    return _coalesce(members)


def _ctor_param_props(members: list[Member], masked: list[str]) -> dict[str, str]:
    """Parameter properties declared in the constructor: name -> visibility."""
    for m in members:
        if m.kind == "ctor":
            text = "\n".join(masked[m.decl : m.end + 1])
            return {
                name: vis
                for vis, name in re.findall(
                    r"\b(private|protected|public)\s+(?:readonly\s+)?([A-Za-z_$][\w$]*)", text
                )
            }
    return {}


def _keep_reason(m: Member, class_extends: bool, declared: set[str], class_name: str,
                 masked_body: str, taken_names: set[str], allow_public: bool = False) -> str | None:
    if m.kind != "method":
        return "field" if m.kind == "field" else "constructor"
    if m.decorated:
        return "decorated"
    if m.accessor:
        return "getter/setter/generator"
    if m.overloaded:
        return "overload set"
    if "static" in m.mods:
        return "static"
    if m.name.startswith("#") or m.name.startswith("["):
        return "#private or computed name"
    if m.visible and not allow_public:
        return "public API"
    if re.search(r"\bsuper\b", masked_body):
        return "uses super"
    if re.search(r"\b(function|class)\b", masked_body) and m.uses_this:
        return "declares its own `this` scope"
    if re.search(r"new\s*\.\s*target|\barguments\b", masked_body):
        return "uses new.target/arguments"
    if re.search(r"\bself\b", masked_body):
        return "already uses the identifier `self`"
    if re.search(r"\.\s*#", masked_body):
        return "touches a #private field"
    if re.search(r"\b%s\b" % re.escape(class_name), masked_body):
        return "references the class itself"
    if re.search(r"\bimport\s*\(", masked_body):
        return "contains a dynamic import"
    if "import.meta" in masked_body:
        return "references import.meta (per-module — its meaning changes in a moved file)"
    if m.name in taken_names:
        return "name already taken at module scope"
    if class_extends:
        for r in sorted(m.refs):
            if r not in declared:
                return "touches inherited member `%s`" % r
    return None


def _split_params(text: str) -> list[str]:
    parts: list[str] = []
    depth = angle = 0
    cur: list[str] = []
    for i, c in enumerate(text):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "<":
            angle += 1
        elif c == ">" and angle and text[i - 1] != "=":
            angle -= 1
        elif c == "," and depth == 0 and angle == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    if cur:
        parts.append("".join(cur))
    return parts


def _stub_plan(member: Member, lines: list[str], masked: list[str]) -> tuple[list[str], list[str]] | None:
    """(signature lines, forwarded argument names) when the method body can be
    replaced by `return name(this, ...args)` — every parameter must be a plain
    (optionally rest/optional/defaulted) identifier so the stub can forward it."""
    sig_end = None
    for k in range(member.decl, member.end + 1):
        if masked[k].rstrip().endswith("{"):
            sig_end = k
            break
    if sig_end is None:
        return None
    sig_mask = "\n".join(masked[member.decl : sig_end + 1])
    stripped = sig_mask.lstrip()
    mm = MEMBER_RE.match(stripped)
    if not mm:
        return None
    offset = len(sig_mask) - len(stripped)
    paren = _param_paren(sig_mask, offset + mm.end("name"))
    if paren is None:
        return None
    depth, close = 0, None
    for i in range(paren, len(sig_mask)):
        c = sig_mask[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                close = i
                break
    if close is None:
        return None
    params = sig_mask[paren + 1 : close]
    ret = sig_mask[close + 1 :]
    if re.search(r"\bthis\b", params) or re.search(r"\bthis\b", ret):
        return None  # this-typed parameter or `this` in the return type
    args: list[str] = []
    for p in _split_params(params):
        p = p.strip()
        if not p:
            continue
        if p[0] in "{[":
            return None  # destructured parameter — no single name to forward
        pm = re.match(r"^(\.\.\.)?\s*([A-Za-z_$][\w$]*)", p)
        if not pm:
            return None
        args.append((pm.group(1) or "") + pm.group(2))
    return [lines[k] for k in range(member.decl, sig_end + 1)], args


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------


def _kebab(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "part"


def _unique(base: str, taken: set[str]) -> str:
    name, i = base, 2
    while name in taken:
        name = "%s-%d" % (base, i)
        i += 1
    taken.add(name)
    return name


def _group_methods(extractable: list[Member], cap: int) -> list[list[Member]]:
    """Connected components by this-references, packed into source-order bins.

    Parts may import each other's functions — even cyclically. That is safe
    here (and only here) because every part contains nothing but hoisted
    function declarations: the imports are used at call time, never during
    module evaluation.
    """
    names = {m.name for m in extractable}
    parent = {m.name: m.name for m in extractable}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for m in extractable:
        for r in m.refs & names:
            ra, rb = find(m.name), find(r)
            if ra != rb:
                parent[ra] = rb
    comps: dict[str, list[Member]] = {}
    for m in extractable:
        comps.setdefault(find(m.name), []).append(m)
    ordered = sorted(comps.values(), key=lambda g: min(m.start for m in g))

    parts: list[list[Member]] = []
    bin_: list[Member] = []
    size = 0
    for comp in ordered:
        comp = sorted(comp, key=lambda m: m.start)
        chunks: list[list[Member]]
        if sum(m.lines + 1 for m in comp) > cap:
            chunks = []
            cur: list[Member] = []
            cur_size = 0
            for m in comp:
                if cur and cur_size + m.lines + 1 > cap:
                    chunks.append(cur)
                    cur, cur_size = [], 0
                cur.append(m)
                cur_size += m.lines + 1
            if cur:
                chunks.append(cur)
        else:
            chunks = [comp]
        for chunk in chunks:
            chunk_size = sum(m.lines + 1 for m in chunk)
            if bin_ and size + chunk_size > cap:
                parts.append(bin_)
                bin_, size = [], 0
            bin_.extend(chunk)
            size += chunk_size
    if bin_:
        parts.append(bin_)
    return [sorted(p, key=lambda m: m.start) for p in parts]


# --------------------------------------------------------------------------
# Rewriting
# --------------------------------------------------------------------------


def _splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, repl in sorted(edits, reverse=True):
        text = text[:start] + repl + text[end:]
    return text


def _rewrite_line(raw: str, mask: str, extracted: dict[str, bool], receiver: str) -> str:
    """Turn `this.foo(` into `foo(receiver, ` for extracted methods; when the
    receiver is `self`, also turn every remaining `this` into `self`."""
    if extracted:
        call_re = re.compile(r"\bthis\s*\.\s*(%s)\s*\(" % "|".join(map(re.escape, extracted)))
        edits = []
        for m in call_re.finditer(mask):
            takes = extracted[m.group(1)]
            edits.append((m.start(), m.end(), "%s(%s" % (m.group(1), (receiver + ", ") if takes else "")))
        raw = _splice(raw, edits)
        mask = _splice(mask, edits)
    if receiver == "self":
        edits = [(m.start(), m.end(), "self") for m in re.finditer(r"\bthis\b", mask)]
        raw = _splice(raw, edits)
    raw = raw.replace("(self, )", "(self)").replace("(this, )", "(this)")
    return raw.rstrip()


def _adjust_relative_imports(line: str, src_dir: Path, dest_dir: Path) -> str:
    """Repoint ./ and ../ specifiers when a copied import lands in another directory.

    Parts only ever land one directory below the original file, so the rewrite is
    a single `../` prefix — which also keeps the original path segments intact."""
    if src_dir.resolve() == dest_dir.resolve():
        return line

    def fix(m: re.Match) -> str:
        quote, spec = m.group(1), m.group(2)
        if dest_dir.resolve().parent == src_dir.resolve():
            new = "../" + (spec[2:] if spec.startswith("./") else spec)
        else:  # unexpected layout: fall back to a canonical relative path
            target = (src_dir / spec).resolve()
            new = os.path.relpath(target, dest_dir.resolve()).replace(os.sep, "/")
            if not new.startswith("."):
                new = "./" + new
        return "%s%s%s" % (quote, new, quote)

    return re.sub(r"(['\"])(\.\.?/[^'\"]*)\1", fix, line)


def _dedent(text_lines: list[str], indent: int, protected: list[bool]) -> list[str]:
    pad = " " * indent
    out = []
    for line, prot in zip(text_lines, protected):
        if not prot and line.startswith(pad):
            out.append(line[indent:])
        else:
            out.append(line)
    return out


def _param_paren(decl: str, scan_from: int) -> int | None:
    """Index of the '(' opening the parameter list, skipping generics."""
    angle = 0
    for i in range(scan_from, len(decl)):
        c = decl[i]
        if c == "<":
            angle += 1
        elif c == ">" and angle and decl[i - 1] != "=":
            angle -= 1
        elif c == "(" and angle == 0:
            return i
    return None


def _emit_function(
    lines: list[str], masked: list[str], in_template: list[bool], member: Member,
    class_name: str, extracted: dict[str, bool],
) -> list[str]:
    seg_raw = list(lines[member.start : member.end + 1])
    seg_mask = list(masked[member.start : member.end + 1])
    seg_tpl = list(in_template[member.start : member.end + 1])
    decl_idx = member.decl - member.start

    # Header geometry, computed before rewrites can shift anything after the name.
    decl_mask = seg_mask[decl_idx]
    indent = len(decl_mask) - len(decl_mask.lstrip())
    mm = MEMBER_RE.match(decl_mask[indent:])
    name_start = indent + (mm.start("name") if mm else 0)
    name_len = (mm.end("name") - mm.start("name")) if mm else len(member.name)

    for k in range(decl_idx, len(seg_raw)):
        seg_raw[k] = _rewrite_line(seg_raw[k], seg_mask[k], extracted, "self")

    decl = seg_raw[decl_idx]
    tail = decl[name_start:]
    prefix = "export " + ("async " if "async" in member.mods else "") + "function "
    decl = " " * indent + prefix + tail

    insert_self_line = False
    if member.uses_this:
        paren = _param_paren(decl, indent + len(prefix) + name_len)
        if paren is not None:
            after = decl[paren + 1 :]
            if not after.strip():
                insert_self_line = True
            elif after.lstrip().startswith(")"):
                decl = decl[: paren + 1] + "self: " + class_name + after
            else:
                decl = decl[: paren + 1] + "self: " + class_name + ", " + after
    seg_raw[decl_idx] = decl

    out = _dedent(seg_raw, indent, seg_tpl)
    if insert_self_line:
        out.insert(decl_idx + 1, "  self: " + class_name + ",")
    return [line.rstrip() for line in out]


# --------------------------------------------------------------------------
# Placement (mirrors split_oversize's sibling/subdirectory choice)
# --------------------------------------------------------------------------


def _module_specifier(module_path: Path, from_path: Path) -> str:
    rel = os.path.relpath(module_path.with_suffix(".js"), from_path.parent)
    rel = rel.replace(os.sep, "/")
    return rel if rel.startswith(".") else "./" + rel


def _count_dir_files(root: Path, directory: Path, globs: list[str]) -> int:
    matched = set()
    for g in globs:
        for p in root.glob(g):
            if p.is_file() and p.parent == directory:
                matched.add(p)
    return len(matched)


def _placement(root: Path, path: Path, cfg: dict, n_parts: int, result: dict) -> list[Path]:
    max_files = cfg["dir"]["max_files"]
    directory = path.parent
    current = _count_dir_files(root, directory, cfg["globs"])
    stem = path.stem
    if current + n_parts <= max_files:
        result["layout"] = "siblings"
        result["layout_reason"] = "%s/ holds %d files, max %d — room for %d more" % (
            directory.relative_to(root), current, max_files, n_parts)
        return [directory / (stem + "-%s.ts") for _ in range(n_parts)]
    result["layout"] = "subdirectory"
    result["layout_reason"] = (
        "%s/ holds %d files, max %d — no room for %d siblings, so nest them under %s/ and "
        "keep %s as the facade" % (
            directory.relative_to(root), current, max_files, n_parts, stem, path.name)
    )
    if n_parts > max_files:
        result["blockers"].append("%d parts exceed dir.max_files (%d) on their own" % (n_parts, max_files))
    return [directory / stem / "%s.ts" for _ in range(n_parts)]


# --------------------------------------------------------------------------
# Analysis: entry + class
# --------------------------------------------------------------------------


def analyze(root: Path, path: Path, cfg: dict, lines: list[str],
            imports: list, blocks: list, giant) -> dict:
    limit = cfg["loc"]["error"]
    target = cfg["loc"].get("warn", limit)
    result: dict = {
        "file": str(path.relative_to(root)),
        "lines": len(lines),
        "limit": limit,
        "strategy": "members",
        "giant": {"name": giant.name, "kind": giant.kind, "lines": giant.lines},
        "blockers": [],
        "groups": [],
        "barrel": sorted({b.name for b in blocks if b.exported}),
    }
    if giant.kind == "class":
        return _analyze_class(root, path, cfg, lines, imports, blocks, giant, result, limit, target)
    if giant.is_data:
        result["strategy"] = "data"
        return _analyze_data(root, path, cfg, lines, imports, blocks, giant, result, limit, target)
    result["blockers"].append(
        "%s would still be over %d lines — `%s %s` is %d lines on its own and is neither a "
        "class nor a data literal; restructure by hand (.claude/SPLITTING.md)"
        % (result["file"], limit, giant.kind, giant.name, giant.lines)
    )
    return result


def _analyze_class(root, path, cfg, lines, imports, blocks, giant, result, limit, target) -> dict:
    masked, depth_at, in_template = _mask(lines)
    class_depth = depth_at[giant.decl]
    body_depth = class_depth + 1
    header_end = next(
        (h for h in range(giant.decl, giant.end) if depth_at[h + 1] > class_depth), None
    )
    if header_end is None or masked[giant.end].strip() != "}":
        result["blockers"].append(
            "could not find the class body boundaries of `%s` — split by hand" % giant.name
        )
        return result
    class_extends = bool(re.search(r"\bextends\b", " ".join(masked[giant.decl : header_end + 1])))

    members = _parse_members(lines, masked, depth_at, header_end + 1, giant.end, body_depth)
    param_props = _ctor_param_props(members, masked)
    declared = {m.name for m in members} | set(param_props)
    import_bound = set().union(*(b[2] for b in imports)) if imports else set()
    taken = {b.name for b in blocks if b is not giant} | import_bound | {giant.name}

    def attempt(allow_public: bool) -> dict:
        res: dict = {**result, "blockers": list(result["blockers"]), "groups": []}
        for m in members:
            m.stub = False
            body = "\n".join(masked[m.decl : m.end + 1])
            m.keep_reason = _keep_reason(m, class_extends, declared, giant.name, body, taken,
                                         allow_public)
        stub_plans: dict[int, tuple[list[str], list[str]]] = {}
        if allow_public:
            for m in members:
                if m.kind == "method" and m.visible and m.keep_reason is None:
                    plan = _stub_plan(m, lines, masked)
                    if plan is None:
                        m.keep_reason = "public API with parameters a stub cannot forward"
                    else:
                        m.stub = True
                        stub_plans[id(m)] = plan

        # A name is pinned when some member references it other than as a direct call,
        # or calls it from inside a nested `this` scope the rewrite cannot see through.
        class_mask = "\n".join(masked[giant.decl : giant.end + 1])
        pinned: dict[str, str] = {}
        for m in members:
            if m.keep_reason is None and not m.stub and re.search(
                r"\bthis\s*\.\s*%s\b(?!\s*\()" % re.escape(m.name), class_mask
            ):
                pinned[m.name] = "referenced without a call"
        for m in members:
            body = "\n".join(masked[m.decl : m.end + 1])
            if m.uses_this and re.search(r"\b(function|class)\b", body):
                for r in m.refs:
                    pinned.setdefault(r, "called from a nested `this` scope in %s" % m.name)
        # Stubbed members are immune to pinning: the property stays on the
        # class, so un-called references and nested-`this` calls still resolve.
        for m in members:
            if m.keep_reason is None and not m.stub and m.name in pinned:
                m.keep_reason = pinned[m.name]

        extractable = [m for m in members if m.keep_reason is None]
        if not extractable:
            reasons = sorted({m.keep_reason for m in members if m.kind == "method" and m.keep_reason})
            res["blockers"].append(
                "%s would still be %d lines (max %d) — `%s %s` is %d lines and none of its members "
                "can be extracted safely (%s). Split it by hand (.claude/SPLITTING.md)"
                % (res["file"], res["lines"], limit, giant.kind, giant.name, giant.lines,
                   "; ".join(reasons) or "no methods found")
            )
            return res

        takes_self = {m.name: m.uses_this for m in extractable}

        # Widen kept private/protected members the parts touch.
        kept = [m for m in members if m.keep_reason is not None]
        kept_by_name = {m.name: m for m in kept}
        widen: set[str] = set()
        for m in extractable:
            for r in m.refs:
                k = kept_by_name.get(r)
                if k is not None and not k.visible:
                    widen.add(r)
                elif k is None and param_props.get(r, "public") != "public":
                    widen.add(r)

        # File-private types/constants the parts need move to support parts; other
        # needed blocks are promoted (exported from the facade, absent from the barrel).
        part_idents = set()
        for m in extractable:
            part_idents.update(IDENT_RE.findall("\n".join(masked[m.start : m.end + 1])))
        needed_top = [b for b in blocks if b is not giant and b.name in part_idents]

        def _has_meta(b) -> bool:  # import.meta is per-module; such blocks must not move
            return "import.meta" in "\n".join(masked[b.start : b.end + 1])

        movable_types = [b for b in needed_top
                         if b.kind in TYPE_KINDS and not b.exported and not _has_meta(b)]
        const_candidates = [b for b in needed_top
                            if b.is_data and not b.exported and not _has_meta(b)]
        movable_set = {b.name for b in movable_types} | {b.name for b in const_candidates}
        facade_resident = {b.name for b in blocks if b is not giant} - movable_set
        movable_consts, promoted = [], []
        for b in const_candidates:
            init_idents = set(IDENT_RE.findall("\n".join(masked[b.start : b.end + 1]))) - {b.name}
            if init_idents & facade_resident:
                promoted.append(b)  # initializer runs at import time; keep it in the facade
            else:
                movable_consts.append(b)
        promoted += [b for b in needed_top if not b.exported
                     and b not in movable_types and b not in movable_consts and b not in promoted]

        overhead = sum(end - start + 1 for start, end, _ in imports) + 8
        cap = max(target - overhead, 20)

        def build_named(method_groups: list[list[Member]], merge_support: bool) -> list[tuple[str, str, list]]:
            taken_names: set[str] = set()
            built: list[tuple[str, str, list]] = []
            if merge_support:
                if movable_types or movable_consts:
                    built.append((_unique("support", taken_names), "support", movable_types + movable_consts))
            else:
                if movable_types:
                    built.append((_unique("types", taken_names), "support", movable_types))
                if movable_consts:
                    built.append((_unique("constants", taken_names), "support", movable_consts))
            for g in method_groups:
                built.append((_unique(_kebab(g[0].name), taken_names), "methods", g))
            return built

        # Fewer, fuller parts when the file count would break dir-check on its own.
        max_files = cfg["dir"]["max_files"]
        named = build_named(_group_methods(extractable, cap), False)
        if len(named) > max_files:
            named = build_named(_group_methods(extractable, cap), True)
        if len(named) > max_files:
            big_cap = max(limit - overhead - 8, cap)
            named = build_named(_group_methods(extractable, big_cap), True)

        path_templates = _placement(root, path, cfg, len(named), res)
        part_paths = [Path(str(path_templates[i]) % name) for i, (name, _, _) in enumerate(named)]
        existing = [p for p in part_paths if p.exists()]
        if existing:
            res["blockers"].append(
                "target path already exists: %s" % ", ".join(str(p.relative_to(root)) for p in existing)
            )

        owner: dict[str, int] = {}
        for idx, (_, _, payload) in enumerate(named):
            for item in payload:
                owner[item.name] = idx

        internal = {
            "lines": lines, "masked": masked, "in_template": in_template,
            "imports": imports, "blocks": blocks, "giant": giant,
            "members": members, "extractable": extractable, "kept": kept,
            "takes_self": takes_self, "widen": widen, "param_props": param_props,
            "moved_types": movable_types, "moved_consts": movable_consts,
            "promoted": promoted, "named": named, "paths": part_paths, "owner": owner,
            "header_end": header_end, "class_name": giant.name,
            "facade_path": path, "src_dir": path.parent, "stub_plans": stub_plans,
        }
        res["_internal"] = internal
        res["widened"] = sorted(widen)
        res["promoted"] = sorted(b.name for b in promoted)
        res["stubbed"] = sorted(m.name for m in extractable if m.stub)
        res["kept"] = [
            {"name": m.name, "reason": m.keep_reason} for m in kept if m.kind == "method"
        ]

        for idx, (name, _, payload) in enumerate(named):
            text = _render_part(idx, internal)
            n_lines = text.count("\n")
            res["groups"].append({
                "name": name,
                "path": str(part_paths[idx].relative_to(root)),
                "lines": n_lines,
                "blocks": [
                    {"name": item.name, "kind": getattr(item, "kind", "method"),
                     "lines": item.lines, "exported": False}
                    for item in payload
                ],
                "imports_from_siblings": sorted(
                    r for item in payload for r in getattr(item, "refs", set())
                    if r in owner and owner[r] != idx
                ),
            })
            if n_lines > limit:
                biggest = max(payload, key=lambda item: item.lines)
                res["blockers"].append(
                    "%s would still be %d lines (max %d) — `%s` is %d lines on its own; split "
                    "that member by hand first (.claude/SPLITTING.md)"
                    % (part_paths[idx].relative_to(root), n_lines, limit, biggest.name, biggest.lines)
                )

        facade_lines = _render_facade(internal, path).count("\n")
        res["facade"] = {"path": res["file"], "lines": facade_lines}
        if facade_lines > limit:
            res["blockers"].append(
                "%s would still be %d lines (max %d) after extraction — what remains is public API "
                "and members a line scanner cannot move; restructure by hand (.claude/SPLITTING.md)"
                % (res["file"], facade_lines, limit)
            )
        return res

    first = attempt(False)
    if first["blockers"] and any("after extraction" in b or "public API" in b for b in first["blockers"]):
        # The facade is what is too big: public method bodies can still move behind
        # thin delegating stubs, which keep the class type surface identical.
        second = attempt(True)
        if not second["blockers"]:
            return second
    return first


# --------------------------------------------------------------------------
# Rendering: class parts + facade
# --------------------------------------------------------------------------


def _copied_imports(internal: dict, idents: set[str], dest: Path) -> list[str]:
    lines = internal["lines"]
    out: list[str] = []
    for start, end, bindings in internal["imports"]:
        if not bindings or bindings & idents:
            for line in lines[start : end + 1]:
                out.append(_adjust_relative_imports(line, internal["src_dir"], dest.parent))
    return out


def _part_local_imports(internal: dict, idents: set[str], needs_self: bool,
                        my_path: Path, idx: int) -> list[str]:
    """Imports from the facade, support parts and sibling method parts."""
    owner = internal["owner"]
    class_name = internal["class_name"]
    out: list[str] = []

    facade_spec = _module_specifier(internal["facade_path"], my_path)
    facade_types = [class_name] if (needs_self or class_name in idents) else []
    facade_values: list[str] = []
    for b in internal["blocks"]:
        if b is internal["giant"] or b.name not in idents or b.name in owner:
            continue
        (facade_types if b.kind in TYPE_KINDS else facade_values).append(b.name)
    if facade_types:
        out.append(IMPORT_TYPE_FMT % (", ".join(dict.fromkeys(facade_types)), facade_spec))
    if facade_values:
        out.append(IMPORT_FMT % (", ".join(sorted(set(facade_values))), facade_spec))

    by_part: dict[int, dict[str, set[str]]] = {}
    for oname, oidx in owner.items():
        if oidx == idx or oname not in idents:
            continue
        _, okind, opayload = internal["named"][oidx]
        slot = by_part.setdefault(oidx, {"types": set(), "values": set()})
        if okind == "support":
            blk = next(b for b in opayload if b.name == oname)
            (slot["types"] if blk.kind in TYPE_KINDS else slot["values"]).add(oname)
        else:
            slot["values"].add(oname)
    for oidx in sorted(by_part):
        spec = _module_specifier(internal["paths"][oidx], my_path)
        if by_part[oidx]["types"]:
            out.append(IMPORT_TYPE_FMT % (", ".join(sorted(by_part[oidx]["types"])), spec))
        if by_part[oidx]["values"]:
            out.append(IMPORT_FMT % (", ".join(sorted(by_part[oidx]["values"])), spec))
    return out


def _render_part(idx: int, internal: dict) -> str:
    lines, masked, in_template = internal["lines"], internal["masked"], internal["in_template"]
    name, kind, payload = internal["named"][idx]
    my_path = internal["paths"][idx]
    takes_self = internal["takes_self"]

    idents: set[str] = set()
    for item in payload:
        idents.update(IDENT_RE.findall("\n".join(masked[item.start : item.end + 1])))

    if kind == "support":
        chunks = []
        for b in payload:
            chunk = list(lines[b.start : b.end + 1])
            if not b.exported:
                off = b.decl - b.start
                chunk[off] = "export " + chunk[off]
            chunks.append([line.rstrip() for line in chunk])
        needs_self = False
    else:
        extracted = dict(takes_self)
        chunks = [
            _emit_function(lines, masked, in_template, m, internal["class_name"], extracted)
            for m in payload
        ]
        needs_self = any(m.uses_this for m in payload)

    out = _copied_imports(internal, idents, my_path)
    out.extend(_part_local_imports(internal, idents, needs_self, my_path, idx))
    if out:
        out.append("")
    for c in chunks:
        out.extend(c)
        out.append("")
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def _first_code_line(masked: list[str]) -> int:
    for i, line in enumerate(masked):
        if line.strip():
            return i
    return 0


def _render_facade(internal: dict, path: Path) -> str:
    lines, masked = internal["lines"], internal["masked"]
    giant = internal["giant"]
    owner = internal["owner"]
    widen = internal["widen"]
    # Calls to stubbed methods stay as `this.foo(...)` — the stub delegates, so
    # no rewrite is needed (or safe: nested `this` scopes may call them too).
    stub_names = {m.name for m in internal["extractable"] if m.stub}
    extracted = {k: v for k, v in internal["takes_self"].items() if k not in stub_names}
    moved_ranges = [(b.start, b.end) for b in internal["moved_types"] + internal["moved_consts"]]
    promoted_decls = {b.decl for b in internal["promoted"]}

    kept_mask = "\n".join("\n".join(masked[m.start : m.end + 1]) for m in internal["kept"])
    outside_mask = "\n".join(
        masked[i] for i in range(len(lines))
        if not (giant.start <= i <= giant.end) and not any(s <= i <= e for s, e in moved_ranges)
    )
    facade_idents = set(IDENT_RE.findall(kept_mask + "\n" + outside_mask))
    if extracted:
        facade_calls = set(re.findall(
            r"\bthis\s*\.\s*(%s)\s*\(" % "|".join(map(re.escape, extracted)), kept_mask))
    else:
        facade_calls = set()

    new_imports: list[str] = []
    by_part: dict[int, dict[str, set[str]]] = {}
    for oname, oidx in owner.items():
        _, okind, opayload = internal["named"][oidx]
        if okind == "support":
            if oname in facade_idents:
                blk = next(b for b in opayload if b.name == oname)
                slot = by_part.setdefault(oidx, {"types": set(), "values": set()})
                (slot["types"] if blk.kind in TYPE_KINDS else slot["values"]).add(oname)
        elif oname in facade_calls or oname in stub_names:
            by_part.setdefault(oidx, {"types": set(), "values": set()})["values"].add(oname)
    for oidx in sorted(by_part):
        spec = _module_specifier(internal["paths"][oidx], path)
        if by_part[oidx]["types"]:
            new_imports.append(IMPORT_TYPE_FMT % (", ".join(sorted(by_part[oidx]["types"])), spec))
        if by_part[oidx]["values"]:
            new_imports.append(IMPORT_FMT % (", ".join(sorted(by_part[oidx]["values"])), spec))

    imports = internal["imports"]
    insert_at = imports[-1][1] + 1 if imports else _first_code_line(masked)

    out: list[str] = []
    i = 0
    while i < len(lines):
        if i == insert_at and new_imports:
            out.extend(new_imports)
            new_imports = []
        if any(s <= i <= e for s, e in moved_ranges):
            i += 1
            continue
        if giant.start <= i <= giant.end:
            out.extend(_render_facade_class(internal, extracted, widen))
            i = giant.end + 1
            continue
        line = lines[i]
        if i in promoted_decls:
            line = "export " + line
        out.append(line.rstrip())
        i += 1
    if new_imports:
        out.extend(new_imports)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return text.rstrip("\n") + "\n"


def _emit_stub(member: Member, plan: tuple[list[str], list[str]], takes_self: bool) -> list[str]:
    """The original signature with the body replaced by a delegating call —
    the class type surface is unchanged, the real body lives in a part."""
    sig_lines, args = plan
    out = [line.rstrip() for line in sig_lines]
    indent = len(sig_lines[0]) - len(sig_lines[0].lstrip())
    recv = ["this"] if takes_self else []
    out.append(" " * (indent + 2) + "return %s(%s)" % (member.name, ", ".join(recv + args)))
    out.append(" " * indent + "}")
    return out


def _render_facade_class(internal: dict, extracted: dict[str, bool], widen: set[str]) -> list[str]:
    lines, masked = internal["lines"], internal["masked"]
    giant = internal["giant"]
    header_end = internal["header_end"]
    param_props = internal["param_props"]
    kept_ids = {id(m) for m in internal["kept"]}
    stub_plans = internal["stub_plans"]
    takes_self = internal["takes_self"]

    covered: dict[int, Member] = {}
    for m in internal["members"]:
        for k in range(m.start, m.end + 1):
            covered[k] = m

    out = [lines[k].rstrip() for k in range(giant.start, header_end + 1)]
    i = header_end + 1
    while i < giant.end:
        m = covered.get(i)
        if m is None:
            out.append(lines[i].rstrip())
            i += 1
            continue
        if id(m) not in kept_ids:
            plan = stub_plans.get(id(m))
            if plan is not None:
                out.extend(lines[k].rstrip() for k in range(m.start, m.decl))
                out.extend(_emit_stub(m, plan, takes_self[m.name]))
                i = m.end + 1
                continue  # keep the blank line that follows
            i = m.end + 1
            while i < giant.end and not lines[i].strip():
                i += 1
            continue
        for k in range(m.start, m.end + 1):
            line = _rewrite_line(lines[k], masked[k], extracted, "this")
            if k == m.decl and m.name in widen:
                line = re.sub(r"^(\s*)(?:private|protected)\s+", r"\1", line)
            if m.kind == "ctor":
                for name in widen & set(param_props):
                    line = re.sub(
                        r"\b(?:private|protected)(\s+readonly)?(\s+%s\b)" % re.escape(name),
                        r"public\1\2", line,
                    )
            out.append(line)
        i = m.end + 1
    while out and not out[-1].strip():
        out.pop()
    out.append(lines[giant.end].rstrip())
    return out


# --------------------------------------------------------------------------
# Analysis + rendering: data literal
# --------------------------------------------------------------------------


def _parse_elements(masked: list[str], decl: int, end: int, open_col: int):
    """Line ranges of the array's top-level elements; None when the literal is
    not line-separable (elements sharing lines with brackets or each other)."""
    if masked[decl][open_col + 1 :].strip():
        return None, end
    elements: list[tuple[int, int]] = []
    depth = 1
    el_start: int | None = None
    for i in range(decl + 1, end + 1):
        line = masked[i]
        for j, c in enumerate(line):
            if c.isspace():
                continue
            if depth == 1 and el_start is None and c not in "]}),":
                el_start = i
            if c in "[{(":
                depth += 1
            elif c in "]})":
                depth -= 1
                if depth == 0:
                    if line[:j].strip():
                        return None, i
                    if el_start is not None:
                        elements.append((el_start, i - 1))
                    return elements, i
            elif c == "," and depth == 1:
                if el_start is None or line[j + 1 :].strip():
                    return None, i
                elements.append((el_start, i))
                el_start = None
    return None, end


def _analyze_data(root, path, cfg, lines, imports, blocks, giant, result, limit, target) -> dict:
    masked, _, _ = _mask(lines)
    if "import.meta" in "\n".join(masked[giant.decl : giant.end + 1]):
        result["blockers"].append(
            "`const %s` references import.meta — per-module meaning would change in moved "
            "element files; split by hand" % giant.name
        )
        return result
    decl_mask = masked[giant.decl]
    eq = decl_mask.find("=")
    open_col, open_char = None, None
    if eq != -1:
        for j in range(eq + 1, len(decl_mask)):
            if not decl_mask[j].isspace():
                open_col, open_char = j, decl_mask[j]
                break
    if open_char != "[":
        result["blockers"].append(
            "`const %s` is a %d-line %s literal — only an array literal can be split without "
            "losing field-level contextual types; split by hand (.claude/SPLITTING.md)"
            % (giant.name, giant.lines, "object" if open_char == "{" else "non-array")
        )
        return result

    colon = decl_mask.find(":", 0, eq)
    annotation = decl_mask[colon + 1 : eq].strip() if colon != -1 else ""
    am = ARRAY_ANNOTATION_RE.match(annotation) if annotation else None
    if not am:
        result["blockers"].append(
            "`const %s` lacks a `T[]` annotation — un-annotated parts would re-infer element "
            "types (literal unions widen to string/number); annotate it, then re-run"
            % giant.name
        )
        return result
    elem_type = am.group("elem") or am.group("elem2")

    elements, _ = _parse_elements(masked, giant.decl, giant.end, open_col)
    if elements is None:
        result["blockers"].append(
            "`const %s` has elements that share lines with brackets or each other — one "
            "element per line range is required for a mechanical split" % giant.name
        )
        return result
    if len(elements) < 2:
        result["blockers"].append("`const %s` has a single element — nothing to split" % giant.name)
        return result

    overhead = sum(end - start + 1 for start, end, _ in imports) + 6
    cap = max(target - overhead, 20)
    bins: list[list[tuple[int, int]]] = []
    cur: list[tuple[int, int]] = []
    size = 0
    for el in elements:
        el_lines = el[1] - el[0] + 1
        if cur and size + el_lines > cap:
            bins.append(cur)
            cur, size = [], 0
        cur.append(el)
        size += el_lines
    if cur:
        bins.append(cur)
    if len(bins) < 2:
        mid = len(elements) // 2
        bins = [elements[:mid], elements[mid:]]

    part_names = ["data-%d" % (i + 1) for i in range(len(bins))]
    path_templates = _placement(root, path, cfg, len(bins), result)
    part_paths = [Path(str(path_templates[i]) % part_names[i]) for i in range(len(bins))]
    existing = [p for p in part_paths if p.exists()]
    if existing:
        result["blockers"].append(
            "target path already exists: %s" % ", ".join(str(p.relative_to(root)) for p in existing)
        )

    const_names = ["%s_%d" % (giant.name, i + 1) for i in range(len(bins))]
    internal = {
        "lines": lines, "masked": masked, "imports": imports, "blocks": blocks,
        "giant": giant, "bins": bins, "paths": part_paths, "const_names": const_names,
        "elem_type": elem_type, "annotation": annotation,
        "facade_path": path, "src_dir": path.parent,
    }
    result["_internal"] = internal

    for i, bin_ in enumerate(bins):
        text = _render_data_part(i, internal)
        n_lines = text.count("\n")
        result["groups"].append({
            "name": part_names[i],
            "path": str(part_paths[i].relative_to(root)),
            "lines": n_lines,
            "blocks": [{"name": const_names[i], "kind": "const",
                        "lines": n_lines, "exported": False}],
            "imports_from_siblings": [],
        })
        if n_lines > limit:
            biggest = max(bin_, key=lambda el: el[1] - el[0])
            result["blockers"].append(
                "%s would still be %d lines (max %d) — one element spans %d lines; split that "
                "element by hand first" % (part_paths[i].relative_to(root), n_lines, limit,
                                           biggest[1] - biggest[0] + 1)
            )

    facade_lines = _render_data_facade(internal, path).count("\n")
    result["facade"] = {"path": result["file"], "lines": facade_lines}
    if facade_lines > limit:
        result["blockers"].append(
            "%s would still be %d lines (max %d) after moving the data out — re-run for the rest"
            % (result["file"], facade_lines, limit)
        )
    return result


def _render_data_part(idx: int, internal: dict) -> str:
    lines, masked = internal["lines"], internal["masked"]
    bin_ = internal["bins"][idx]
    my_path = internal["paths"][idx]
    annotation = internal["annotation"]
    const_name = internal["const_names"][idx]

    body_lines: list[str] = []
    idents: set[str] = set(IDENT_RE.findall(annotation))
    for start, end in bin_:
        body_lines.extend(lines[k] for k in range(start, end + 1))
        idents.update(IDENT_RE.findall("\n".join(masked[k] for k in range(start, end + 1))))
    if body_lines and not body_lines[-1].rstrip().endswith(","):
        body_lines[-1] = body_lines[-1].rstrip() + ","

    out = _copied_imports(internal, idents, my_path)
    root_type = internal["elem_type"].split(".")[0]
    if any(b.name == root_type and b.kind in TYPE_KINDS for b in internal["blocks"]):
        spec = _module_specifier(internal["facade_path"], my_path)
        out.append(IMPORT_TYPE_FMT % (root_type, spec))
    if out:
        out.append("")
    out.append("export const %s: %s = [" % (const_name, annotation))
    out.extend(line.rstrip() for line in body_lines)
    out.append("]")
    return "\n".join(out) + "\n"


def _render_data_facade(internal: dict, path: Path) -> str:
    lines = internal["lines"]
    giant = internal["giant"]
    imports = internal["imports"]
    const_names = internal["const_names"]

    new_imports = [
        IMPORT_FMT % (const_names[i], _module_specifier(internal["paths"][i], path))
        for i in range(len(const_names))
    ]
    insert_at = imports[-1][1] + 1 if imports else _first_code_line(internal["masked"])

    assembly = [lines[k].rstrip() for k in range(giant.start, giant.decl)]  # leading comments
    export_kw = "export " if giant.exported else ""
    assembly.append("%sconst %s: %s = [" % (export_kw, giant.name, internal["annotation"]))
    assembly.extend("  ...%s," % name for name in const_names)
    assembly.append("]")

    out: list[str] = []
    i = 0
    while i < len(lines):
        if i == insert_at and new_imports:
            out.extend(new_imports)
            new_imports = []
        if giant.start <= i <= giant.end:
            out.extend(assembly)
            i = giant.end + 1
            continue
        out.append(lines[i].rstrip())
        i += 1
    if new_imports:
        out.extend(new_imports)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return text.rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# Public entry points used by split_oversize.py
# --------------------------------------------------------------------------


def render_all(root: Path, path: Path, analysis: dict) -> list[tuple[Path, str]]:
    internal = analysis["_internal"]
    written: list[tuple[Path, str]] = []
    if analysis["strategy"] == "data":
        for i in range(len(internal["bins"])):
            written.append((internal["paths"][i], _render_data_part(i, internal)))
        written.append((path, _render_data_facade(internal, path)))
    else:
        for i in range(len(internal["named"])):
            written.append((internal["paths"][i], _render_part(i, internal)))
        written.append((path, _render_facade(internal, path)))
    return written


def apply(root: Path, path: Path, analysis: dict) -> list[str]:
    written: list[str] = []
    for target, text in render_all(root, path, analysis):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(str(target.relative_to(root)))
    return written


def print_proposal(analysis: dict) -> None:
    giant = analysis["giant"]
    print("[loc-fix] %s — %d lines (max %d)" % (analysis["file"], analysis["lines"], analysis["limit"]))
    label = "member extraction" if analysis["strategy"] == "members" else "data extraction"
    print(
        "  strategy: %s — `%s %s` is %d lines on its own; no rearranging of top-level "
        "declarations can fix this file" % (label, giant["kind"], giant["name"], giant["lines"])
    )
    if analysis.get("layout"):
        print("  layout: %s — %s" % (analysis["layout"], analysis["layout_reason"]))
    for i, g in enumerate(analysis["groups"], 1):
        members = ", ".join(b["name"] for b in g["blocks"])
        print("  %d. %-44s %4d lines  (%s)" % (i, g["path"], g["lines"], members))
    if analysis.get("facade"):
        print(
            "  facade: %s — %d lines — keeps the declaration plus everything that cannot move"
            % (analysis["facade"]["path"], analysis["facade"]["lines"])
        )
    for k in analysis.get("kept", []):
        print("    kept in class: %s — %s" % (k["name"], k["reason"]))
    if analysis.get("stubbed"):
        print(
            "  stubbed: %s — public bodies move to parts; delegating stubs keep the class "
            "type surface identical" % ", ".join(analysis["stubbed"])
        )
    if analysis.get("widened"):
        print(
            "  widened: private -> public on %s (the parts need them; the package barrel is unchanged)"
            % ", ".join(analysis["widened"])
        )
    if analysis.get("promoted"):
        print(
            "  promoted: %s — exported from %s for the parts, absent from the barrel"
            % (", ".join(analysis["promoted"]), analysis["file"])
        )
    if analysis["strategy"] == "members" and analysis["groups"]:
        print("  note: extracted functions take the instance as `self`; `this.x()` becomes `x(this)`")
    for b in analysis["blockers"]:
        print("  blocked: %s" % b)
    if analysis["groups"] and not analysis["blockers"]:
        print("  apply: python3 .claude/scripts/split_oversize.py --apply %s" % analysis["file"])
        print("  then:  just lint-fix && just check   (apply leaves unused imports for Biome to clean)")
