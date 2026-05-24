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
import re
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
        label = _mermaid_escape(short_label(p))
        preview = _mermaid_escape(make_preview(contents.get(p, "")))
        lines.append(f'    {nid}["<b>{label}</b><br/><span class=preview>{preview}</span>"]')
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


_STATIC_STYLE = """<style>
  body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 1100px;
         margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
  h1 { font-size: 1.25rem; margin-bottom: 0.25rem; }
  .meta { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }
  .diagram { background: #fafafa; border: 1px solid #eee; border-radius: 6px;
             padding: 1rem; overflow-x: auto; }
  details { border: 1px solid #eee; border-radius: 6px; margin: 0.5rem 0;
            background: #fff; }
  details[open] { background: #fdfdfd; }
  summary { cursor: pointer; padding: 0.6rem 0.8rem; font-weight: 600;
            display: flex; gap: 0.75rem; align-items: baseline; }
  pre { margin: 0; padding: 0.9rem 1rem; border-top: 1px solid #eee;
        background: #fafafa; overflow-x: auto; font-size: 0.85rem;
        line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
  h2 { font-size: 1rem; margin-top: 2rem; }
  .preview { color: #666; font-weight: 400; font-size: 0.8em; }
  .path { color: #888; font-weight: 400; font-size: 0.75rem; word-break: break-all; }
  .node b { font-size: 0.85em; }
</style>"""

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
    for f in files:
        nid = path_to_id.get(str(f), "")
        label = _html.escape(short_label(f))
        full = _html.escape(str(f))
        body = _html.escape(contents.get(f, ""))
        blocks.append(
            f'<details id="editor-{nid}" open><summary><code>{label}</code> '
            f'<span class=path>{full}</span></summary>'
            f'<pre>{body}</pre></details>'
        )
    files_html = "\n".join(blocks)
    mermaid_safe = _html.escape(mermaid).replace("&quot;", '"').replace("#quot;", "&quot;")
    project_safe = _html.escape(str(project_root))
    return (
        "<!doctype html>\n<html lang=en>\n<meta charset=utf-8>\n"
        f"<title>CLAUDE.md tree — {project_safe}</title>\n"
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
    mermaid_safe = _html.escape(_STATE.mermaid).replace("&quot;", '"').replace("#quot;", "&quot;")
    project_safe = _html.escape(str(_STATE.project_root))
    return _EDITOR_TEMPLATE.replace("__MERMAID__", mermaid_safe) \
                           .replace("__PROJECT__", project_safe) \
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
            payload = [
                {"id": fid, "path": str(p), "label": short_label(p),
                 "preview": make_preview(_read_safely(p))}
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
<style>
  body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 1180px;
         margin: 1.5rem auto; padding: 0 1rem; color: #1a1a1a; }
  h1 { font-size: 1.2rem; margin: 0 0 .25rem; }
  .meta { color: #666; font-size: .8rem; margin-bottom: 1.25rem; }
  .diagram { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px;
             padding: .75rem; overflow-x: auto; margin-bottom: 1.5rem; }
  .diagram .nodeLabel b { font-size: .8em; }
  .diagram .preview { color: #777; font-size: .72em; font-style: italic; }
  .node-mine > rect, .node-mine > polygon { stroke-width: 2px !important; }
  .editor { border: 1px solid #e8e8e8; border-radius: 8px; margin: .9rem 0;
            background: #fff; scroll-margin-top: 1rem; }
  .editor header { display: flex; align-items: baseline; gap: .75rem;
                   padding: .6rem .9rem; border-bottom: 1px solid #f0f0f0;
                   flex-wrap: wrap; }
  .editor header code { font-size: .9rem; font-weight: 600; }
  .editor header .path { color: #888; font-size: .72rem; word-break: break-all;
                         flex: 1 1 auto; }
  .editor header .badge { font-size: .68rem; padding: 2px 6px; border-radius: 4px;
                          background: #eef; color: #335; }
  .editor header .dirty { background: #fde; color: #833; }
  .editor textarea { width: 100%; min-height: 12rem; box-sizing: border-box;
                     border: 0; padding: .8rem .9rem; font-family: ui-monospace,
                     SFMono-Regular, Menlo, monospace; font-size: .82rem;
                     line-height: 1.5; resize: vertical; background: #fcfcfc;
                     outline: 0; }
  .editor footer { display: flex; gap: .5rem; align-items: center;
                   padding: .55rem .9rem; border-top: 1px solid #f0f0f0;
                   font-size: .78rem; flex-wrap: wrap; }
  .editor footer .spacer { flex: 1; }
  .editor button { font: inherit; padding: .35rem .8rem; border-radius: 5px;
                   border: 1px solid #d0d0d0; background: #f6f6f6;
                   cursor: pointer; }
  .editor button:hover:not(:disabled) { background: #ececec; }
  .editor button:disabled { opacity: .5; cursor: default; }
  .editor button.primary { border-color: #2563eb; background: #2563eb;
                            color: white; }
  .editor button.primary:hover:not(:disabled) { background: #1d4fd8; }
  .editor button.danger { border-color: #b91c1c; color: #b91c1c;
                          background: #fff; }
  .editor select { font: inherit; padding: .3rem .4rem; border-radius: 5px;
                   border: 1px solid #d0d0d0; background: #fff; }
  .toast { position: fixed; bottom: 1rem; right: 1rem; background: #1a1a1a;
           color: #fff; padding: .55rem .85rem; border-radius: 6px;
           font-size: .8rem; opacity: 0; transition: opacity .2s; }
  .toast.show { opacity: 1; }
  .toast.err { background: #b91c1c; }
</style>

<h1>CLAUDE.md tree — editor</h1>
<div class=meta>
  Project: <code>__PROJECT__</code> ·
  Edit, then Save / Revert. Each save snapshots prior content to
  <code>CLAUDE.md.history.jsonl</code>.
</div>

<div class=diagram><pre class=mermaid>__MERMAID__</pre></div>

<div id=editors></div>
<div id=toast class=toast></div>

<script type=module>
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
const TOKEN = '__TOKEN__';
const editors = document.getElementById('editors');
const toastEl = document.getElementById('toast');

function toast(msg, kind) {
  toastEl.textContent = msg;
  toastEl.className = 'toast show' + (kind === 'err' ? ' err' : '');
  setTimeout(() => { toastEl.className = 'toast'; }, 2200);
}

function buildEditor(file) {
  const div = document.createElement('section');
  div.className = 'editor';
  div.id = 'editor-' + file.id;
  div.innerHTML = `
    <header>
      <code>${file.label}</code>
      <span class=path>${file.path}</span>
      <span class=badge data-role=status>loading…</span>
    </header>
    <textarea spellcheck=false></textarea>
    <footer>
      <button data-action=save class=primary disabled>Save</button>
      <button data-action=revert>Revert to last snapshot</button>
      <span class=spacer></span>
      <label>History:
        <select data-role=history><option value="">(latest snapshot)</option></select>
      </label>
      <button data-action=preview>Preview history</button>
    </footer>`;
  editors.appendChild(div);
  return div;
}

function api(path, opts = {}) {
  const url = path + (path.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(TOKEN);
  return fetch(url, opts).then(async r => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  });
}

async function loadContent(file, ed) {
  const ta = ed.querySelector('textarea');
  const status = ed.querySelector('[data-role=status]');
  const r = await fetch('/api/content?id=' + file.id).then(r => r.json());
  ta.value = r.content;
  ta.dataset.sha = r.sha;
  status.textContent = 'sha ' + r.sha;
  status.classList.remove('dirty');
  ed.querySelector('[data-action=save]').disabled = true;
  await refreshHistory(file, ed);
}

async function refreshHistory(file, ed) {
  const sel = ed.querySelector('[data-role=history]');
  const entries = await fetch('/api/history?id=' + file.id).then(r => r.json());
  sel.innerHTML = '<option value="">(latest snapshot)</option>';
  entries.forEach((e, i) => {
    const o = document.createElement('option');
    o.value = i;
    o.textContent = `${e.ts.replace('T', ' ').replace('+00:00', 'Z')} · ${e.sha}`;
    sel.appendChild(o);
  });
  ed.querySelector('[data-action=revert]').disabled = entries.length === 0;
  ed.dataset.historyCount = entries.length;
}

function wire(file, ed) {
  const ta = ed.querySelector('textarea');
  const status = ed.querySelector('[data-role=status]');
  const saveBtn = ed.querySelector('[data-action=save]');
  ta.addEventListener('input', () => {
    saveBtn.disabled = false;
    status.classList.add('dirty');
    status.textContent = 'unsaved';
  });
  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    try {
      const r = await api('/api/save?id=' + file.id, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content: ta.value, expected_sha: ta.dataset.sha})
      });
      ta.dataset.sha = r.sha;
      status.textContent = 'sha ' + r.sha;
      status.classList.remove('dirty');
      toast('Saved · ' + file.label);
      await refreshHistory(file, ed);
    } catch (e) {
      saveBtn.disabled = false;
      toast('Save failed: ' + e.message, 'err');
    }
  });
  ed.querySelector('[data-action=revert]').addEventListener('click', async () => {
    if (!confirm('Revert ' + file.label + ' to last snapshot?')) return;
    try {
      await api('/api/revert?id=' + file.id, {method: 'POST'});
      await loadContent(file, ed);
      toast('Reverted · ' + file.label);
    } catch (e) {
      toast('Revert failed: ' + e.message, 'err');
    }
  });
  ed.querySelector('[data-action=preview]').addEventListener('click', async () => {
    const sel = ed.querySelector('[data-role=history]');
    const n = sel.value;
    if (n === '') return loadContent(file, ed);
    const txt = await fetch('/api/history/entry?id=' + file.id + '&n=' + n).then(r => r.text());
    ta.value = txt;
    status.textContent = 'previewing #' + n + ' (not saved)';
    status.classList.add('dirty');
    ed.querySelector('[data-action=save]').disabled = false;
  });
}

window.onNodeClick = function(id) {
  const el = document.getElementById('editor-' + id);
  if (!el) return;
  el.scrollIntoView({behavior: 'smooth', block: 'start'});
  el.querySelector('textarea').focus({preventScroll: true});
};

(async () => {
  mermaid.initialize({ startOnLoad: true, theme: 'neutral',
                       securityLevel: 'loose',
                       flowchart: { htmlLabels: true } });
  const files = await fetch('/api/files').then(r => r.json());
  for (const f of files) {
    const ed = buildEditor(f);
    wire(f, ed);
    await loadContent(f, ed);
  }
})();
</script>
</html>
"""


if __name__ == "__main__":
    main()
