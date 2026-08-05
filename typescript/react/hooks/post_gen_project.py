#!/usr/bin/env python3
"""Post-generation hook: set up Umami tracking, set up MCP, write meta."""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(os.path.realpath(os.path.curdir))
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
INCLUDE_TRACKING = "{{ cookiecutter.include_tracking }}"
TRACKING_TARGET = "index.html"
TRACKING_PLACEHOLDER_LINE = "    <!-- TRACKING_PLACEHOLDER -->\n"
MCP_SERVERS = "{{ cookiecutter.mcp_servers }}"
MCP_SCOPE = "{{ cookiecutter.mcp_scope }}"
TEMPLATE_VERSION = "{{ cookiecutter._version }}"
TEMPLATE_PATH = r"{{ cookiecutter._template }}"
ATLAS_TYPE = "node"
ATLAS_FRAMEWORK = "react"

CONTEXT = {
    "project_name": "{{ cookiecutter.project_name }}",
    "project_slug": PROJECT_SLUG,
    "description": "{{ cookiecutter.description }}",
    "author": "{{ cookiecutter.author }}",
    "include_tracking": INCLUDE_TRACKING,
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


def _strip_placeholder():
    target = PROJECT_DIR / TRACKING_TARGET
    if not target.exists():
        return
    content = target.read_text()
    if TRACKING_PLACEHOLDER_LINE in content:
        target.write_text(content.replace(TRACKING_PLACEHOLDER_LINE, ""))


def _repo_tools_dir():
    try:
        tmpl = Path(TEMPLATE_PATH).resolve()
    except Exception:
        return None
    for p in [tmpl, *tmpl.parents]:
        if (p / "tools" / "sync_manifest.json").is_file():
            return p / "tools"
    return None


def setup_tracking():
    """Strip the placeholder, or auto-register in Umami and inject the script.
    umami_register.py resolves credentials itself (env, then the onenv `umami`
    namespace) — the flow is prompt-free and best-effort: any failure leaves
    the placeholder and never blocks generation."""
    if INCLUDE_TRACKING != "y":
        _strip_placeholder()
        return

    if os.environ.get("TEMPLATE_RENDER_TEST"):
        print(f"  Umami: placeholder left in {TRACKING_TARGET} — run tools/inject_tracking.py later")
        return

    tools = _repo_tools_dir()
    register = (tools / "umami_register.py") if tools else None
    inject = (tools / "inject_tracking.py") if tools else None
    if not (register and register.exists() and inject and inject.exists()):
        print("  Umami: skipped (repo tools/ not found)")
        print(f"  Umami: placeholder left in {TRACKING_TARGET} — run tools/inject_tracking.py later")
        return

    r = subprocess.run(
        [sys.executable, str(register), PROJECT_SLUG, PROJECT_SLUG, "--json"],
        capture_output=True, text=True,
    )
    website_id = umami_url = ""
    if r.returncode == 0:
        try:
            reg = json.loads(r.stdout)
            website_id, umami_url = reg["websiteId"], reg["umamiUrl"]
        except (ValueError, KeyError):
            pass
    if not (website_id and umami_url):
        print(f"  Umami: register failed: {r.stderr.strip() or r.stdout.strip()}")
        print(f"  Umami: placeholder left in {TRACKING_TARGET} — run tools/inject_tracking.py later")
        return
    print(f"  Umami: registered '{PROJECT_SLUG}' → {website_id}")

    r = subprocess.run(
        [sys.executable, str(inject), str(PROJECT_DIR), umami_url, website_id],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    if out:
        print("  " + out.replace("\n", "\n  "))
    if r.returncode != 0:
        print(f"  Umami: inject failed: {r.stderr.strip()}")


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
        "template": "typescript/react",
        "template_version": TEMPLATE_VERSION,
        "template_source": resolve_template_source(),
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "context": CONTEXT,
    }
    with open(".template-meta.json", "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


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


def write_atlas():
    atlas_path = Path(".atlas")
    data = {
        "description": "{{ cookiecutter.description }}",
        "type": ATLAS_TYPE,
        "framework": ATLAS_FRAMEWORK,
        "port": int("{{ cookiecutter.port }}"),
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


def bootstrap_agent_log():
    """Seed the shared agent journal (canonical copy: hooks/_agent_log.py)."""
    hint = "  agent-log: skipped — run 'atlas agent-log init' later"
    if not shutil.which("atlas"):
        print(hint)
        return
    try:
        r = subprocess.run(
            ["atlas", "agent-log", "init"],
            timeout=15, check=True, capture_output=True, text=True,
        )
        out = r.stdout.strip()
        if out:
            print("  " + out.replace("\n", "\n  "))
    except Exception:
        print(hint)


def main():
    setup_tracking()
    write_meta()
    write_atlas()
    setup_mcp()
    bootstrap_agent_log()
    print(f"\n  Project created: {PROJECT_SLUG}\n")
    print("  Getting started:")
    if not os.environ.get("ATLAS_CD_FILE"):  # the atlas zsh wrapper cds there itself
        print(f"    cd {PROJECT_SLUG}")
    print("    bun install")
    print("    bun run dev\n")


if __name__ == "__main__":
    main()
