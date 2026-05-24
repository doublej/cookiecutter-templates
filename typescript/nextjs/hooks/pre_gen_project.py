#!/usr/bin/env python3
"""Pre-generation hook: validate project inputs."""
import re
import sys

PROJECT_NAME = "{{ cookiecutter.project_name }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")


def validate():
    if not PROJECT_NAME or len(PROJECT_NAME) > 50:
        print(f"ERROR: project_name must be 1-50 chars, got: '{PROJECT_NAME}'")
        sys.exit(1)

    unsafe = set(r'/\:*?"<>|')
    bad = [c for c in PROJECT_NAME if c in unsafe]
    if bad:
        print(f"ERROR: project_name contains unsafe chars: {''.join(bad)}")
        sys.exit(1)

    if len(PROJECT_SLUG) < 2 or not SLUG_RE.match(PROJECT_SLUG):
        print(f"ERROR: project_slug must be kebab-case (e.g. 'my-project'), got: '{PROJECT_SLUG}'")
        sys.exit(1)


if __name__ == "__main__":
    validate()
