#!/usr/bin/env python3
"""Post-generation hook: write meta file and print instructions."""
import json
from datetime import datetime, timezone

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"

CONTEXT = {
    "project_name": "{{ cookiecutter.project_name }}",
    "project_slug": PROJECT_SLUG,
    "description": "{{ cookiecutter.description }}",
    "author": "{{ cookiecutter.author }}",
    "python_version": "{{ cookiecutter.python_version }}",
}


def write_meta():
    meta = {
        "template": "python/cli",
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    write_meta()
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    uv sync")
    print(f"    uv run {PROJECT_SLUG} hello\n")
