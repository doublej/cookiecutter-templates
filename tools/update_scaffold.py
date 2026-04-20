#!/usr/bin/env python3
"""Update scaffold files in a rendered project from the master templates."""
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD_FILES = [".gitignore", ".quality.json", "agent.md", "CLAUDE.md", "Justfile"]
MANIFEST = TEMPLATES_ROOT / "tools" / "sync_manifest.json"


def _merge_paths() -> list[str]:
    try:
        return json.loads(MANIFEST.read_text()).get("merge_paths", {}).get("files", [])
    except Exception:
        return []


def _shallow_merge_json(local_path: Path, upstream_path: Path) -> tuple[bool, str]:
    """Shallow-merge upstream JSON into local, preserving local values.

    Returns (changed, merged_text). changed=True when the merge adds fields
    missing locally; existing local values are never overwritten.
    """
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
        print("error: .template-meta.json not found in", project_dir, file=sys.stderr)
        sys.exit(1)
    return json.loads(meta_path.read_text())


def render_template(template_dir: Path, context: dict, output_dir: Path) -> Path:
    args = [a for k, v in context.items() for a in (f"{k}={v}",)]
    result = subprocess.run(
        ["cookiecutter", str(template_dir), "--no-input", "-o", str(output_dir), *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("error: cookiecutter failed:", result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    rendered = next(output_dir.iterdir())
    return rendered


def diff_file(old_path: Path, new_path: Path, label: str) -> list[str]:
    old_lines = old_path.read_text().splitlines(keepends=True) if old_path.exists() else []
    new_lines = new_path.read_text().splitlines(keepends=True)
    return list(unified_diff(old_lines, new_lines, fromfile=f"a/{label}", tofile=f"b/{label}"))


def _upstream_version(template_dir: Path) -> str | None:
    cc = template_dir / "cookiecutter.json"
    if not cc.is_file():
        return None
    try:
        return json.loads(cc.read_text()).get("_version")
    except Exception:
        return None


def main():
    apply = "--apply" in sys.argv
    project_dir = Path.cwd()

    meta = load_meta(project_dir)
    template_name = meta["template"]
    context = meta["context"]
    local_version = meta.get("template_version")

    template_dir = TEMPLATES_ROOT / template_name
    if not template_dir.exists():
        print(f"error: template not found: {template_dir}", file=sys.stderr)
        sys.exit(1)

    upstream_version = _upstream_version(template_dir)
    if local_version and upstream_version:
        print(f"Updating {template_name}: local {local_version} -> upstream {upstream_version}")
    elif upstream_version:
        print(f"Updating {template_name}: upstream {upstream_version}")
    else:
        print(f"Updating {template_name}")

    with tempfile.TemporaryDirectory() as tmp:
        rendered = render_template(template_dir, context, Path(tmp))

        changes: list[tuple[str, list[str]]] = []
        for fname in SCAFFOLD_FILES:
            src = rendered / fname
            if not src.exists():
                continue
            dst = project_dir / fname
            diff = diff_file(dst, src, fname)
            if diff:
                changes.append((fname, diff))

        merges: list[tuple[str, str]] = []
        for fname in _merge_paths():
            src = rendered / fname
            if not src.is_file():
                continue
            dst = project_dir / fname
            changed, merged_text = _shallow_merge_json(dst, src)
            if changed:
                merges.append((fname, merged_text))

        if not changes and not merges and local_version == upstream_version:
            print("Up to date.")
            return
        if not changes and not merges:
            print("scaffold files are up to date")
        else:
            for fname, diff in changes:
                print(f"--- {fname} ---")
                sys.stdout.writelines(diff)
                print()
            for fname, _ in merges:
                print(f"--- {fname} (merge: new fields will be added; your values preserved) ---")
                print()

        if apply:
            for fname, _ in changes:
                src = rendered / fname
                shutil.copy2(src, project_dir / fname)
                print(f"  updated: {fname}")
            for fname, merged_text in merges:
                (project_dir / fname).write_text(merged_text)
                print(f"  merged: {fname}")
            if upstream_version:
                meta["template_version"] = upstream_version
            meta["rendered_at"] = datetime.now(timezone.utc).isoformat()
            (project_dir / ".template-meta.json").write_text(
                json.dumps(meta, indent=2) + "\n"
            )
            print(f"  updated: .template-meta.json")
            n = len(changes) + len(merges) + 1
            print(f"\n{n} file(s) updated")
        elif changes or merges:
            total = len(changes) + len(merges)
            print(f"{total} file(s) differ — run with --apply to update")


if __name__ == "__main__":
    main()
