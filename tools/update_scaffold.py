#!/usr/bin/env python3
"""Update scaffold files in a rendered project from the master templates.

Classifies every rendered file into one of three buckets so the right thing
happens automatically — instead of bulldozing the user's customizations.

  template_managed   pure tooling (`.claude/scripts/*.py`) — safe to overwrite
  mergeable          shallow-mergeable JSON (`.atlas`)
  seed               render-once files (CLAUDE.md, Justfile, .gitignore, ...)
                     — diffed only; with --apply we write the upstream copy to
                     `<file>.upstream` so you can merge manually

Default: report-only (no writes).
  --apply            apply template_managed + mergeable; sidecar seeds
  --force            also overwrite seeds (the old destructive behaviour)
  --include-other    treat unclassified files as seeds (sidecar them too)

Resolves project dir from cwd; reads .template-meta.json for template name.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = TEMPLATES_ROOT / "tools" / "sync_manifest.json"

# Pattern lists (relative paths from the project root). Order matters: first
# match wins. Patterns use fnmatch (POSIX-style globs, *, **, ?).
TEMPLATE_MANAGED_PATTERNS = [
    ".claude/scripts/*.py",
]

SEED_FILE_PATTERNS = [
    "CLAUDE.md", "README.md", "agent.md", "Justfile",
    ".gitignore", ".quality.json", ".swiftlint.yml",
    ".claude/settings.json",
    # language manifests / configs — never overwrite user edits
    "pyproject.toml", "package.json", "Cargo.toml", "Package.swift",
    "build.gradle.kts", "settings.gradle.kts", "gradle.properties",
    "biome.json", "tsconfig.json", "vite.config.ts", "vitest.config.ts",
    "next.config.ts", "svelte.config.js", "app/build.gradle.kts",
    "app/src/main/AndroidManifest.xml", "app/src/main/cpp/CMakeLists.txt",
    # source seed files
    "src/**/*.py", "src/**/*.ts", "src/**/*.tsx", "src/**/*.rs",
    "src/**/*.swift", "app/src/main/cpp/*.cpp", "app/src/main/cpp/*.h",
]


def _merge_paths() -> list[str]:
    try:
        return json.loads(MANIFEST.read_text()).get("merge_paths", {}).get("files", [])
    except Exception:
        return []


def _shallow_merge_json(local_path: Path, upstream_path: Path) -> tuple[bool, str]:
    try:
        local = json.loads(local_path.read_text()) if local_path.is_file() else {}
        upstream = json.loads(upstream_path.read_text())
    except Exception:
        return False, ""
    if not isinstance(local, dict) or not isinstance(upstream, dict):
        return False, ""
    merged = dict(local)
    added = []
    for k, v in upstream.items():
        if k not in merged:
            merged[k] = v
            added.append(k)
    if not added:
        return False, ""
    return True, json.dumps(merged, indent=2) + "\n"


def load_meta(project_dir: Path) -> dict:
    meta_path = project_dir / ".template-meta.json"
    if not meta_path.exists():
        print(f"error: .template-meta.json not found in {project_dir}", file=sys.stderr)
        sys.exit(1)
    return json.loads(meta_path.read_text())


def render_template(template_dir: Path, context: dict, output_dir: Path) -> Path:
    args = [a for k, v in context.items() for a in (f"{k}={v}",)]
    result = subprocess.run(
        ["cookiecutter", str(template_dir), "--no-input", "-o", str(output_dir), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"error: cookiecutter failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return next(output_dir.iterdir())


def _upstream_version(template_dir: Path) -> str | None:
    cc = template_dir / "cookiecutter.json"
    if not cc.is_file():
        return None
    try:
        return json.loads(cc.read_text()).get("_version")
    except Exception:
        return None


def classify(rel_path: str, merge_paths: set[str]) -> str:
    if rel_path in merge_paths:
        return "mergeable"
    for pat in TEMPLATE_MANAGED_PATTERNS:
        if fnmatch.fnmatch(rel_path, pat):
            return "template_managed"
    for pat in SEED_FILE_PATTERNS:
        if fnmatch.fnmatch(rel_path, pat):
            return "seed"
    return "other"


def _same(a: Path, b: Path) -> bool:
    if not (a.is_file() and b.is_file()):
        return False
    return a.read_bytes() == b.read_bytes()


def _short_diff(old: Path, new: Path, label: str, max_lines: int = 12) -> str:
    old_lines = old.read_text(errors="replace").splitlines(keepends=True) if old.is_file() else []
    new_lines = new.read_text(errors="replace").splitlines(keepends=True)
    diff = list(unified_diff(old_lines, new_lines, fromfile=f"a/{label}",
                             tofile=f"b/{label}", n=2))
    if len(diff) > max_lines:
        diff = diff[:max_lines] + [f"... ({len(diff) - max_lines} more lines)\n"]
    return "".join(diff)


def collect(rendered: Path, project: Path) -> dict[str, list[tuple[str, Path, Path]]]:
    merge_paths = set(_merge_paths())
    buckets: dict[str, list[tuple[str, Path, Path]]] = {
        "template_managed": [], "mergeable": [], "seed": [], "other": [],
    }
    for src in rendered.rglob("*"):
        if not src.is_file():
            continue
        rel = str(src.relative_to(rendered))
        dst = project / rel
        if _same(src, dst):
            continue
        buckets[classify(rel, merge_paths)].append((rel, src, dst))
    return buckets


def _apply_template_managed(items: list, dry: bool) -> int:
    n = 0
    for rel, src, dst in items:
        action = "would update" if dry else "updated"
        print(f"  [tool] {action}: {rel}")
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        n += 1
    return n


def _apply_mergeable(items: list, dry: bool) -> int:
    n = 0
    for rel, src, dst in items:
        changed, merged = _shallow_merge_json(dst, src)
        if not changed:
            continue
        action = "would merge" if dry else "merged"
        print(f"  [merge] {action}: {rel}")
        if not dry:
            dst.write_text(merged)
        n += 1
    return n


def _apply_seeds(items: list, dry: bool, force: bool) -> int:
    """Without --force: write `<file>.upstream` sidecars. With --force: overwrite."""
    n = 0
    for rel, src, dst in items:
        if force:
            action = "would overwrite (--force)" if dry else "overwrote (--force)"
            print(f"  [seed] {action}: {rel}")
            if not dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        else:
            sidecar = dst.with_name(dst.name + ".upstream")
            action = "would write sidecar" if dry else "wrote sidecar"
            print(f"  [seed] {action}: {rel} (-> {rel}.upstream)")
            if not dry:
                sidecar.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, sidecar)
        n += 1
    return n


def _print_summary(buckets: dict, show_diffs: bool) -> None:
    counts = {k: len(v) for k, v in buckets.items()}
    total = sum(counts.values())
    if total == 0:
        return
    print(f"\nChanges detected: {total} file(s)")
    print(f"  template_managed: {counts['template_managed']:>3}  (safe to overwrite — tooling)")
    print(f"  mergeable:        {counts['mergeable']:>3}  (shallow JSON merge)")
    print(f"  seed:             {counts['seed']:>3}  (your customizations — sidecar by default)")
    if counts["other"]:
        print(f"  other:            {counts['other']:>3}  (unclassified — skipped without --include-other)")
    if not show_diffs:
        return
    for cls in ("seed", "template_managed", "other"):
        for rel, src, dst in buckets[cls]:
            print(f"\n--- {cls}: {rel} ---")
            print(_short_diff(dst, src, rel) or "(new file)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=".", help="project dir (default: cwd)")
    parser.add_argument("--apply", action="store_true",
                        help="apply changes (template_managed + mergeable in place; seeds → sidecar)")
    parser.add_argument("--force", action="store_true",
                        help="with --apply, also overwrite seed files (DESTRUCTIVE — your edits are lost)")
    parser.add_argument("--include-other", action="store_true",
                        help="treat unclassified files as seeds (write sidecars)")
    parser.add_argument("--diffs", action="store_true",
                        help="print short diffs for each changed file")
    args = parser.parse_args()

    project_dir = Path(args.path).resolve()
    meta = load_meta(project_dir)
    template_name = meta["template"]
    context = meta.get("context", {})
    local_version = meta.get("template_version")
    retrofit = bool(meta.get("retrofit"))

    template_dir = TEMPLATES_ROOT / template_name
    if not template_dir.exists():
        print(f"error: template not found: {template_dir}", file=sys.stderr)
        sys.exit(1)

    upstream_version = _upstream_version(template_dir)
    head = f"{template_name}: local {local_version} -> upstream {upstream_version}"
    print(f"Updating {head}")
    if retrofit:
        print("note: retrofit project — your local files predate the template.")
        print("      Seeds (CLAUDE.md, Justfile, .gitignore, …) will NOT be overwritten;")
        print("      upstream copies land as `<file>.upstream` for manual merge.")

    with tempfile.TemporaryDirectory() as tmp:
        rendered = render_template(template_dir, context, Path(tmp))
        buckets = collect(rendered, project_dir)
        if not args.include_other:
            buckets["other"] = []  # drop from apply, still show in summary
        _print_summary(buckets, show_diffs=args.diffs)

        n_changed = sum(len(v) for v in buckets.values())
        if n_changed == 0 and local_version == upstream_version:
            print("\nUp to date.")
            return

        dry = not args.apply
        applied = 0
        applied += _apply_template_managed(buckets["template_managed"], dry)
        applied += _apply_mergeable(buckets["mergeable"], dry)
        applied += _apply_seeds(buckets["seed"], dry, args.force)
        if args.include_other:
            applied += _apply_seeds(buckets["other"], dry, args.force)

        if not dry and upstream_version:
            meta["template_version"] = upstream_version
            meta["rendered_at"] = datetime.now(timezone.utc).isoformat()
            (project_dir / ".template-meta.json").write_text(
                json.dumps(meta, indent=2) + "\n"
            )
            print(f"  updated: .template-meta.json -> {upstream_version}")
            applied += 1

        if dry:
            seed_count = len(buckets["seed"])
            tail = " (use --apply; add --diffs for previews)"
            if seed_count and not args.force:
                tail = " (use --apply; seed files become .upstream sidecars unless --force)"
            print(f"\nReport-only: {applied} file(s) would change.{tail}")
        else:
            print(f"\nApplied: {applied} file(s) changed.")
            if buckets["seed"] and not args.force:
                print("\nNext steps for each <file>.upstream sidecar:")
                print("  diff -u <file> <file>.upstream  # review")
                print("  # cherry-pick what you want into <file>, then:")
                print("  rm <file>.upstream")


if __name__ == "__main__":
    main()
