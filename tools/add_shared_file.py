#!/usr/bin/env python3
"""Copy a new file into every template in a scope and register it in sync_manifest.json.

Without this, adding one cross-family file means hand-pasting it into up to 19
`{{cookiecutter.project_slug}}/` directories and manually editing the manifest.

Usage:
    uv run tools/add_shared_file.py <source_file> <relative_dest_path> --scope cross_family
    uv run tools/add_shared_file.py <source_file> <relative_dest_path> --scope typescript
    uv run tools/add_shared_file.py <source_file> <relative_dest_path> --templates python/cli,go/api

--scope cross_family   copy into every template across every family, register in
                        manifest["cross_family"]["identical_files"]
--scope <family>       copy into every template in that family, register in
                        manifest["families"][family]["identical_files"]
--templates a,b,c      explicit template list, no manifest registration (ad hoc set)

Does not bump versions or run checks — run bump_version.py per changed template and
sync_check.py afterward.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "sync_manifest.json"


def all_family_templates(manifest: dict) -> list[str]:
    # Same discovery as sync_check.py's cross-family check: templates outside any
    # family (android/quest-vr, typescript/raycast-extension) still get cross-family files.
    exclude = set(manifest.get("cross_family", {}).get("exclude_templates", []))
    discovered = sorted(p.parent.relative_to(ROOT).as_posix() for p in ROOT.glob("*/*/cookiecutter.json"))
    return [t for t in discovered if t not in exclude]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source_file")
    parser.add_argument("relative_dest_path")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scope", help="'cross_family' or a family name (e.g. 'typescript')")
    group.add_argument("--templates", help="comma-separated template list, no registration")
    args = parser.parse_args()

    source = Path(args.source_file)
    if not source.is_file():
        raise SystemExit(f"error: source file not found: {source}")
    content = source.read_bytes()

    manifest = json.loads(MANIFEST.read_text())

    if args.templates:
        templates = args.templates.split(",")
        registered_in = None
    elif args.scope == "cross_family":
        templates = all_family_templates(manifest)
        registered_in = manifest["cross_family"]["identical_files"]
    elif args.scope in manifest["families"]:
        templates = manifest["families"][args.scope]["templates"]
        registered_in = manifest["families"][args.scope]["identical_files"]
    else:
        raise SystemExit(f"error: unknown scope '{args.scope}' (known families: {', '.join(manifest['families'])}, or 'cross_family')")

    changed = []
    for tmpl in templates:
        dest = ROOT / tmpl / args.relative_dest_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() == content:
            continue
        dest.write_bytes(content)
        changed.append(tmpl)

    if registered_in is not None and args.relative_dest_path not in registered_in:
        registered_in.append(args.relative_dest_path)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"registered {args.relative_dest_path} in manifest")

    print(f"wrote to {len(templates)} template(s), {len(changed)} changed:")
    for tmpl in changed:
        print(f"  {tmpl}")
    if changed:
        print("\nnext: bump_version.py for each changed template, then sync_check.py")


if __name__ == "__main__":
    main()
