#!/usr/bin/env python3
"""Post-generation hook: clean up files, git init, bun install, initial commit."""
import os
import subprocess
from pathlib import Path

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
PROJECT_TYPE = "{{ cookiecutter.project_type }}"
INCLUDE_DOCKER = "{{ cookiecutter.include_docker }}" == "True"


def rm(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink()


def run(cmd: list[str]) -> bool:
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def cleanup_files():
    # Remove CLI files if not a CLI project
    if PROJECT_TYPE != "cli":
        rm("src/cli.ts")

    # Remove logger if not API or Worker
    if PROJECT_TYPE not in ("api", "worker"):
        rm("src/logger.ts")

    # Remove Docker files if not included
    if not INCLUDE_DOCKER:
        rm("Dockerfile")
        rm("docker-compose.yml")


def main():
    cleanup_files()
    run(["git", "init"])
    run(["bun", "install"])
    run(["git", "add", "."])
    run(["git", "commit", "-m", "init: scaffold project"])
    print(f"\ncd {PROJECT_SLUG}")


if __name__ == "__main__":
    main()
