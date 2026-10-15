#!/usr/bin/env python3
"""Update scaffold files in a rendered project from the master templates.

Classifies every rendered file into one of three buckets so the right thing
happens automatically — instead of bulldozing the user's customizations.

  template_managed   pure tooling (`.claude/scripts/*.py`) — safe to overwrite
  mergeable          shallow-mergeable JSON (`.atlas`)
  seed / other       everything else — 3-way merged like `git merge`: the base is
                     the project's own template version rendered with the same
                     context, so only what the template changed is applied and
                     local edits stay. Files the template did not change are left
                     alone, files you deleted stay deleted, new template files are
                     added. Where both sides changed the same lines the file gets
                     git conflict markers. Without a base (retrofit, unversioned,
                     unknown version) seeds fall back to `<file>.upstream` sidecars.

Default: report-only (no writes).
  --apply            apply all of the above
  --force            overwrite seeds instead of merging (destructive)
  --include-other    without a base, also sidecar unclassified files

Resolves project dir from cwd; reads .template-meta.json for template name.
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
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
    # Pure doctrine, never user-edited — inert for templates that don't ship it.
    ".claude/SPLITTING.md",
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
    """Render for diffing only. Raises RuntimeError when cookiecutter fails."""
    # mcp_servers only drives post-gen side effects (`mcpick-plus init` is interactive, `claude mcp add`
    # writes global config); no rendered file reads it, so a diff render always uses none.
    context = {**context, "mcp_servers": "none"}
    args = [a for k, v in context.items() for a in (f"{k}={v}",)]
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cookiecutter", str(template_dir), "--no-input", "-o", str(output_dir), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        # A re-render is only compared, never shipped: post-gen hooks must skip network side
        # effects such as registering a new Umami website on every update.
        env={**os.environ, "TEMPLATE_RENDER_TEST": "1"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"cookiecutter failed: {result.stderr.strip()}")
    return next(output_dir.iterdir())


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=TEMPLATES_ROOT, capture_output=True, text=True, check=True).stdout


def _extract(template_name: str, commit: str, workdir: Path) -> Path:
    archive = subprocess.run(["git", "archive", commit, template_name], cwd=TEMPLATES_ROOT,
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(workdir, filter="data")
    return workdir / template_name


def released_template(template_name: str, workdir: Path) -> tuple[str, Path]:
    """Extract the template as it was when its current _version was released.

    The version comes from HEAD, and the files from the commit that introduced that version.
    Commits after the bump and uncommitted edits are unreleased work and never reach a project.
    """
    cc_rel = f"{template_name}/cookiecutter.json"
    version = json.loads(_git("show", f"HEAD:{cc_rel}"))["_version"]
    release = _git("log", "-1", "--format=%H", "-S", f'"_version": "{version}"', "--", cc_rel).strip()
    if not release:
        raise RuntimeError(f"no commit introduces {template_name} _version {version}")
    return version, _extract(template_name, release, workdir)


def base_template(template_name: str, version: str, workdir: Path) -> Path | None:
    """Extract the template as it was released at an older _version: the merge base for a project
    rendered from it. The oldest commit touching the version string introduced it; later ones bumped
    it away. None when no commit has that version (hand-edited or pre-versioning meta)."""
    cc_rel = f"{template_name}/cookiecutter.json"
    commits = _git("log", "--reverse", "--format=%H", "-S", f'"_version": "{version}"', "--", cc_rel).split()
    return _extract(template_name, commits[0], workdir) if commits else None


def write_meta_version(project_dir: Path, meta: dict, version: str) -> None:
    meta["template_version"] = version
    meta["rendered_at"] = datetime.now(timezone.utc).isoformat()
    (project_dir / ".template-meta.json").write_text(json.dumps(meta, indent=2) + "\n")


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


def collect(rendered: Path, project: Path, base: Path | None = None) -> dict[str, list[tuple[str, Path, Path]]]:
    """With a `base` render, files the template did not change and files the project deleted are
    not changes, and seed + other files land in the `merge` bucket."""
    merge_paths = set(_merge_paths())
    buckets: dict[str, list[tuple[str, Path, Path]]] = {
        "template_managed": [], "mergeable": [], "seed": [], "other": [], "merge": [],
    }
    for src in rendered.rglob("*"):
        if not src.is_file():
            continue
        rel = str(src.relative_to(rendered))
        dst = project / rel
        # .template-meta.json always differs (rendered_at); this script owns it on --apply.
        if rel == ".template-meta.json" or _same(src, dst):
            continue
        cls = classify(rel, merge_paths)
        if base is not None and cls in ("seed", "other"):
            old = base / rel
            if _same(src, old) or (old.is_file() and not dst.exists()):
                continue
            cls = "merge"
        buckets[cls].append((rel, src, dst))
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


def merge_file(dst: Path, base_file: Path, src: Path) -> tuple[str, bytes | None]:
    """3-way merge of one file. Returns (outcome, new content); content None means sidecar it."""
    if not dst.exists():
        return "added", src.read_bytes()
    if _same(dst, base_file):
        return "updated", src.read_bytes()
    result = subprocess.run(
        ["git", "merge-file", "-p", "--diff3", "-L", "yours", "-L", "template (old)", "-L", "template (new)",
         str(dst), str(base_file) if base_file.is_file() else os.devnull, str(src)],
        capture_output=True,
    )
    if not 0 <= result.returncode <= 127:  # binary file or git error
        return "sidecar", None
    return ("merged" if result.returncode == 0 else "conflict"), result.stdout


def _apply_merges(items: list, base: Path, dry: bool) -> list[str]:
    """Returns the paths left with conflict markers (or sidecars, for unmergeable files)."""
    unresolved = []
    for rel, src, dst in items:
        outcome, content = merge_file(dst, base / rel, src)
        print(f"  [{outcome}] {rel}")
        if outcome in ("conflict", "sidecar"):
            unresolved.append(rel + (".upstream" if content is None else ""))
        if dry:
            continue
        target = dst if content is not None else dst.with_name(dst.name + ".upstream")
        target.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            shutil.copy2(src, target)
        else:
            target.write_bytes(content)
    return unresolved


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
    if counts["merge"]:
        print(f"  merge:            {counts['merge']:>3}  (3-way merged — your edits kept)")
    if counts["seed"]:
        print(f"  seed:             {counts['seed']:>3}  (no merge base — sidecar by default)")
    if counts["other"]:
        print(f"  other:            {counts['other']:>3}  (unclassified — skipped without --include-other)")
    if not show_diffs:
        return
    for cls in ("merge", "seed", "template_managed", "other"):
        for rel, src, dst in buckets[cls]:
            print(f"\n--- {cls}: {rel} ---")
            print(_short_diff(dst, src, rel) or "(new file)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=".", help="project dir (default: cwd)")
    parser.add_argument("--apply", action="store_true",
                        help="apply changes (tooling overwritten, .atlas merged, everything else 3-way merged)")
    parser.add_argument("--force", action="store_true",
                        help="with --apply, overwrite seed files instead of merging (DESTRUCTIVE — your edits are lost)")
    parser.add_argument("--include-other", action="store_true",
                        help="without a merge base, treat unclassified files as seeds (write sidecars)")
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

    with tempfile.TemporaryDirectory() as tmp:
        upstream_version, released_dir = released_template(template_name, Path(tmp) / "released")
        head = f"{template_name}: local {local_version} -> upstream {upstream_version}"
        print(f"Updating {head}")
        if local_version == upstream_version and not retrofit:
            # Template changes are released by bumping _version (CI enforces the bump). Same version
            # with different files is unreleased work in the templates repo, not an update.
            print("\nUp to date.")
            return
        if retrofit:
            print("note: retrofit project — your local files predate the template.")
            print("      Seeds (CLAUDE.md, Justfile, .gitignore, …) will NOT be overwritten;")
            print("      upstream copies land as `<file>.upstream` for manual merge.")

        try:
            rendered = render_template(released_dir, context, Path(tmp) / "rendered")
        except RuntimeError as e:
            sys.exit(f"error: {e}")
        base = None
        if local_version and not retrofit and not args.force:
            base_dir = base_template(template_name, local_version, Path(tmp) / "base-src")
            try:
                base = base_dir and render_template(base_dir, context, Path(tmp) / "base")
            except RuntimeError as e:
                print(f"note: cannot render merge base {local_version} ({e}); seeds become sidecars")
        if base is None and not retrofit and not args.force:
            print(f"note: no merge base for {local_version}; seeds become `<file>.upstream` sidecars")
        buckets = collect(rendered, project_dir, base)
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
        unresolved = _apply_merges(buckets["merge"], base, dry) if base else []
        applied += len(buckets["merge"])
        if args.include_other:
            applied += _apply_seeds(buckets["other"], dry, args.force)

        if not dry:
            write_meta_version(project_dir, meta, upstream_version)
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
        if unresolved:
            print(f"\n{'Would leave' if dry else 'Left'} {len(unresolved)} file(s) with git conflict markers"
                  " (or .upstream sidecars) — both sides changed the same lines:")
            for rel in unresolved:
                print(f"  {rel}")


if __name__ == "__main__":
    main()
