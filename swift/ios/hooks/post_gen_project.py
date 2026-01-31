#!/usr/bin/env python3
"""Post-generation hook: print getting started instructions."""

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"


if __name__ == "__main__":
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    swift build")
    print("    open Package.swift  # Opens in Xcode\n")
