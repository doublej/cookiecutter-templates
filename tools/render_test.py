#!/usr/bin/env python3
"""Render and smoke-test all cookiecutter templates with multiple context variants."""
import json
import platform
import py_compile
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
    "typescript/bun-package": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
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
    "typescript/nextjs": [
        {"include_tracking": "n"},
        {"include_tracking": "y"},
        {"include_tracking": "n", "mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "rust/cli": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "swift/ios": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "swift/macos": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "swift/stt-component": [
        {},
    ],
    "android/quest-vr": [
        {},
        {"graphics_api": "vulkan"},
        {"mcp_servers": "standard", "mcp_scope": "project"},
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


def check_versioning_payload(
    project_dir: Path, template_name: str, template_path: Path
) -> list[tuple[str, bool, str]]:
    """Assert .template-meta.json + .claude payload are shaped correctly."""
    results: list[tuple[str, bool, str]] = []
    legacy = template_name.startswith("legacy/")

    # .template-meta.json with matching template_version
    meta_path = project_dir / ".template-meta.json"
    if not meta_path.is_file():
        results.append(("meta exists", False, f"missing: {meta_path}"))
        return results
    try:
        meta = json.loads(meta_path.read_text())
    except Exception as e:
        results.append(("meta parses", False, f"{e}"))
        return results

    cc = template_path / "cookiecutter.json"
    cc_version = json.loads(cc.read_text()).get("_version")
    if cc_version != meta.get("template_version"):
        results.append((
            "meta version matches cookiecutter._version",
            False,
            f"cookiecutter.json={cc_version!r} meta={meta.get('template_version')!r}",
        ))
        return results
    results.append(("meta shape", True, ""))

    if legacy:
        return results

    settings = project_dir / ".claude" / "settings.json"
    if not settings.is_file():
        results.append((".claude/settings.json exists", False, "missing"))
        return results
    try:
        json.loads(settings.read_text())
    except Exception as e:
        results.append((".claude/settings.json parses", False, f"{e}"))
        return results

    script = project_dir / ".claude" / "scripts" / "check_template_update.py"
    if not script.is_file():
        results.append(("check_template_update.py exists", False, "missing"))
        return results
    try:
        py_compile.compile(str(script), doraise=True)
    except py_compile.PyCompileError as e:
        results.append(("check_template_update.py compiles", False, f"{e}"))
        return results
    results.append((".claude payload", True, ""))
    return results


def smoke_just_fmt(project_dir: Path) -> list[tuple[str, bool, str]]:
    """Verify the rendered Justfile is canonically formatted."""
    if not (project_dir / "Justfile").exists():
        return []
    if not has_command("just"):
        return []
    ok, out = run_smoke(["just", "--fmt", "--check"], project_dir)
    return [("just --fmt --check", ok, out)]


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


def smoke_rust(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("cargo"):
        results.append(("cargo build", False, "cargo not found, skipping"))
        return results
    ok, out = run_smoke(["cargo", "build"], project_dir)
    results.append(("cargo build", ok, out))
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


def smoke_android(project_dir: Path) -> list[tuple[str, bool, str]]:
    """File-existence + content sanity for Android/NDK templates.

    Running a real Gradle build requires the Android SDK and NDK, which we
    can't rely on in CI. Instead we verify the rendered scaffold has the
    expected layout and no leftover Jinja markers.
    """
    results = []
    required = [
        "build.gradle.kts",
        "settings.gradle.kts",
        "gradle.properties",
        "app/build.gradle.kts",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/cpp/CMakeLists.txt",
        "app/src/main/cpp/main.cpp",
        "app/src/main/cpp/openxr_app.cpp",
        "app/src/main/cpp/openxr_app.h",
    ]
    missing = [p for p in required if not (project_dir / p).is_file()]
    if missing:
        results.append(("files exist", False, "missing: " + ", ".join(missing)))
        return results
    results.append(("files exist", True, ""))

    manifest = (project_dir / "app/src/main/AndroidManifest.xml").read_text()
    if "com.oculus.intent.category.VR" not in manifest:
        results.append(("manifest has VR intent", False, "missing VR intent category"))
        return results
    if "com.oculus.supportedDevices" not in manifest:
        results.append(("manifest has VR intent", False, "missing supportedDevices"))
        return results
    results.append(("manifest has VR intent", True, ""))

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".kts", ".xml", ".cpp", ".h", ".txt", ".md", ".json", ".properties"}:
            continue
        text = path.read_text(errors="ignore")
        if "{{ cookiecutter." in text or "{% cookiecutter" in text:
            rel = path.relative_to(project_dir)
            results.append(("no unrendered jinja", False, f"{rel}"))
            return results
    results.append(("no unrendered jinja", True, ""))
    return results


def get_smoke_fn(template_name: str):
    if template_name.startswith("python/") or template_name.startswith("legacy/"):
        return smoke_python
    if template_name.startswith("typescript/"):
        return smoke_typescript
    if template_name.startswith("rust/"):
        return smoke_rust
    if template_name.startswith("swift/"):
        return smoke_swift
    if template_name.startswith("android/"):
        return smoke_android
    return lambda _: []


WORKSPACE_DEFS = ["hub-and-spoke"]

SPOKE_MANIFESTS = {
    "typescript/sveltekit": "package.json",
    "typescript/node-worker": "package.json",
    "rust/cli": "Cargo.toml",
}


def smoke_workspace(ws_name: str) -> tuple[bool, list[str]]:
    """Render a workspace and verify root + spoke structure."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "scaffold_workspace", ROOT / "tools" / "scaffold_workspace.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ws_def = mod.load_workspace_def(ws_name)
    errors = []

    with tempfile.TemporaryDirectory() as tmp:
        try:
            mod.scaffold(ws_name, "test project", Path(tmp))
        except Exception as e:
            return False, [f"scaffold failed: {e}"]

        ws_root = Path(tmp) / "test-project"
        if not ws_root.exists():
            return False, [f"workspace root not created: {ws_root}"]

        for expected in ["shared-config.json", "Justfile", "README.md", "CLAUDE.md"]:
            if not (ws_root / expected).exists():
                errors.append(f"missing root file: {expected}")

        if not (ws_root / "infra").is_dir():
            errors.append("missing infra/ directory")

        for spoke in ws_def["spokes"]:
            spoke_dir = ws_root / ("test-project" + spoke["suffix"])
            if not spoke_dir.exists():
                errors.append(f"missing spoke dir: {spoke_dir.name}")
                continue
            manifest = SPOKE_MANIFESTS.get(spoke["template"])
            if manifest and not (spoke_dir / manifest).exists():
                errors.append(f"missing manifest {manifest} in {spoke_dir.name}")

    return len(errors) == 0, errors


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

                smoke_results = (
                    check_versioning_payload(project_dir, name, template_path)
                    + smoke_just_fmt(project_dir)
                    + smoke_fn(project_dir)
                )
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

    # Workspace rendering tests
    for ws_name in WORKSPACE_DEFS:
        total += 1
        print(f"\n{'='*60}")
        print(f"Workspace: {ws_name}")
        print(f"{'='*60}")
        ok, errors = smoke_workspace(ws_name)
        if ok:
            print(f"  PASSED")
            passed += 1
        else:
            for err in errors:
                print(f"  FAIL: {err}")
            failed_list.append((f"workspace/{ws_name}", "; ".join(errors)))

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
