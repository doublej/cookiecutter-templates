#!/usr/bin/env python3
"""Post-generation hook: git init, bun install, optional Umami tracking."""
import os
import subprocess
import sys
from pathlib import Path

UMAMI_CLI = Path.home() / "Documents/development/python/tracking/umami.py"
PROJECT_DIR = Path(os.path.realpath(os.path.curdir))
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"


def run(cmd: list[str]) -> bool:
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def setup_tracking():
    html_file = PROJECT_DIR / "src" / "app.html"

    if "{{ cookiecutter.include_tracking }}" != "y":
        content = html_file.read_text()
        content = content.replace("\t\t<!-- TRACKING_PLACEHOLDER -->\n", "")
        html_file.write_text(content)
        return

    if not UMAMI_CLI.exists():
        print(f"ERROR: Umami CLI not found at {UMAMI_CLI}")
        sys.exit(1)

    domain = "{{ cookiecutter.project_slug }}.local"
    name = "{{ cookiecutter.project_name }}"

    result = subprocess.run(
        ["uv", "run", "python", str(UMAMI_CLI), "add", domain, name],
        capture_output=True,
        text=True,
        cwd=UMAMI_CLI.parent,
    )

    if result.returncode != 0:
        print(f"ERROR: Failed to create Umami site:\n{result.stderr}")
        sys.exit(1)

    output = result.stdout
    tracking_id = ""
    script_url = ""

    for line in output.splitlines():
        if line.startswith("ID:"):
            tracking_id = line.split(":", 1)[1].strip()
        if 'src="' in line:
            start = line.find('src="') + 5
            end = line.find('"', start)
            script_url = line[start:end]

    if not tracking_id or not script_url:
        print(f"ERROR: Could not parse Umami output:\n{output}")
        sys.exit(1)

    snippet = f'<script defer src="{script_url}" data-website-id="{tracking_id}"></script>'

    content = html_file.read_text()
    content = content.replace("<!-- TRACKING_PLACEHOLDER -->", snippet)
    html_file.write_text(content)

    print(f"Umami tracking added: {name} (ID: {tracking_id})")


def main():
    setup_tracking()
    run(["git", "init"])
    run(["bun", "install"])
    run(["git", "add", "."])
    run(["git", "commit", "-m", "init: scaffold project"])
    print(f"\ncd {PROJECT_SLUG}")


if __name__ == "__main__":
    main()
