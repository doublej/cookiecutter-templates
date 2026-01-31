#!/usr/bin/env python3
"""Inject Umami tracking snippet into a rendered project.

Usage:
    python tools/inject_tracking.py <project_dir> <umami_url> <website_id>

The script finds HTML files with <!-- TRACKING_PLACEHOLDER --> and replaces
the placeholder with the Umami tracking script tag.
"""
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\s*<!--\s*TRACKING_PLACEHOLDER\s*-->\s*\n?")


def inject(project_dir: Path, umami_url: str, website_id: str) -> int:
    snippet = f'<script defer src="{umami_url}/script.js" data-website-id="{website_id}"></script>'
    count = 0

    for html_file in project_dir.rglob("*.html"):
        content = html_file.read_text()
        if "TRACKING_PLACEHOLDER" not in content:
            continue

        updated = PLACEHOLDER_RE.sub(f"\n    {snippet}\n", content)
        html_file.write_text(updated)
        print(f"  Injected tracking into {html_file.relative_to(project_dir)}")
        count += 1

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
        print("  No TRACKING_PLACEHOLDER found in any HTML files")
    else:
        print(f"  Injected tracking into {count} file(s)")


if __name__ == "__main__":
    main()
