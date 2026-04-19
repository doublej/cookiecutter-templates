#!/usr/bin/env python
"""Post-generation hook: clean up conditional files and directories."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)
MCP_SERVERS = "{{cookiecutter.mcp_servers}}"
MCP_SCOPE = "{{cookiecutter.mcp_scope}}"
TEMPLATE_VERSION = "{{cookiecutter._version}}"
TEMPLATE_PATH = r"{{cookiecutter._template}}"


def remove_file(filepath: str) -> None:
    path = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.exists(path):
        os.remove(path)


def remove_dir(filepath: str) -> None:
    path = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.isdir(path):
        shutil.rmtree(path)


def move_file(filepath: str, target: str) -> None:
    src = os.path.join(PROJECT_DIRECTORY, filepath)
    dst = os.path.join(PROJECT_DIRECTORY, target)
    if os.path.exists(src):
        os.rename(src, dst)


def move_dir(src: str, target: str) -> None:
    src_path = os.path.join(PROJECT_DIRECTORY, src)
    dst_path = os.path.join(PROJECT_DIRECTORY, target)
    if os.path.isdir(src_path):
        shutil.move(src_path, dst_path)


LICENSE_FILES = ["LICENSE_MIT", "LICENSE_BSD", "LICENSE_ISC", "LICENSE_APACHE", "LICENSE_GPL"]

LICENSE_MAP = {
    "MIT license": "LICENSE_MIT",
    "BSD license": "LICENSE_BSD",
    "ISC license": "LICENSE_ISC",
    "Apache Software License 2.0": "LICENSE_APACHE",
    "GNU General Public License v3": "LICENSE_GPL",
}

MCP_PRESETS = {
    "minimal": ["context7"],
    "standard": ["context7", "consult-user-mcp"],
}

MCP_SERVER_CONFIGS = {
    "context7": {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp@latest"],
    },
    "consult-user-mcp": {
        "command": "npx",
        "args": ["-y", "consult-user-mcp@latest"],
    },
}


def cleanup_github_actions():
    if "{{cookiecutter.include_github_actions}}" != "y":
        remove_dir(".github")
    else:
        if "{{cookiecutter.mkdocs}}" != "y" and "{{cookiecutter.publish_to_pypi}}" == "n":
            remove_file(".github/workflows/on-release-main.yml")


def cleanup_optional_features():
    if "{{cookiecutter.mkdocs}}" != "y":
        remove_dir("docs")
        remove_file("mkdocs.yml")

    if "{{cookiecutter.dockerfile}}" != "y":
        remove_file("Dockerfile")

    if "{{cookiecutter.codecov}}" != "y":
        remove_file("codecov.yaml")
        if "{{cookiecutter.include_github_actions}}" == "y":
            remove_file(".github/workflows/validate-codecov-config.yml")

    if "{{cookiecutter.devcontainer}}" != "y":
        remove_dir(".devcontainer")


def handle_license():
    selected = "{{cookiecutter.open_source_license}}"
    keep_file = LICENSE_MAP.get(selected)

    if keep_file:
        move_file(keep_file, "LICENSE")
        for f in LICENSE_FILES:
            if f != keep_file:
                remove_file(f)
    else:
        for f in LICENSE_FILES:
            remove_file(f)


def handle_layout():
    if "{{cookiecutter.layout}}" == "src":
        src_dir = os.path.join(PROJECT_DIRECTORY, "src")
        if os.path.isdir(src_dir):
            remove_dir("src")
        move_dir("{{cookiecutter.project_slug}}", os.path.join("src", "{{cookiecutter.project_slug}}"))


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
        "template": "legacy/cookiecutter-uv",
        "template_version": TEMPLATE_VERSION,
        "template_source": resolve_template_source(),
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": {
            "project_name": "{{cookiecutter.project_name}}",
            "project_slug": "{{cookiecutter.project_slug}}",
            "description": "{{cookiecutter.description}}",
            "author": "{{cookiecutter.author}}",
            "layout": "{{cookiecutter.layout}}",
            "mcp_servers": MCP_SERVERS,
            "mcp_scope": MCP_SCOPE,
        },
    }
    meta_path = os.path.join(PROJECT_DIRECTORY, ".template-meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def _write_mcp_json(server_names):
    servers = {}
    for name in server_names:
        if name in MCP_SERVER_CONFIGS:
            servers[name] = MCP_SERVER_CONFIGS[name]
    config = {"mcpServers": servers}
    mcp_path = os.path.join(PROJECT_DIRECTORY, ".mcp.json")
    with open(mcp_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"  MCP: wrote .mcp.json ({len(servers)} servers)")


def _add_via_claude_cli(server_names):
    if not shutil.which("claude"):
        print("  MCP: claude CLI not found. Run these commands manually:")
        for name in server_names:
            cfg = MCP_SERVER_CONFIGS.get(name)
            if cfg:
                args = " ".join(cfg["args"])
                print(f"    claude mcp add {name} -- {cfg['command']} {args}")
        return
    for name in server_names:
        cfg = MCP_SERVER_CONFIGS.get(name)
        if not cfg:
            continue
        cmd = ["claude", "mcp", "add", name, "--scope", "local", "--", cfg["command"], *cfg["args"]]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  MCP: added {name} (local scope)")
        else:
            print(f"  MCP: failed to add {name}: {result.stderr.strip()}")


def _run_mcpick_interactive():
    if not shutil.which("mcpick-plus"):
        print("  MCP: mcpick-plus not found. Install with: npm i -g mcpick-plus")
        print("  Then run: mcpick-plus init")
        return
    subprocess.run(["mcpick-plus", "init"])


def setup_mcp():
    if MCP_SERVERS == "none":
        return

    server_names = MCP_PRESETS.get(MCP_SERVERS)

    if MCP_SERVERS == "interactive":
        _run_mcpick_interactive()
        return

    if not server_names:
        return

    if MCP_SCOPE == "project":
        _write_mcp_json(server_names)
    else:
        _add_via_claude_cli(server_names)


def print_getting_started():
    print(f"\n  Project created: {{cookiecutter.project_name}}\n")
    print("  Getting started:")
    print(f"    cd {{cookiecutter.project_name}}")
    print("    uv sync")
    print("    uv run pytest\n")


if __name__ == "__main__":
    cleanup_github_actions()
    cleanup_optional_features()
    handle_license()
    handle_layout()
    write_meta()
    setup_mcp()
    print_getting_started()
