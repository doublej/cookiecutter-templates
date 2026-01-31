#!/usr/bin/env python3
"""Post-generation hook: clean up Docker files, write meta."""
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
INCLUDE_DOCKER = "{{ cookiecutter.include_docker }}".lower() in ("true", "y", "yes", "1")

CONTEXT = {
    "project_name": "{{ cookiecutter.project_name }}",
    "project_slug": PROJECT_SLUG,
    "description": "{{ cookiecutter.description }}",
    "author": "{{ cookiecutter.author }}",
    "include_docker": "{{ cookiecutter.include_docker }}",
}


def rm(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink()


def write_meta():
    meta = {
        "template": "typescript/node-api",
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)


def main():
    if not INCLUDE_DOCKER:
        rm("Dockerfile")
        rm("docker-compose.yml")

    write_meta()
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


if __name__ == "__main__":
    main()
