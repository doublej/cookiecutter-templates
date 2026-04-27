#!/usr/bin/env python3
"""Check that shared files stay in sync within each language family."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "sync_manifest.json"


def load_manifest() -> dict:
    with open(MANIFEST) as f:
        return json.load(f)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def parse_justfile_recipes(path: Path) -> dict[str, str]:
    """Parse a Justfile into {recipe_name: full_block} including attributes."""
    text = path.read_text()
    # Split into blocks: each recipe starts with optional [group(...)] + recipe_name:
    # We match attribute lines + recipe header + indented body
    pattern = re.compile(
        r"^((?:\[.*\]\n)*)"  # optional attribute lines like [group('...')]
        r"^(\w[\w-]*)(?:\s+[^:\n]*)?\s*:\s*(?:[^=\n]*)$"  # recipe name + deps
        r"((?:\n(?:    |\t| ).+)*)",  # indented body lines
        re.MULTILINE,
    )
    recipes = {}
    for m in pattern.finditer(text):
        attrs, name, body = m.group(1), m.group(2), m.group(3)
        recipes[name] = (attrs + name + body).strip()
    return recipes


def check_identical_files(family: str, cfg: dict) -> list[str]:
    """Check that identical_files are byte-for-byte equal across templates."""
    errors = []
    for rel_path in cfg.get("identical_files", []):
        hashes: dict[str, str] = {}
        for tmpl in cfg["templates"]:
            full = ROOT / tmpl / rel_path
            if not full.exists():
                errors.append(f"  {family}: {rel_path} missing in {tmpl}")
                continue
            hashes[tmpl] = file_hash(full)

        unique = set(hashes.values())
        if len(unique) <= 1:
            continue
        errors.append(f"  {family}: {rel_path} differs across templates:")
        for tmpl, h in hashes.items():
            errors.append(f"    {tmpl}: {h}")
    return errors


def check_justfile_recipes(family: str, cfg: dict) -> list[str]:
    """Check that shared Justfile recipes match across templates."""
    errors = []
    shared = cfg.get("justfile_shared_recipes", [])
    if not shared:
        return errors

    exceptions = cfg.get("justfile_exceptions", {})
    justfile_rel = "{{cookiecutter.project_slug}}/Justfile"

    # Parse all Justfiles
    parsed: dict[str, dict[str, str]] = {}
    for tmpl in cfg["templates"]:
        jf = ROOT / tmpl / justfile_rel
        if not jf.exists():
            errors.append(f"  {family}: Justfile missing in {tmpl}")
            continue
        parsed[tmpl] = parse_justfile_recipes(jf)

    if len(parsed) < 2:
        return errors

    # Use first template as reference for each recipe
    templates = list(parsed.keys())
    ref_tmpl = templates[0]

    for recipe in shared:
        skip_tmpls = set()
        for tmpl, exc in exceptions.items():
            if recipe in exc.get("skip_recipes", []):
                skip_tmpls.add(tmpl)

        ref_body = parsed.get(ref_tmpl, {}).get(recipe)
        if ref_body is None and ref_tmpl not in skip_tmpls:
            errors.append(f"  {family}: recipe '{recipe}' missing in {ref_tmpl}")
            continue

        # Find first non-skipped template as actual reference
        actual_ref = None
        for t in templates:
            if t not in skip_tmpls and recipe in parsed.get(t, {}):
                actual_ref = t
                break
        if actual_ref is None:
            continue

        ref_body = parsed[actual_ref][recipe]
        for tmpl in templates:
            if tmpl == actual_ref or tmpl in skip_tmpls:
                continue
            body = parsed.get(tmpl, {}).get(recipe)
            if body is None:
                errors.append(f"  {family}: recipe '{recipe}' missing in {tmpl}")
            elif body != ref_body:
                errors.append(
                    f"  {family}: recipe '{recipe}' differs: "
                    f"{actual_ref} vs {tmpl}"
                )
    return errors


def check_cross_family_files(manifest: dict) -> list[str]:
    """Check that cross_family identical_files match across every non-excluded template."""
    errors: list[str] = []
    cfg = manifest.get("cross_family")
    if not cfg:
        return errors

    exclude = set(cfg.get("exclude_templates", []))
    overrides = cfg.get("slug_dir_overrides", {})
    # Discover every template dir (has a cookiecutter.json), then apply excludes.
    discovered = sorted(
        p.parent.relative_to(ROOT).as_posix()
        for p in ROOT.glob("*/*/cookiecutter.json")
    )
    all_templates = [t for t in discovered if t not in exclude]

    for rel_path in cfg.get("identical_files", []):
        hashes: dict[str, str] = {}
        for tmpl in all_templates:
            slug_dir = overrides.get(tmpl, "{{cookiecutter.project_slug}}")
            full = ROOT / tmpl / rel_path.replace(
                "{{cookiecutter.project_slug}}", slug_dir
            )
            if not full.exists():
                errors.append(f"  cross_family: {rel_path} missing in {tmpl}")
                continue
            hashes[tmpl] = file_hash(full)

        unique = set(hashes.values())
        if len(unique) <= 1:
            continue
        errors.append(f"  cross_family: {rel_path} differs across templates:")
        for tmpl, h in hashes.items():
            errors.append(f"    {tmpl}: {h}")
    return errors


def _git_diff_names(base: str) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, cwd=ROOT, timeout=10,
        )
    except Exception as e:
        raise SystemExit(f"error: git diff failed: {e}")
    if r.returncode != 0:
        raise SystemExit(f"error: git diff {base}...HEAD failed: {r.stderr.strip()}")
    return [line for line in r.stdout.splitlines() if line]


def _version_in_ref(template: str, ref: str) -> str | None:
    path = f"{template}/cookiecutter.json"
    try:
        r = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, text=True, cwd=ROOT, timeout=5,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout).get("_version")
    except Exception:
        return None


def check_versions_bumped(manifest: dict, base: str = "origin/main") -> list[str]:
    """For every template changed vs `base`, require `_version` to bump.

    Intended for CI (--enforce-bumps). Discovers templates via cookiecutter.json
    presence so android/quest-vr is covered too.
    """
    errors: list[str] = []
    changed = _git_diff_names(base)
    if not changed:
        return errors

    discovered = sorted(
        p.parent.relative_to(ROOT).as_posix()
        for p in ROOT.glob("*/*/cookiecutter.json")
    )
    exclude = set(manifest.get("cross_family", {}).get("exclude_templates", []))

    for tmpl in discovered:
        if tmpl in exclude:
            continue
        if not any(f.startswith(tmpl + "/") for f in changed):
            continue
        head_cc = ROOT / tmpl / "cookiecutter.json"
        if not head_cc.is_file():
            continue
        head_version = json.loads(head_cc.read_text()).get("_version")
        base_version = _version_in_ref(tmpl, base)
        if base_version is None:
            # New template — no prior _version to compare; accept.
            continue
        if head_version == base_version:
            errors.append(
                f"  bumps: {tmpl} has file changes vs {base} but _version "
                f"is still {head_version} — run `uv run tools/bump_version.py "
                f"{tmpl} {{major|minor|patch}} \"note\"`"
            )
            continue
        changelog_rel = f"{tmpl}/CHANGELOG.md"
        if changelog_rel not in changed:
            errors.append(
                f"  bumps: {tmpl} bumped _version to {head_version} but "
                f"CHANGELOG.md was not touched — bump_version.py prepends an entry automatically"
            )
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enforce-bumps",
        action="store_true",
        help="Fail when a changed template's cookiecutter.json _version did not bump vs origin/main.",
    )
    parser.add_argument(
        "--bump-base",
        default="origin/main",
        help="Git ref used as the baseline for --enforce-bumps (default: origin/main).",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    all_errors: list[str] = []

    for family, cfg in manifest["families"].items():
        print(f"Checking {family}...")
        errors = check_identical_files(family, cfg)
        errors += check_justfile_recipes(family, cfg)
        if errors:
            all_errors.extend(errors)
            print(f"  FAIL ({len(errors)} issue(s))")
        else:
            print(f"  OK")

    print(f"Checking cross-family...")
    cf_errors = check_cross_family_files(manifest)
    if cf_errors:
        all_errors.extend(cf_errors)
        print(f"  FAIL ({len(cf_errors)} issue(s))")
    else:
        print(f"  OK")

    if args.enforce_bumps:
        print(f"Checking version bumps vs {args.bump_base}...")
        bump_errors = check_versions_bumped(manifest, args.bump_base)
        if bump_errors:
            all_errors.extend(bump_errors)
            print(f"  FAIL ({len(bump_errors)} issue(s))")
        else:
            print(f"  OK")

    if all_errors:
        print(f"\nSync errors found:")
        for e in all_errors:
            print(e)
        sys.exit(1)
    else:
        print(f"\nAll families in sync.")


if __name__ == "__main__":
    main()
