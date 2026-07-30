#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["cookiecutter"]
# ///
"""Render and smoke-test all cookiecutter templates with multiple context variants."""
import json
import os
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
    "typescript/raycast-extension": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
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
    "go/cli": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "go/api": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "swift/ios": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "swift/macos": [
        {},
        {"mcp_servers": "minimal", "mcp_scope": "project"},
    ],
    "android/quest-vr": [
        {},
        {"graphics_api": "vulkan"},
        {"mcp_servers": "standard", "mcp_scope": "project"},
    ],
    "shopify/theme": [
        {},
        {"mcp_servers": "standard", "mcp_scope": "project"},
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

    # Signal post-gen hooks to skip any interactive prompts (e.g. Umami
    # register/inject), so this non-interactive harness never blocks on input().
    os.environ["TEMPLATE_RENDER_TEST"] = "1"

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
    # CI=1 keeps watch-mode tools (vitest) single-pass in local runs too;
    # explicit utf-8 so Windows doesn't decode child output as cp1252
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=120,
        env={**os.environ, "CI": "1"},
        encoding="utf-8", errors="replace",
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def check_versioning_payload(
    project_dir: Path, template_name: str, template_path: Path
) -> list[tuple[str, bool, str]]:
    """Assert .template-meta.json + .claude payload are shaped correctly."""
    results: list[tuple[str, bool, str]] = []

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

    settings = project_dir / ".claude" / "settings.json"
    if not settings.is_file():
        results.append((".claude/settings.json exists", False, "missing"))
        return results
    try:
        json.loads(settings.read_text())
    except Exception as e:
        results.append((".claude/settings.json parses", False, f"{e}"))
        return results

    scripts_dir = project_dir / ".claude" / "scripts"
    for name in ("check_template_update.py",):
        script = scripts_dir / name
        if not script.is_file():
            results.append((f"{name} exists", False, "missing"))
            return results
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as e:
            results.append((f"{name} compiles", False, f"{e}"))
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
        results.append(("bun install", True, "SKIP: bun not found"))
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


def smoke_raycast(project_dir: Path) -> list[tuple[str, bool, str]]:
    """Manifest + toolchain sanity for Raycast extension templates.

    `ray lint`/`ray build` need the Raycast CLI (macOS-only, ships with the
    app), which the CI matrix can't provide. We verify the rendered scaffold's
    shape and manifest everywhere, and on macOS with bun available we
    additionally install deps and typecheck with tsc.
    """
    results = []
    required = [
        "package.json",
        "tsconfig.json",
        ".eslintrc.json",
        "src/hello.tsx",
        "src/lib/prefs.ts",
        "assets/command-icon.png",
    ]
    missing = [p for p in required if not (project_dir / p).is_file()]
    if missing:
        results.append(("files exist", False, "missing: " + ", ".join(missing)))
        return results
    results.append(("files exist", True, ""))

    try:
        pkg = json.loads((project_dir / "package.json").read_text())
    except Exception as e:
        results.append(("package.json parses", False, f"{e}"))
        return results
    required_keys = [
        "name", "title", "description", "icon", "author", "license", "commands",
    ]
    missing_keys = [k for k in required_keys if k not in pkg]
    if missing_keys:
        results.append(("manifest keys", False, "missing: " + ", ".join(missing_keys)))
        return results
    results.append(("manifest keys", True, ""))

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".ts", ".tsx", ".json", ".md"}:
            continue
        text = path.read_text(errors="ignore")
        if "{{ cookiecutter." in text or "{% cookiecutter" in text:
            rel = path.relative_to(project_dir)
            results.append(("no unrendered jinja", False, f"{rel}"))
            return results
    results.append(("no unrendered jinja", True, ""))

    if platform.system() != "Darwin":
        return results
    if not has_command("bun"):
        results.append(("bun install", True, "SKIP: bun not found"))
        return results
    ok, out = run_smoke(["bun", "install"], project_dir)
    results.append(("bun install", ok, out))
    if not ok:
        return results
    ok, out = run_smoke(["bunx", "tsc", "--noEmit"], project_dir)
    results.append(("tsc --noEmit", ok, out))
    return results


