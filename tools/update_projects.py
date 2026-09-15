#!/usr/bin/env python3
"""Pull released scaffold tooling into every generated project that is behind its template.

Safe to run across all projects without questions:
  - only projects whose .template-meta.json points at this templates repo and whose
    template_version is below the released upstream version
  - renders the released template (update_scaffold.released_template), never unreleased work
  - writes only template-managed tooling (.claude/scripts/*.py) and adds missing keys to .atlas;
    seeds and net-new files stay for `/update-scaffold` inside the project, which the
    SessionStart hook keeps prompting for until they are resolved
  - bumps template_version only when nothing else differs
  - skips a project that is not a git repo, is mid merge/rebase, or has uncommitted changes
    in any file it would write
  - with --apply, commits exactly the files it wrote (`git commit -- <paths>`); never pushes

Default: report only.

Usage:
    python3 tools/update_projects.py [--root ~/dev] [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import update_scaffold as us

PRUNE = {"node_modules", "_archive", ".git", ".build", ".venv", "venv", "dist", "build", ".next",
         ".svelte-kit", "target", "worktrees"}
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply")


def find_projects(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNE and Path(dirpath, d) != us.TEMPLATES_ROOT]
        if ".template-meta.json" in filenames:
            found.append(Path(dirpath))
    return sorted(found)


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def git(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)


def update_project(project: Path, released: dict, tmp: Path, apply: bool) -> str:
    """Return a report line, or `skip:<reason>` for projects that are not worth a line."""
    meta = json.loads((project / ".template-meta.json").read_text())
    template, local = meta.get("template"), meta.get("template_version")
    source = (meta.get("template_source") or {}).get("path")
    if not (template and local and source):
        return "skip:unversioned meta"
    if meta.get("retrofit"):
        return "skip:retrofit (local files predate the template)"
    if Path(source).resolve() != us.TEMPLATES_ROOT or not (us.TEMPLATES_ROOT / template).is_dir():
        return "skip:other templates repo"
    if template not in released:
        released[template] = us.released_template(template, tmp / "released" / template.replace("/", "-"))
    upstream, template_dir = released[template]
    if version_tuple(local) >= version_tuple(upstream):
        return "skip:up to date"

    git_dir = git(project, "rev-parse", "--absolute-git-dir")
    if git_dir.returncode:
        return "skip:not a git repo"
    label = f"{template} {local} -> {upstream}"
    if any((Path(git_dir.stdout.strip()) / marker).exists() for marker in IN_PROGRESS):
        return f"SKIP     {label}  merge/rebase in progress"

    rendered = us.render_template(template_dir, meta.get("context", {}), Path(tempfile.mkdtemp(dir=tmp)))
    buckets = us.collect(rendered, project)
    tools = buckets["template_managed"]
    merges = [item for item in buckets["mergeable"] if us._shallow_merge_json(item[2], item[1])[0]]
    pending = len(buckets["seed"]) + len(buckets["other"])
    touched = [rel for rel, _, _ in tools + merges] + ([".template-meta.json"] if pending == 0 else [])
    label += f"  tooling {len(tools)}, .atlas {len(merges)}, left for /update-scaffold {pending}"
    if not tools and not merges and pending:
        return "skip:only seed changes (hook prompts in the project)"
    if git(project, "status", "--porcelain", "--", *touched).stdout.strip():
        return f"SKIP     {label}  uncommitted changes in those files"
    if not apply:
        return f"PLAN     {label}"

    us._apply_template_managed(tools, dry=False)
    us._apply_mergeable(merges, dry=False)
    if pending == 0:
        us.write_meta_version(project, meta, upstream)
    ignored = set(git(project, "check-ignore", "--", *touched).stdout.splitlines())
    tracked = [rel for rel in touched if rel not in ignored]
    if not tracked:  # `git commit --` without paths would commit whatever else is staged
        return f"APPLIED  {label}  (all gitignored, nothing to commit)"
    added = git(project, "add", "--", *tracked)
    committed = git(project, "commit", "-q", "-m", f"chore: update scaffold tooling to {template} {upstream}",
                    "--", *tracked)
    if added.returncode or committed.returncode:
        return f"UNCOMMITTED {label}  {(added.stderr + committed.stderr).strip()[:160]}"
    return f"APPLIED  {label}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(Path.home() / "dev"), help="where to look for projects")
    parser.add_argument("--apply", action="store_true", help="write the tooling updates and commit them per project")
    args = parser.parse_args()

    skipped: Counter[str] = Counter()
    with tempfile.TemporaryDirectory() as tmp:
        released: dict = {}
        for project in find_projects(Path(args.root).expanduser().resolve()):
            try:
                line = update_project(project, released, Path(tmp), args.apply)
            except Exception as e:  # one broken project must not stop the batch
                line = f"FAILED   {type(e).__name__}: {(str(e).strip().splitlines() or [''])[-1][:160]}"
            if line.startswith("skip:"):
                skipped[line.removeprefix("skip:")] += 1
            else:
                print(f"{line}\n         {project}")
    print("\nNot touched: " + ", ".join(f"{reason} {n}" for reason, n in sorted(skipped.items())))
    if not args.apply:
        print("Report only. Re-run with --apply to write and commit the PLAN lines.")


if __name__ == "__main__":
    main()
