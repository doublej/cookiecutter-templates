#!/usr/bin/env python3
"""Post-generation hook: write meta file and print instructions."""
import json
from datetime import datetime, timezone
from pathlib import Path

COMPONENT_SLUG = "{{ cookiecutter.component_slug }}"
MODULE_NAME = "{{ cookiecutter.module_name }}"

TEMPLATE_VERSION = "{{ cookiecutter._version }}"
TEMPLATE_PATH = r"{{ cookiecutter._template }}"
ATLAS_TYPE = "swift"
ATLAS_FRAMEWORK = "spm"

CONTEXT = {
    "component_name": "{{ cookiecutter.component_name }}",
    "component_slug": COMPONENT_SLUG,
    "module_name": MODULE_NAME,
    "description": "{{ cookiecutter.description }}",
    "deployment_target": "{{ cookiecutter.deployment_target }}",
}


def resolve_template_source():
    """Best-effort source-repo info for .template-meta.json."""
    try:
        tmpl = Path(TEMPLATE_PATH).resolve()
    except Exception:
        return {"type": "unknown"}
    for p in [tmpl, *tmpl.parents]:
        if (p / "tools" / "sync_manifest.json").is_file():
            def _g(*args):
                try:
                    r = subprocess.run(
                        ["git", "-C", str(p), *args],
                        capture_output=True, text=True, timeout=5,
                    )
                    return (r.stdout.strip() or None) if r.returncode == 0 else None
                except Exception:
                    return None
            return {
                "type": "local",
                "path": str(p),
                "git_remote": _g("config", "--get", "remote.origin.url"),
                "git_sha": _g("rev-parse", "HEAD"),
            }
    return {"type": "unknown", "path": str(tmpl)}


def write_meta():
    meta = {
        "template": "swift/stt-component",
        "template_version": TEMPLATE_VERSION,
        "template_source": resolve_template_source(),
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
def write_atlas():
    atlas_path = Path(".atlas")
    data = {
        "description": "{{ cookiecutter.description }}",
        "type": ATLAS_TYPE,
        "framework": ATLAS_FRAMEWORK,
        "archived": False,
    }
    if atlas_path.is_file():
        try:
            existing = json.loads(atlas_path.read_text())
        except Exception:
            existing = {}
        for k, v in data.items():
            existing.setdefault(k, v)
        data = existing
    atlas_path.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    write_meta()
    write_atlas()
    print(f"\n  Component created: {COMPONENT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {COMPONENT_SLUG}")
    print("    just build")
    print("    just test\n")
