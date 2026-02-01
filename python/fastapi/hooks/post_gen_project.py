#!/usr/bin/env python3
"""Post-generation hook: write meta file, set up MCP, print instructions."""
import json
import shutil
import subprocess
from datetime import datetime, timezone

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
MCP_SERVERS = "{{ cookiecutter.mcp_servers }}"
MCP_SCOPE = "{{ cookiecutter.mcp_scope }}"

CONTEXT = {
    "project_name": "{{ cookiecutter.project_name }}",
    "project_slug": PROJECT_SLUG,
    "description": "{{ cookiecutter.description }}",
    "author": "{{ cookiecutter.author }}",
    "python_version": "{{ cookiecutter.python_version }}",
    "mcp_servers": MCP_SERVERS,
    "mcp_scope": MCP_SCOPE,
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


def write_meta():
    meta = {
        "template": "python/fastapi",
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)


def _write_mcp_json(server_names):
    servers = {}
    for name in server_names:
        if name in MCP_SERVER_CONFIGS:
            servers[name] = MCP_SERVER_CONFIGS[name]
    config = {"mcpServers": servers}
    with open(".mcp.json", "w") as f:
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


if __name__ == "__main__":
    write_meta()
    setup_mcp()
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    print(f"    cd {PROJECT_SLUG}")
    print("    uv sync")
    print("    uv run uvicorn {}.main:app --reload\n".format(PROJECT_SLUG.replace("-", "_")))