def smoke_rust(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("cargo"):
        results.append(("cargo build", True, "SKIP: cargo not found"))
        return results
    ok, out = run_smoke(["cargo", "build"], project_dir)
    results.append(("cargo build", ok, out))
    return results


def smoke_go(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("go"):
        results.append(("go build", True, "SKIP: go not found"))
        return results
    for cmd, label in ([sys_go("build"), "go build"], [sys_go("vet"), "go vet"], [sys_go("test"), "go test"]):
        ok, out = run_smoke(cmd, project_dir)
        results.append((label, ok, out))
        if not ok:
            break
    return results


def sys_go(subcmd: str) -> list[str]:
    return ["go", subcmd, "./..."]


def smoke_swift(project_dir: Path) -> list[tuple[str, bool, str]]:
    results = []
    if not has_command("swift"):
        results.append(("swift build", True, "SKIP: swift not found"))
        return results
    if platform.system() != "Darwin":
        results.append(("swift build", True, "SKIP: Swift templates require macOS"))
        return results
    cmd = ["swift", "build"]
    manifest = (project_dir / "Package.swift").read_text(encoding="utf-8")
    if ".iOS(" in manifest:
        # iOS-only packages can't build for the macOS host; target the simulator SDK
        sdk = subprocess.run(
            ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"],
            capture_output=True, text=True,
        ).stdout.strip()
        cmd += ["--sdk", sdk, "--triple", "arm64-apple-ios-simulator"]
    ok, out = run_smoke(cmd, project_dir)
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


def smoke_shopify(project_dir: Path) -> list[tuple[str, bool, str]]:
    """File-existence + JSON validity for Shopify Liquid themes.

    A real `shopify theme check` needs the Shopify CLI, which we can't rely on
    in CI. We verify the rendered theme has the expected layout, that every
    JSON file parses, and that no Jinja markers leaked through. If the Shopify
    CLI is present we additionally run Theme Check.
    """
    results = []
    required = [
        "layout/theme.liquid",
        "config/settings_schema.json",
        "config/settings_data.json",
        "locales/en.default.json",
        "templates/index.json",
        "templates/product.json",
        "templates/collection.json",
        "templates/page.json",
        "templates/cart.json",
        "templates/404.json",
        "sections/header.liquid",
        "sections/footer.liquid",
        ".theme-check.yml",
    ]
    missing = [p for p in required if not (project_dir / p).is_file()]
    if missing:
        results.append(("files exist", False, "missing: " + ", ".join(missing)))
        return results
    results.append(("files exist", True, ""))

    bad_json = []
    for path in sorted(project_dir.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            bad_json.append(f"{path.relative_to(project_dir)}: {e}")
    if bad_json:
        results.append(("json parses", False, "; ".join(bad_json)))
        return results
    results.append(("json parses", True, ""))

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".liquid", ".json", ".md", ".css", ".js", ".yml", ".yaml"}:
            continue
        text = path.read_text(errors="ignore")
        if "{{ cookiecutter." in text or "{% cookiecutter" in text:
            rel = path.relative_to(project_dir)
            results.append(("no unrendered jinja", False, f"{rel}"))
            return results
    results.append(("no unrendered jinja", True, ""))

    if has_command("shopify"):
        ok, out = run_smoke(["shopify", "theme", "check"], project_dir)
        results.append(("shopify theme check", ok, out))
    return results


def get_smoke_fn(template_name: str):
    # Exact match before the typescript/ prefix: raycast needs its own smoke
    # (smoke_typescript would run `ray` scripts, unavailable off-macOS).
    if template_name == "typescript/raycast-extension":
        return smoke_raycast
    if template_name.startswith("python/"):
        return smoke_python
    if template_name.startswith("typescript/"):
        return smoke_typescript
    if template_name.startswith("rust/"):
        return smoke_rust
    if template_name.startswith("go/"):
        return smoke_go
    if template_name.startswith("swift/"):
        return smoke_swift
    if template_name.startswith("android/"):
        return smoke_android
    if template_name.startswith("shopify/"):
        return smoke_shopify
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
                        for line in output.strip().splitlines()[-30:]:
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
