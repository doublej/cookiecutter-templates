#!/usr/bin/env python3
"""Post-generation hook: clean up tracking placeholder, write meta."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(os.path.realpath(os.path.curdir))
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
INCLUDE_TRACKING = "{{ cookiecutter.include_tracking }}"

CONTEXT = {
    "project_name": "{{ cookiecutter.project_name }}",
    "project_slug": PROJECT_SLUG,
    "description": "{{ cookiecutter.description }}",
    "author": "{{ cookiecutter.author }}",
    "include_tracking": INCLUDE_TRACKING,
}


def cleanup_tracking():
    html_file = PROJECT_DIR / "src" / "app.html"
    if not html_file.exists():
        return

    if INCLUDE_TRACKING != "y":
        content = html_file.read_text()
        content = content.replace("\t\t<!-- TRACKING_PLACEHOLDER -->\n", "")
        html_file.write_text(content)
        return

    print("  Note: tracking placeholder left in src/app.html")
    print("  Run tools/inject_tracking.py to inject Umami tracking")


def write_meta():
    meta = {
        "template": "typescript/sveltekit",
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)


def main():
    cleanup_tracking()
    write_meta()
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


if __name__ == "__main__":
    main()
