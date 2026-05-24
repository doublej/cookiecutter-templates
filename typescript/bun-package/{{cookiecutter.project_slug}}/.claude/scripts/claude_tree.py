#!/usr/bin/env python3
"""Interactive viewer + editor for every CLAUDE.md in the project + ancestor chain.

Default mode launches a local HTTP server (127.0.0.1, ephemeral port) with a
mermaid flowchart whose nodes preview each CLAUDE.md (H1 + first paragraph).
Click a node to scroll to its editor; save/revert is gated; every save
appends the previous content to a sidecar `CLAUDE.md.history.jsonl` next to
each file (one JSON line per snapshot).

Static mode (`--static`) keeps the old behaviour: writes
`.claude/claude-tree.html` + `.claude/claude-tree.md` and exits.

Walks up from cwd to filesystem root, picks up `~/.claude/CLAUDE.md`, then
walks down inside the project. Best-effort phone-home via `_diag.py`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html as _html
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "target", "dist", "build",
    ".next", ".svelte-kit", ".cache", "__pycache__", ".mypy_cache",
    ".ruff_cache", ".pytest_cache", "_diagnostics", ".gradle", "DerivedData",
    ".build", ".swiftpm",
}
_MAX_BYTES = 1_000_000  # per CLAUDE.md, hard safety cap
_HISTORY_SUFFIX = ".history.jsonl"

sys.path.insert(0, str(Path(__file__).parent))
try:
    import _diag  # type: ignore
except Exception:
    _diag = None  # type: ignore


def find_ancestors(start: Path) -> list[Path]:
    results: list[Path] = []
    cur = start.parent
    while True:
        candidate = cur / "CLAUDE.md"
        if candidate.is_file():
            results.append(candidate.resolve())
        if cur == cur.parent:
            break
        cur = cur.parent
    home_global = Path.home() / ".claude" / "CLAUDE.md"
    if home_global.is_file() and home_global.resolve() not in results:
        results.append(home_global.resolve())
    return results


def find_descendants(root: Path) -> list[Path]:
    results: list[Path] = []
    for path in root.rglob("CLAUDE.md"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts[:-1]
        if any(p in _SKIP_DIRS for p in rel_parts):
            continue
        results.append(path.resolve())
    return sorted(results)


def short_label(path: Path) -> str:
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def _read_safely(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as e:
        return f"<unreadable: {e}>"
    if len(data) > _MAX_BYTES:
        return data[:_MAX_BYTES].decode("utf-8", errors="replace") + "\n\n... (truncated)"
    return data.decode("utf-8", errors="replace")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def make_preview(text: str, max_chars: int = 120) -> str:
    """Return H1 + first paragraph snippet for mermaid node label."""
    lines = text.splitlines()
    h1 = ""
    rest_start = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith("# "):
            h1 = stripped[2:].strip()
            rest_start = i + 1
            break
    paragraph = ""
    for ln in lines[rest_start:]:
        stripped = ln.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            if paragraph:
                break
            continue
        paragraph = stripped
        break
    pieces = [p for p in (h1, paragraph) if p]
    snippet = " — ".join(pieces) if pieces else "(empty)"
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 1] + "…"
    return snippet


def _mermaid_escape(label: str) -> str:
    return label.replace("\\", "\\\\").replace('"', '#quot;').replace("\n", " ")


def _mermaid_for_html(mermaid: str) -> str:
    """Escape a mermaid source for embedding inside ``<pre class=mermaid>``.

    The browser decodes HTML entities into the ``<pre>`` textContent before
    mermaid parses it, so a plain HTML-escape reproduces the source exactly:
    node-label tags survive as real angle brackets (htmlLabels), the ``"``
    delimiters survive, and mermaid's own ``#quot;`` entity stays literal — so a
    quote character inside a label can't prematurely terminate ``["..."]``.
    """
    return _html.escape(mermaid)


def _clamp(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def extract_preview(text: str) -> dict:
    """Structured preview of a CLAUDE.md: title, blurb, section list, size."""
    lines = text.splitlines()
    h1, h1_idx = "", -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("# ") and not s.startswith("## "):
            h1, h1_idx = s[2:].strip(), i
            break
    sections = [
        ln.strip()[3:].strip()
        for ln in lines
        if ln.strip().startswith("## ") and not ln.strip().startswith("### ")
    ]
    blurb = ""
    for ln in lines[h1_idx + 1:]:
        s = ln.strip()
        if not s or s.startswith(("#", ">", "-", "*", "`", "|", "<")):
            continue
        blurb = s
        break
    return {"h1": h1, "blurb": blurb, "sections": sections, "lines": len(lines)}


def make_node_html(path: Path, text: str) -> str:
    """Rich HTML label for a mermaid node: a fixed-width card with path, title,
    blurb, section outline, and a line-count footer. The fixed width (set in CSS
    on `.cmcard`) is what stops mermaid collapsing the node to a 1-char column."""
    info = extract_preview(text)
    rows = [f'<div class=cmpath>{_mermaid_escape(short_label(path))}</div>']
    if info["h1"]:
        rows.append(f'<div class=cmtitle>{_mermaid_escape(_clamp(info["h1"], 64))}</div>')
    if info["blurb"]:
        rows.append(f'<div class=cmblurb>{_mermaid_escape(_clamp(info["blurb"], 130))}</div>')
    if info["sections"]:
        chips = " · ".join(info["sections"])
        rows.append(f'<div class=cmsecs>§ {_mermaid_escape(_clamp(chips, 120))}</div>')
    rows.append(f'<div class=cmmeta>{info["lines"]} lines</div>')
    return f'<div class=cmcard>{"".join(rows)}</div>'


def build_mermaid(project_root: Path, ancestors: list[Path], descendants: list[Path],
                  contents: dict[Path, str]) -> tuple[str, dict[str, str]]:
    """Return (mermaid_source, {node_id: path_str}). Each node label has
    `path<br/>preview`; node id is `n<index>` and is wired to a JS click handler."""
    lines = ["flowchart TD"]
    nodes: dict[Path, str] = {}
    id_to_path: dict[str, str] = {}

    def node(p: Path) -> str:
        if p in nodes:
            return nodes[p]
        nid = f"n{len(nodes)}"
        label = make_node_html(p, contents.get(p, ""))
        lines.append(f'    {nid}["{label}"]')
        lines.append(f'    click {nid} call onNodeClick("{nid}")')
        nodes[p] = nid
        id_to_path[nid] = str(p)
        return nid

    ancestors_sorted = sorted(set(ancestors), key=lambda p: len(p.parts))
    prev = None
    for a in ancestors_sorted:
        nid = node(a)
        if prev is not None:
            lines.append(f"    {prev} --> {nid}")
        prev = nid

    project_cmd = project_root / "CLAUDE.md"
    project_node = node(project_cmd.resolve()) if project_cmd.is_file() else None
    if project_node and prev and project_node != prev:
        lines.append(f"    {prev} --> {project_node}")

    parent_for: dict[Path, str] = {}
    if project_node:
        parent_for[project_root.resolve()] = project_node
    for d in descendants:
        if project_node and d == project_cmd.resolve():
            continue
        parent_node = project_node
        cur = d.parent.parent
        while cur and cur != cur.parent:
            if cur in parent_for:
                parent_node = parent_for[cur]
                break
            cur = cur.parent
        nid = node(d)
        if parent_node:
            lines.append(f"    {parent_node} --> {nid}")
        parent_for[d.parent.resolve()] = nid

    return "\n".join(lines), id_to_path


def render_markdown(project_root: Path, mermaid: str, files: list[Path]) -> str:
    ts = _dt.datetime.now().isoformat(timespec="seconds")
    parts = [
        "# CLAUDE.md tree",
        "",
        f"Project: `{project_root}`  ",
        f"Generated: {ts}  ",
        f"Files found: {len(files)}",
        "",
        "```mermaid",
        mermaid,
        "```",
        "",
        "## Files",
        "",
    ]
    for f in files:
        parts.append(f"- [`{short_label(f)}`]({f})")
    parts.append("")
    return "\n".join(parts)


# Distinctive type pairing (Space Grotesk for UI/headings, IBM Plex Mono for
# code/paths), loaded from Google Fonts with graceful system fallbacks so the
# tool still works offline.
_FONT_LINKS = (
    '<link rel=preconnect href="https://fonts.googleapis.com">'
    '<link rel=preconnect href="https://fonts.gstatic.com" crossorigin>'
    '<link rel=stylesheet href="https://fonts.googleapis.com/css2?'
    "family=IBM+Plex+Mono:wght@400;500&"
    'family=Space+Grotesk:wght@400;500;700&display=swap">'
)

# Mermaid node card — shared by static + live views. The fixed `.cmcard` width is
# the load-bearing rule: without it mermaid collapses htmlLabel nodes to ~1ch.
_NODE_CARD_CSS = """
  .diagram .nodeLabel { white-space: normal; text-align: left; }
  .diagram .node rect, .diagram .node polygon { fill: #ffffff; stroke: #e3e0d8;
            stroke-width: 1.25px; rx: 10; ry: 10; }
  .diagram .node.sel rect, .diagram .node.sel polygon { stroke: #4338ca;
            stroke-width: 2.25px; }
  .diagram .edgePath path { stroke: #d2cdc3; }
  .diagram .arrowheadPath, .diagram marker path { fill: #d2cdc3; stroke: none; }
  .cmcard { width: 198px; text-align: left; padding: 2px 1px; }
  .cmpath { font: 9px/1.45 'IBM Plex Mono', ui-monospace, Menlo, monospace;
            color: #a9a59c; overflow-wrap: anywhere; margin-bottom: 5px; }
  .cmtitle { font: 600 13px/1.25 'Space Grotesk', ui-sans-serif, sans-serif;
             color: #1b1b1f; letter-spacing: -.01em; margin-bottom: 5px; }
  .cmblurb { font: 11px/1.4 'Space Grotesk', ui-sans-serif, sans-serif; color: #6b6b73;
             display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
             overflow: hidden; margin-bottom: 5px; }
  .cmsecs { font: 10px/1.4 'IBM Plex Mono', ui-monospace, monospace; color: #0f766e;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden; margin-bottom: 5px; }
  .cmmeta { font: 9px/1.2 'IBM Plex Mono', ui-monospace, monospace; color: #b6b2a9; }
"""

_STATIC_STYLE = (
    "<style>\n"
    "  body { font-family: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;\n"
    "         max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #1b1b1f;\n"
    "         background: #f4f3ef; }\n"
    "  h1 { font-weight: 700; font-size: 1.3rem; letter-spacing: -.02em;\n"
    "       margin-bottom: .25rem; }\n"
    "  .meta { color: #6b6b73; font-size: .85rem; margin-bottom: 1.5rem; }\n"
    "  .diagram { background: #faf9f5; border: 1px solid #e3e0d8; border-radius: 14px;\n"
    "             padding: 1rem; overflow-x: auto; }\n"
    "  details { border: 1px solid #e3e0d8; border-radius: 10px; margin: .5rem 0;\n"
    "            background: #fff; }\n"
    "  details[open] { background: #fffdf8; }\n"
    "  summary { cursor: pointer; padding: .6rem .9rem; font-weight: 600;\n"
    "            display: flex; gap: .75rem; align-items: baseline; }\n"
    "  pre { margin: 0; padding: .9rem 1rem; border-top: 1px solid #efece4;\n"
    "        background: #faf9f5; overflow-x: auto;\n"
    "        font-family: 'IBM Plex Mono', ui-monospace, Menlo, monospace;\n"
    "        font-size: .82rem; line-height: 1.5; white-space: pre-wrap;\n"
    "        word-break: break-word; }\n"
    "  h2 { font-weight: 600; font-size: 1rem; margin-top: 2rem; }\n"
    "  .path { color: #a9a59c; font-weight: 400; font-size: .72rem;\n"
    "          font-family: 'IBM Plex Mono', ui-monospace, monospace;\n"
    "          word-break: break-all; }\n"
    + _NODE_CARD_CSS
    + "</style>"
)

_STATIC_SCRIPT = (
    "<script type=module>\n"
    "  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';\n"
    "  window.onNodeClick = function(id) {\n"
    "    const el = document.getElementById('editor-' + id);\n"
    "    if (el) el.scrollIntoView({behavior:'smooth', block:'start'});\n"
    "  };\n"
    "  mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose',\n"
    "                       flowchart: { htmlLabels: true } });\n"
    "</script>"
)


def render_static_html(project_root: Path, mermaid: str, files: list[Path],
                       id_to_path: dict[str, str], contents: dict[Path, str]) -> str:
    ts = _dt.datetime.now().isoformat(timespec="seconds")
    blocks = []
    path_to_id = {v: k for k, v in id_to_path.items()}
    project_cmd = (project_root / "CLAUDE.md").resolve()
    for f in files:
        nid = path_to_id.get(str(f), "")
        label = _html.escape(short_label(f))
        full = _html.escape(str(f))
        body = _html.escape(contents.get(f, ""))
        open_attr = " open" if f == project_cmd else ""
        blocks.append(
            f'<details id="editor-{nid}"{open_attr}><summary><code>{label}</code> '
            f'<span class=path>{full}</span></summary>'
            f'<pre>{body}</pre></details>'
        )
    files_html = "\n".join(blocks)
    mermaid_safe = _mermaid_for_html(mermaid)
    project_safe = _html.escape(str(project_root))
    return (
        "<!doctype html>\n<html lang=en>\n<meta charset=utf-8>\n"
        f"<title>CLAUDE.md tree — {project_safe}</title>\n{_FONT_LINKS}\n"
        f"{_STATIC_STYLE}\n<h1>CLAUDE.md tree</h1>\n"
        f"<div class=meta>Project: <code>{project_safe}</code><br>"
        f"Generated: {ts} · {len(files)} files</div>\n"
        f"<h2>Hierarchy</h2>\n<div class=diagram><pre class=mermaid>{mermaid_safe}</pre></div>\n"
        f"<h2>Contents</h2>\n{files_html}\n{_STATIC_SCRIPT}\n</html>\n"
    )


def history_path_for(p: Path) -> Path:
    return p.with_name(p.name + _HISTORY_SUFFIX)


def append_history(p: Path, prior_content: str) -> None:
    record = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "sha": _sha(prior_content),
        "content": prior_content,
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    fd = os.open(str(history_path_for(p)),
                 os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def read_history(p: Path) -> list[dict]:
    hp = history_path_for(p)
    if not hp.is_file():
        return []
    entries: list[dict] = []
    for line in hp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def pop_history(p: Path) -> dict | None:
    """Remove and return the most recent history entry (LIFO)."""
    entries = read_history(p)
    if not entries:
        return None
    last = entries.pop()
    hp = history_path_for(p)
    hp.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
                  encoding="utf-8")
    return last


class _ServerState:
    """Module-level singleton for the running server. Cleaner than globals."""
    files: dict[str, Path] = {}
    project_root: Path = Path.cwd()
    token: str = ""
    mermaid: str = ""


_STATE = _ServerState()


def _server_html() -> str:
    """Render the live editor HTML. Uses inline template + JS that calls the API."""
    mermaid_safe = _mermaid_for_html(_STATE.mermaid)
    project_safe = _html.escape(str(_STATE.project_root))
    return _EDITOR_TEMPLATE.replace("__MERMAID__", mermaid_safe) \
                           .replace("__PROJECT__", project_safe) \
                           .replace("__FONTS__", _FONT_LINKS) \
                           .replace("__NODECSS__", _NODE_CARD_CSS) \
                           .replace("__TOKEN__", _STATE.token)


class _Handler(http.server.BaseHTTPRequestHandler):
    server_version = "ClaudeTree/1.0"

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        if self.path.startswith("/api/"):
            sys.stderr.write(f"[claude-tree] {self.command} {self.path}\n")

    def _send_json(self, code: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str, ctype: str = "text/plain") -> None:
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self) -> dict[str, str]:
        return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

    def _resolve(self, q: dict[str, str]) -> Path | None:
        fid = q.get("id", "")
        return _STATE.files.get(fid)

    def _check_token(self, q: dict[str, str]) -> bool:
        return q.get("token", "") == _STATE.token and bool(_STATE.token)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        q = self._query()
        if route == "/":
            self._send_text(200, _server_html(), "text/html")
        elif route == "/api/files":
            proj = (_STATE.project_root / "CLAUDE.md").resolve()

            def _kind(p: Path) -> str:
                if p == proj:
                    return "project"
                try:
                    p.relative_to(_STATE.project_root)
                    return "descendant"
                except ValueError:
                    return "ancestor"

            payload = [
                {"id": fid, "path": str(p), "label": short_label(p),
                 "kind": _kind(p), "preview": make_preview(_read_safely(p))}
                for fid, p in _STATE.files.items()
            ]
            self._send_json(200, payload)
        elif route == "/api/content":
            p = self._resolve(q)
            if not p:
                return self._send_json(404, {"error": "unknown id"})
            content = _read_safely(p)
            self._send_json(200, {"content": content, "sha": _sha(content)})
        elif route == "/api/history":
            p = self._resolve(q)
            if not p:
                return self._send_json(404, {"error": "unknown id"})
            entries = read_history(p)
            summary = [{"ts": e["ts"], "sha": e.get("sha", ""),
                        "preview": make_preview(e.get("content", ""))} for e in entries]
            self._send_json(200, summary)
        elif route == "/api/history/entry":
            p = self._resolve(q)
            if not p:
                return self._send_json(404, {"error": "unknown id"})
            try:
                n = int(q.get("n", "-1"))
            except ValueError:
                return self._send_json(400, {"error": "bad n"})
            entries = read_history(p)
            if not entries or not (-len(entries) <= n < len(entries)):
                return self._send_json(404, {"error": "no such entry"})
            self._send_text(200, entries[n].get("content", ""))
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        q = self._query()
        if not self._check_token(q):
            return self._send_json(403, {"error": "bad token"})
        p = self._resolve(q)
        if not p:
            return self._send_json(404, {"error": "unknown id"})
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else ""

        if route == "/api/save":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "bad json"})
            new_content = payload.get("content", "")
            disk_sha = _sha(_read_safely(p))
            expected = payload.get("expected_sha")
            if expected and expected != disk_sha and not payload.get("force"):
                return self._send_json(409, {"error": "disk changed", "disk_sha": disk_sha})
            try:
                append_history(p, _read_safely(p))
                p.write_text(new_content, encoding="utf-8")
            except OSError as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"ok": True, "sha": _sha(new_content)})

        if route == "/api/revert":
            entry = pop_history(p)
            if not entry:
                return self._send_json(404, {"error": "no history"})
            try:
                p.write_text(entry.get("content", ""), encoding="utf-8")
            except OSError as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"ok": True, "sha": entry.get("sha", "")})

        self.send_error(404)


def _serve(host: str = "127.0.0.1", port: int = 0, open_browser: bool = True) -> None:
    with socketserver.ThreadingTCPServer((host, port), _Handler) as httpd:
        actual_port = httpd.server_address[1]
        url = f"http://{host}:{actual_port}/"
        print(f"[claude-tree] editor at {url}  (Ctrl-C to stop)", flush=True)
        if open_browser:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[claude-tree] shutting down.")
            httpd.shutdown()


def _build_state(root: Path) -> tuple[list[Path], list[Path], dict[Path, str]]:
    ancestors = find_ancestors(root)
    descendants = find_descendants(root)
    contents = {p: _read_safely(p) for p in (*ancestors, *descendants)}
    return ancestors, descendants, contents


def run_static(root: Path) -> dict:
    ancestors, descendants, contents = _build_state(root)
    files = list(dict.fromkeys(ancestors + descendants))
    mermaid, id_to_path = build_mermaid(root, ancestors, descendants, contents)
    out_dir = root / ".claude"
    out_dir.mkdir(exist_ok=True)
    html_path = out_dir / "claude-tree.html"
    md_path = out_dir / "claude-tree.md"
    html_path.write_text(render_static_html(root, mermaid, files, id_to_path, contents))
    md_path.write_text(render_markdown(root, mermaid, files))
    print(f"[claude-tree] {len(files)} CLAUDE.md → {html_path.relative_to(root)} + {md_path.relative_to(root)}")
    return {"mode": "static", "files": len(files)}


def run_server(root: Path, port: int, open_browser: bool) -> dict:
    ancestors, descendants, contents = _build_state(root)
    files = list(dict.fromkeys(ancestors + descendants))
    mermaid, id_to_path = build_mermaid(root, ancestors, descendants, contents)
    _STATE.project_root = root
    _STATE.token = secrets.token_urlsafe(24)
    _STATE.mermaid = mermaid
    _STATE.files = {nid: Path(p) for nid, p in id_to_path.items()}
    _serve(port=port, open_browser=open_browser)
    return {"mode": "server", "files": len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true",
                        help="write .claude/claude-tree.{html,md} and exit (no server)")
    parser.add_argument("--port", type=int, default=0,
                        help="server port (0 = ephemeral)")
    parser.add_argument("--no-open", action="store_true",
                        help="don't auto-open browser")
    args = parser.parse_args()

    started = time.monotonic()
    status = "ok"
    error: BaseException | None = None
    meta: dict = {}
    try:
        root = Path.cwd().resolve()
        if args.static:
            meta = run_static(root)
        else:
            meta = run_server(root, args.port, open_browser=not args.no_open)
    except Exception as e:
        status = "error"
        error = e
        print(f"[claude-tree] error: {e}", file=sys.stderr)
    duration_ms = int((time.monotonic() - started) * 1000)
    if _diag is not None:
        _diag.log("claude_tree", status, duration_ms, meta=meta, error=error)
    if status == "error":
        sys.exit(1)


# ---------------------------------------------------------------------------
# Server-mode HTML (single-file template). Placeholders: __MERMAID__,
# __PROJECT__, __TOKEN__. JS calls back to the Python server's /api/* routes.
# ---------------------------------------------------------------------------
_EDITOR_TEMPLATE = r"""<!doctype html>
<html lang=en>
<meta charset=utf-8>
<title>CLAUDE.md tree — __PROJECT__</title>
__FONTS__
<style>
  :root {
    --bg: #f4f3ef; --panel: #ffffff; --panel-2: #faf9f5;
    --ink: #1b1b1f; --muted: #6b6b73; --faint: #a9a59c;
    --line: #e3e0d8; --line-soft: #efece4;
    --accent: #4338ca; --accent-ink: #ffffff; --accent-tint: #ecebfc;
    --danger: #b4451f;
    --sans: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;
    --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body { font-family: var(--sans); color: var(--ink); background: var(--bg);
         display: flex; flex-direction: column; -webkit-font-smoothing: antialiased; }
  .topbar { display: flex; align-items: center; gap: .7rem; flex-wrap: wrap;
            padding: .6rem 1rem; background: var(--panel);
            border-bottom: 1px solid var(--line); }
  .topbar h1 { font-size: .95rem; font-weight: 700; letter-spacing: -.02em; margin: 0;
               display: flex; align-items: center; gap: .5rem; }
  .topbar h1::before { content: ""; width: 9px; height: 9px; border-radius: 2px;
                       background: var(--accent); transform: rotate(45deg); }
  .topbar .proj { color: var(--muted); font: 400 .72rem/1 var(--mono);
                  word-break: break-all; }
  .topbar .hint { color: var(--faint); font-size: .72rem; margin-left: auto; }
  .topbar kbd { font: 500 .68rem var(--mono); background: var(--panel-2);
                border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px;
                color: var(--muted); }
  .split { flex: 1; display: flex; min-height: 0; }
  .graphpane { flex: 0 0 36%; min-width: 248px; max-width: 64%; overflow: auto;
               resize: horizontal; border-right: 1px solid var(--line);
               background: var(--panel-2); padding: .8rem;
               background-image: radial-gradient(circle at 1px 1px, #e7e4db 1px, transparent 0);
               background-size: 22px 22px; animation: rise .5s ease both; }
  .diagram svg { height: auto; }
__NODECSS__
  .editorpane { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column;
                overflow: hidden; background: var(--panel);
                animation: rise .5s .07s ease both; }
  .empty { margin: auto; color: var(--faint); font: 400 .85rem var(--sans);
           text-align: center; padding: 2rem; }
  #editor { display: none; flex-direction: column; height: 100%; }
  #editor.show { display: flex; }
  #editor header { display: flex; align-items: baseline; gap: .6rem;
                   padding: .7rem 1rem; border-bottom: 1px solid var(--line-soft);
                   flex-wrap: wrap; }
  #editor header code { font: 600 .92rem var(--sans); letter-spacing: -.01em; }
  #editor header .path { color: var(--faint); font: 400 .7rem var(--mono);
                         word-break: break-all; flex: 1 1 auto; }
  #editor header .badge { font: 500 .66rem var(--mono); padding: 2px 8px;
                          border-radius: 999px; background: var(--accent-tint);
                          color: var(--accent); white-space: nowrap; }
  #editor header .badge.dirty { background: #fbe7df; color: var(--danger); }
  #editor textarea { flex: 1; width: 100%; border: 0; padding: 1rem 1.1rem;
                     font: 400 .82rem/1.6 var(--mono); resize: none; tab-size: 2;
                     background: var(--panel); color: var(--ink); outline: 0; }
  #editor footer { display: flex; gap: .5rem; align-items: center;
                   padding: .6rem 1rem; border-top: 1px solid var(--line-soft);
                   font-size: .76rem; flex-wrap: wrap; background: var(--panel-2); }
  #editor footer .spacer { flex: 1; }
  #editor footer label { color: var(--muted); display: flex; gap: .35rem;
                         align-items: center; }
  button { font: 500 .76rem var(--sans); padding: .36rem .85rem; border-radius: 7px;
           border: 1px solid var(--line); background: var(--panel); color: var(--ink);
           cursor: pointer; transition: background .12s, border-color .12s; }
  button:hover:not(:disabled) { background: var(--panel-2); border-color: #d6d2c8; }
  button:disabled { opacity: .45; cursor: default; }
  button.primary { border-color: var(--accent); background: var(--accent);
                   color: var(--accent-ink); }
  button.primary:hover:not(:disabled) { background: #3730a3; border-color: #3730a3; }
  select { font: 500 .74rem var(--mono); padding: .3rem .45rem; border-radius: 6px;
           border: 1px solid var(--line); background: var(--panel); color: var(--ink); }
  .toast { position: fixed; bottom: 1.1rem; right: 1.1rem; background: var(--ink);
           color: #fff; padding: .6rem .9rem; border-radius: 8px;
           font: 500 .8rem var(--sans); box-shadow: 0 6px 24px rgba(0,0,0,.18);
           opacity: 0; transform: translateY(6px);
           transition: opacity .2s, transform .2s; }
  .toast.show { opacity: 1; transform: none; }
  .toast.err { background: var(--danger); }
  @keyframes rise { from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: none; } }
</style>

<div class=topbar>
  <h1>CLAUDE.md tree</h1>
  <span class=proj>__PROJECT__</span>
  <span class=hint>Click a node to open · <kbd>⌘/Ctrl-S</kbd> to save</span>
</div>

<div class=split>
  <aside class=graphpane><div class=diagram><pre class=mermaid>__MERMAID__</pre></div></aside>
  <main class=editorpane>
    <div class=empty id=empty>Select a CLAUDE.md node on the left to edit it.</div>
    <section id=editor>
      <header>
        <code data-role=label></code>
        <span class=path data-role=path></span>
        <span class=badge data-role=status></span>
      </header>
      <textarea spellcheck=false data-role=ta></textarea>
      <footer>
        <button data-action=save class=primary disabled>Save</button>
        <button data-action=revert disabled>Revert to last snapshot</button>
        <span class=spacer></span>
        <label>History:
          <select data-role=history><option value="">(latest)</option></select>
        </label>
        <button data-action=preview>Preview</button>
      </footer>
    </section>
  </main>
</div>
<div id=toast class=toast></div>

<script type=module>
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
const TOKEN = '__TOKEN__';
const toastEl = document.getElementById('toast');
const emptyEl = document.getElementById('empty');
const ed = document.getElementById('editor');
const els = {
  label: ed.querySelector('[data-role=label]'),
  path: ed.querySelector('[data-role=path]'),
  status: ed.querySelector('[data-role=status]'),
  ta: ed.querySelector('[data-role=ta]'),
  history: ed.querySelector('[data-role=history]'),
  save: ed.querySelector('[data-action=save]'),
  revert: ed.querySelector('[data-action=revert]'),
  preview: ed.querySelector('[data-action=preview]'),
};
const filesById = {};
let current = null;
let dirty = false;

function toast(msg, kind) {
  toastEl.textContent = msg;
  toastEl.className = 'toast show' + (kind === 'err' ? ' err' : '');
  setTimeout(() => { toastEl.className = 'toast'; }, 2200);
}

function api(path, opts = {}) {
  const url = path + (path.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(TOKEN);
  return fetch(url, opts).then(async r => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  });
}

function setDirty(on) {
  dirty = on;
  els.save.disabled = !on;
  els.status.classList.toggle('dirty', on);
}

function highlight(id) {
  document.querySelectorAll('g.node.sel').forEach(n => n.classList.remove('sel'));
  const n = document.querySelector('[id^="flowchart-' + id + '-"]');
  if (n) n.classList.add('sel');
}

async function refreshHistory() {
  const entries = await fetch('/api/history?id=' + current.id).then(r => r.json());
  els.history.innerHTML = '<option value="">(latest)</option>';
  entries.forEach((e, i) => {
    const o = document.createElement('option');
    o.value = i;
    o.textContent = `${e.ts.replace('T', ' ').replace('+00:00', 'Z')} · ${e.sha}`;
    els.history.appendChild(o);
  });
  els.revert.disabled = entries.length === 0;
}

async function loadInto(id) {
  const file = filesById[id];
  if (!file) return;
  current = file;
  emptyEl.style.display = 'none';
  ed.classList.add('show');
  els.label.textContent = file.label;
  els.path.textContent = file.path;
  els.status.textContent = 'loading…';
  const r = await fetch('/api/content?id=' + id).then(r => r.json());
  els.ta.value = r.content;
  els.ta.dataset.sha = r.sha;
  els.status.textContent = 'sha ' + r.sha;
  setDirty(false);
  highlight(id);
  await refreshHistory();
}

function open(id) {
  if (dirty && current && id !== current.id &&
      !confirm('Discard unsaved changes to ' + current.label + '?')) return;
  loadInto(id).then(() => els.ta.focus({preventScroll: true}));
}
window.onNodeClick = open;

els.ta.addEventListener('input', () => {
  els.status.textContent = 'unsaved';
  setDirty(true);
});

async function save() {
  if (!current || !dirty) return;
  els.save.disabled = true;
  try {
    const r = await api('/api/save?id=' + current.id, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: els.ta.value, expected_sha: els.ta.dataset.sha})
    });
    els.ta.dataset.sha = r.sha;
    els.status.textContent = 'sha ' + r.sha;
    setDirty(false);
    toast('Saved · ' + current.label);
    await refreshHistory();
  } catch (e) {
    els.save.disabled = false;
    toast('Save failed: ' + e.message, 'err');
  }
}
els.save.addEventListener('click', save);

