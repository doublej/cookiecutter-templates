#!/usr/bin/env python3
"""Post-generation hook: clean up Docker files if not included."""
from pathlib import Path

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
INCLUDE_DOCKER = "{{ cookiecutter.include_docker }}".lower() in ("true", "y", "yes", "1")


def rm(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink()


def main():
    if not INCLUDE_DOCKER:
        rm("Dockerfile")
        rm("docker-compose.yml")

    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


if __name__ == "__main__":
    main()
