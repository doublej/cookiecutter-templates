#!/usr/bin/env python3
"""Inject the Umami tracking snippet into a rendered project.

Usage:
    python tools/inject_tracking.py <project_dir> <umami_url> <website_id>

Replaces the tracking placeholder with a Umami <script> tag, preserving the
placeholder's indentation. Two placeholder forms are recognised:

    HTML  (.html):  <!-- TRACKING_PLACEHOLDER -->
    JSX   (.tsx):   {/* TRACKING_PLACEHOLDER */}      -> self-closing <script ... />
"""
import re
import sys
from pathlib import Path

HTML_RE = re.compile(r"(?m)^([ \t]*)<!--\s*TRACKING_PLACEHOLDER\s*-->[ \t]*\n?")
JSX_RE = re.compile(r"(?m)^([ \t]*)\{/\*\s*TRACKING_PLACEHOLDER\s*\*/\}[ \t]*\n?")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".svelte-kit", ".next"}
LINE_WIDTH = 100  # biome.json formatter.lineWidth in the web templates


def _jsx_snippet(indent: str, src: str, website_id: str) -> str:
    """Biome keeps a JSX element on one line only while it fits; past that, one attribute per line."""
    one_line = f'<script defer src="{src}" data-website-id="{website_id}" />'
    if len(indent) + len(one_line) <= LINE_WIDTH:
        return one_line
    pad = indent + "  "
    return f'<script\n{pad}defer\n{pad}src="{src}"\n{pad}data-website-id="{website_id}"\n{indent}/>'


def _inject_file(path: Path, pattern: re.Pattern, snippet, project_dir: Path) -> bool:
    content = path.read_text()
    if "TRACKING_PLACEHOLDER" not in content:
        return False
    updated = pattern.sub(lambda m: f"{m.group(1)}{snippet(m.group(1))}\n", content)
    if updated == content:
        return False
    path.write_text(updated)
    print(f"Umami: injected tracking into {path.relative_to(project_dir)}")
    return True


def inject(project_dir: Path, umami_url: str, website_id: str) -> int:
    src = f"{umami_url}/script.js"
    html_snippet = f'<script defer src="{src}" data-website-id="{website_id}"></script>'
    count = 0
    for path in project_dir.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix == ".html":
            count += _inject_file(path, HTML_RE, lambda _indent: html_snippet, project_dir)
        elif path.suffix == ".tsx":
            count += _inject_file(path, JSX_RE, lambda indent: _jsx_snippet(indent, src, website_id), project_dir)
    return count


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <project_dir> <umami_url> <website_id>")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    umami_url = sys.argv[2].rstrip("/")
    website_id = sys.argv[3]

    if not project_dir.is_dir():
        print(f"ERROR: {project_dir} is not a directory")
        sys.exit(1)

    count = inject(project_dir, umami_url, website_id)
    if count == 0:
        print("Umami: no TRACKING_PLACEHOLDER found in any HTML/TSX files")


if __name__ == "__main__":
    main()