els.revert.addEventListener('click', async () => {
  if (!current) return;
  if (!confirm('Revert ' + current.label + ' to last snapshot?')) return;
  try {
    await api('/api/revert?id=' + current.id, {method: 'POST'});
    await loadInto(current.id);
    toast('Reverted · ' + current.label);
  } catch (e) {
    toast('Revert failed: ' + e.message, 'err');
  }
});

els.preview.addEventListener('click', async () => {
  if (!current) return;
  const n = els.history.value;
  if (n === '') return loadInto(current.id);
  const txt = await fetch('/api/history/entry?id=' + current.id + '&n=' + n).then(r => r.text());
  els.ta.value = txt;
  els.status.textContent = 'previewing #' + n + ' (unsaved)';
  setDirty(true);
});

document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault();
    save();
  }
});
window.addEventListener('beforeunload', (e) => {
  if (dirty) { e.preventDefault(); e.returnValue = ''; }
});

// Render the graph at natural 1:1 size and let the pane scroll, instead of
// mermaid's default fit-to-width which shrinks node cards to illegibility.
function sizeGraph() {
  const svg = document.querySelector('.diagram svg');
  if (!svg || !svg.viewBox || !svg.viewBox.baseVal.width) return;
  svg.style.maxWidth = 'none';
  svg.style.width = svg.viewBox.baseVal.width + 'px';
  svg.style.height = svg.viewBox.baseVal.height + 'px';
}

(async () => {
  mermaid.initialize({ startOnLoad: false, theme: 'neutral',
                       securityLevel: 'loose',
                       flowchart: { htmlLabels: true } });
  try { await mermaid.run(); sizeGraph(); } catch (e) { console.error('mermaid', e); }
  const files = await fetch('/api/files').then(r => r.json());
  files.forEach(f => { filesById[f.id] = f; });
  const initial = files.find(f => f.kind === 'project') || files[0];
  if (initial) loadInto(initial.id);
})();
</script>
</html>
"""


if __name__ == "__main__":
    main()
