#!/usr/bin/env python3
"""Post-generation hook: clean up conditional files."""
from pathlib import Path


PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
PROJECT_TYPE = "{{ cookiecutter.project_type }}"
INCLUDE_DOCKER = "{{ cookiecutter.include_docker }}".lower() in ("true", "y", "yes", "1")


def rm(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink()


def cleanup_files():
    if PROJECT_TYPE != "cli":
        rm("src/cli.ts")

    if PROJECT_TYPE not in ("api", "worker"):
        rm("src/logger.ts")

    if not INCLUDE_DOCKER:
        rm("Dockerfile")
        rm("docker-compose.yml")


def print_getting_started():
    print(f"\n  Project created: {PROJECT_SLUG}")
    print(f"  Type: {PROJECT_TYPE}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


def main():
    cleanup_files()
    print_getting_started()


if __name__ == "__main__":
    main()
