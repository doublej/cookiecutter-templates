#!/usr/bin/env python3
"""Pre-generation hook: validate project inputs."""
import re
import sys

PROJECT_NAME = "{{ cookiecutter.project_name }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
MODULE_NAME = "{{ cookiecutter.module_name }}"
PACKAGE_ID = "{{ cookiecutter.package_id }}"
MIN_SDK = "{{ cookiecutter.min_sdk_version }}"
TARGET_SDK = "{{ cookiecutter.target_sdk_version }}"

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
MODULE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


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
        print(f"ERROR: project_slug must be kebab-case (e.g. 'my-vr-app'), got: '{PROJECT_SLUG}'")
        sys.exit(1)

    if not MODULE_RE.match(MODULE_NAME):
        print(f"ERROR: module_name must be PascalCase (e.g. 'MyVrApp'), got: '{MODULE_NAME}'")
        sys.exit(1)

    if not PACKAGE_RE.match(PACKAGE_ID):
        print(f"ERROR: package_id must be reverse-DNS (e.g. 'com.example.myapp'), got: '{PACKAGE_ID}'")
        sys.exit(1)

    try:
        min_sdk = int(MIN_SDK)
        target_sdk = int(TARGET_SDK)
    except ValueError:
        print(f"ERROR: min_sdk_version and target_sdk_version must be integers")
        sys.exit(1)

    if min_sdk < 29:
        print(f"ERROR: min_sdk_version must be >= 29 (Quest requires Android 10+), got: {min_sdk}")
        sys.exit(1)

    if target_sdk < min_sdk:
        print(f"ERROR: target_sdk_version ({target_sdk}) must be >= min_sdk_version ({min_sdk})")
        sys.exit(1)


if __name__ == "__main__":
    validate()
