#!/usr/bin/env python3
"""Post-generation hook: clean up tracking placeholder."""
import os
from pathlib import Path

PROJECT_DIR = Path(os.path.realpath(os.path.curdir))
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
INCLUDE_TRACKING = "{{ cookiecutter.include_tracking }}"


def cleanup_tracking():
    html_file = PROJECT_DIR / "src" / "app.html"
    if not html_file.exists():
        return

    if INCLUDE_TRACKING != "y":
        content = html_file.read_text()
        content = content.replace("\t\t<!-- TRACKING_PLACEHOLDER -->\n", "")
        html_file.write_text(content)
        return

    # Leave placeholder for manual setup via tools/inject_tracking.py
    print("  Note: tracking placeholder left in src/app.html")
    print("  Run tools/inject_tracking.py to inject Umami tracking")


def print_getting_started():
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


def main():
    cleanup_tracking()
    print_getting_started()


if __name__ == "__main__":
    main()
