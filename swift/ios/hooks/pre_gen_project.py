#!/usr/bin/env python3
"""Pre-generation hook: validate project inputs."""
import re
import sys

PROJECT_NAME = "{{ cookiecutter.project_name }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
MODULE_NAME = "{{ cookiecutter.module_name }}"

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
MODULE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


def validate():
    if not PROJECT_NAME or len(PROJECT_NAME) > 50:
        print(f"ERROR: project_name must be 1-50 chars, got: '{PROJECT_NAME}'")
        sys.exit(1)

    unsafe = set(r'/\:*?"<>|')
    bad = [c for c in PROJECT_NAME if c in unsafe]
    if bad:
        print(f"ERROR: project_name contains unsafe chars: {''.join(bad)}")
        sys.exit(1)

    if not SLUG_RE.match(PROJECT_SLUG):
        print(f"ERROR: project_slug must be kebab-case (e.g. 'my-app'), got: '{PROJECT_SLUG}'")
        sys.exit(1)

    if not MODULE_RE.match(MODULE_NAME):
        print(f"ERROR: module_name must be PascalCase (e.g. 'MyApp'), got: '{MODULE_NAME}'")
        sys.exit(1)


if __name__ == "__main__":
    validate()
