#!/usr/bin/env python3
"""Render and smoke-test all cookiecutter templates with multiple context variants."""
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEMPLATES: dict[str, list[dict]] = {
    "python/fastapi": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "python/flask": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "python/cli": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "typescript/node-api": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "typescript/node-cli": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "typescript/node-lib": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "typescript/node-worker": [
        {"worker_type": "simple"},
        {"worker_type": "cron"},
        {"worker_type": "long-running"},
        {"worker_type": "simple", "mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "typescript/sveltekit": [
        {"include_tracking": "n"},
        {"include_tracking": "y"},
        {"include_tracking": "n", "mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "typescript/react": [
        {"include_tracking": "n"},
        {"include_tracking": "y"},
        {"include_tracking": "n", "mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "swift/ios": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "swift/macos": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "legacy/cookiecutter-uv": [
        {"layout": "flat"},
        {"layout": "src"},
        {"layout": "flat", "dockerfile": "y"},
        {"layout": "flat", "mkdocs": "y"},
        {"layout": "flat", "mcp_servers": "standard", "mcp_scope": "project"},
    ],
}


def find_templates() -> dict[str, Path]:
    """Discover templates by finding cookiecutter.json files."""
    found = {}
    for template_dir, _ in TEMPLATES.items():
        cc_json = ROOT / template_dir / "cookiecutter.json"
        if cc_json.exists():
            found[template_dir] = ROOT / template_dir
    return found


def load_defaults(template_path: Path) -> dict:
    """Load default context from cookiecutter.json."""
    cc_json = template_path / "cookiecutter.json"
    with open(cc_json) as f:
        raw = json.load(f)
    defaults = {}
    for key, val in raw.items():
        if isinstance(val, list):
            defaults[key] = val[0]
        else:
            defaults[key] = val
    return defaults


def render_template(template_path: Path, context: dict, output_dir: Path) -> Path:
    """Render a template with cookiecutter API into output_dir."""
    from cookiecutter.main import cookiecutter

    result = cookiecutter(
        str(template_path),
        no_input=True,
        extra_context=context,
        output_dir=str(output_dir),
    )
    return Path(result)


def has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_smoke(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run a smoke command, return (success, output)."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def smoke_python(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    src_dir = project_dir / "src"
    if src_dir.exists():
        ok, out = run_smoke([sys.executable, "-m", "compileall", "src/"], project_dir)
        results.append(("compileall", ok, out))
    return results


def smoke_typescript(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("bun"):
        results.append(("bun install", False, "bun not found, skipping"))
        return results
    ok, out = run_smoke(["bun", "install"], project_dir)
    results.append(("bun install", ok, out))
    if not ok:
        return results
    for script in ["lint", "build", "test"]:
        pkg = json.loads((project_dir / "package.json").read_text())
        if script in pkg.get("scripts", {}):
            ok, out = run_smoke(["bun", "run", script], project_dir)
            results.append((f"bun run {script}", ok, out))
            if not ok:
                break
    return results


def smoke_swift(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("swift"):
        results.append(("swift build", False, "swift not found, skipping"))
        return results
    if platform.system() != "Darwin":
        results.append(("swift build", False, "Swift templates require macOS, skipping"))
        return results
    ok, out = run_smoke(["swift", "build"], project_dir)
    results.append(("swift build", ok, out))
    return results


def get_smoke_fn(template_name: str):
    if template_name.startswith("python/") or template_name.startswith("legacy/"):
        return smoke_python
    if template_name.startswith("typescript/"):
        return smoke_typescript
    if template_name.startswith("swift/"):
        return smoke_swift
    return lambda _: []


def main():
    templates = find_templates()
    if not templates:
        print("No templates found!")
        sys.exit(1)

    missing = set(TEMPLATES.keys()) - set(templates.keys())
    if missing:
        print(f"Warning: templates not found: {', '.join(sorted(missing))}")

    total = 0
    passed = 0
    failed_list = []

    for name, template_path in sorted(templates.items()):
        variants = TEMPLATES.get(name, [{}])
        defaults = load_defaults(template_path)
        smoke_fn = get_smoke_fn(name)

        for i, overrides in enumerate(variants):
            variant_label = f"{name} (variant {i})" if len(variants) > 1 else name
            context = {**defaults, **overrides}
            total += 1

            print(f"\n{'='*60}")
            print(f"Template: {variant_label}")
            print(f"Context overrides: {overrides or 'defaults'}")
            print(f"{'='*60}")

            with tempfile.TemporaryDirectory() as tmp:
                try:
                    project_dir = render_template(template_path, context, Path(tmp))
                    print(f"  Rendered to: {project_dir.name}")
                except Exception as e:
                    print(f"  RENDER FAILED: {e}")
                    failed_list.append((variant_label, f"render: {e}"))
                    continue

                smoke_results = smoke_fn(project_dir)
                variant_ok = True
                for check_name, ok, output in smoke_results:
                    status = "PASS" if ok else "FAIL"
                    print(f"  [{status}] {check_name}")
                    if not ok:
                        variant_ok = False
                        for line in output.strip().splitlines()[-5:]:
                            print(f"    {line}")

                if variant_ok:
                    print(f"  PASSED")
                    passed += 1
                else:
                    failed_list.append((variant_label, "smoke test"))

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed")
    if failed_list:
        print(f"\nFailed:")
        for name, reason in failed_list:
            print(f"  - {name}: {reason}")
        sys.exit(1)
    else:
        print("All templates passed!")


if __name__ == "__main__":
    main()
