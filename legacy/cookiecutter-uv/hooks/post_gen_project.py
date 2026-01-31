#!/usr/bin/env python
"""Post-generation hook: clean up conditional files and directories."""
from __future__ import annotations

import os
import shutil

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath: str) -> None:
    path = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.exists(path):
        os.remove(path)


def remove_dir(filepath: str) -> None:
    path = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.isdir(path):
        shutil.rmtree(path)


def move_file(filepath: str, target: str) -> None:
    src = os.path.join(PROJECT_DIRECTORY, filepath)
    dst = os.path.join(PROJECT_DIRECTORY, target)
    if os.path.exists(src):
        os.rename(src, dst)


def move_dir(src: str, target: str) -> None:
    src_path = os.path.join(PROJECT_DIRECTORY, src)
    dst_path = os.path.join(PROJECT_DIRECTORY, target)
    if os.path.isdir(src_path):
        shutil.move(src_path, dst_path)


LICENSE_FILES = ["LICENSE_MIT", "LICENSE_BSD", "LICENSE_ISC", "LICENSE_APACHE", "LICENSE_GPL"]

LICENSE_MAP = {
    "MIT license": "LICENSE_MIT",
    "BSD license": "LICENSE_BSD",
    "ISC license": "LICENSE_ISC",
    "Apache Software License 2.0": "LICENSE_APACHE",
    "GNU General Public License v3": "LICENSE_GPL",
}


def cleanup_github_actions():
    if "{{cookiecutter.include_github_actions}}" != "y":
        remove_dir(".github")
    else:
        if "{{cookiecutter.mkdocs}}" != "y" and "{{cookiecutter.publish_to_pypi}}" == "n":
            remove_file(".github/workflows/on-release-main.yml")


def cleanup_optional_features():
    if "{{cookiecutter.mkdocs}}" != "y":
        remove_dir("docs")
        remove_file("mkdocs.yml")

    if "{{cookiecutter.dockerfile}}" != "y":
        remove_file("Dockerfile")

    if "{{cookiecutter.codecov}}" != "y":
        remove_file("codecov.yaml")
        if "{{cookiecutter.include_github_actions}}" == "y":
            remove_file(".github/workflows/validate-codecov-config.yml")

    if "{{cookiecutter.devcontainer}}" != "y":
        remove_dir(".devcontainer")


def handle_license():
    selected = "{{cookiecutter.open_source_license}}"
    keep_file = LICENSE_MAP.get(selected)

    if keep_file:
        move_file(keep_file, "LICENSE")
        for f in LICENSE_FILES:
            if f != keep_file:
                remove_file(f)
    else:
        for f in LICENSE_FILES:
            remove_file(f)


def handle_layout():
    if "{{cookiecutter.layout}}" == "src":
        src_dir = os.path.join(PROJECT_DIRECTORY, "src")
        if os.path.isdir(src_dir):
            remove_dir("src")
        move_dir("{{cookiecutter.project_slug}}", os.path.join("src", "{{cookiecutter.project_slug}}"))


def print_getting_started():
    slug = "{{cookiecutter.project_slug}}"
    print(f"\n  Project created: {slug}\n")
    print("  Getting started:")
    print(f"    cd {slug}")
    print("    uv sync")
    print("    uv run pytest\n")


if __name__ == "__main__":
    cleanup_github_actions()
    cleanup_optional_features()
    handle_license()
    handle_layout()
    print_getting_started()
