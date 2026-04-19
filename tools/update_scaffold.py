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

        if not changes and local_version == upstream_version:
            print("Up to date.")
            return
        if not changes:
            print("scaffold files are up to date")
        else:
            for fname, diff in changes:
                print(f"--- {fname} ---")
                sys.stdout.writelines(diff)
                print()

        if apply:
            for fname, _ in changes:
                src = rendered / fname
                shutil.copy2(src, project_dir / fname)
                print(f"  updated: {fname}")
            if upstream_version:
                meta["template_version"] = upstream_version
            meta["rendered_at"] = datetime.now(timezone.utc).isoformat()
            (project_dir / ".template-meta.json").write_text(
                json.dumps(meta, indent=2) + "\n"
            )
            print(f"  updated: .template-meta.json")
            n = len(changes) + 1
            print(f"\n{n} file(s) updated")
        elif changes:
            print(f"{len(changes)} file(s) differ — run with --apply to update")


if __name__ == "__main__":
    main()
