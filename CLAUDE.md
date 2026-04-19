# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A unified cookiecutter template collection for scaffolding projects across Python, TypeScript, Rust, and Swift. Includes workspace composition for multi-project setups and validation tooling to keep templates consistent.

## Commands

```bash
# Validate sync across template families (identical files, Justfile recipes, workspace refs)
uv run tools/sync_check.py

# CI-only: also fail when a changed template did not bump its _version
uv run tools/sync_check.py --enforce-bumps --bump-base origin/main

# Render all templates with multiple context variants and run smoke tests
uv run tools/render_test.py

# Offline unit test for the SessionStart update-check hook
uv run tools/test_update_check.py

# Bump a template version (strict MAJOR.MINOR.PATCH only)
uv run tools/bump_version.py python/fastapi {major|minor|patch}

# Scaffold a hub-and-spoke workspace
uv run tools/scaffold_workspace.py hub-and-spoke --output ~/projects/ --name "my project"

# Generate a single project
cookiecutter python/fastapi
cookiecutter typescript/node-api
cookiecutter rust/cli
cookiecutter swift/macos
```

Always run `sync_check.py` then `render_test.py` after changes. CI runs both on push/PR to main.

## Template versioning

Every `cookiecutter.json` carries a private `_version` field (not prompted). Every render writes it into the project's `.template-meta.json` as `template_version`. Every generated project ships a `.claude/` SessionStart hook that compares local version against the upstream template on every Claude Code session and prints `[template-update] <tmpl> <local> -> <upstream> available ...` when upstream has advanced — prompting the agent to ask the user whether to run `update_scaffold.py`.

**Semver semantics (strict `MAJOR.MINOR.PATCH`, no pre-release suffixes):**

- `patch` — file content tweak, dep bump, lint fix
- `minor` — new file, new Justfile recipe, added feature
- `major` — breaking scaffold change (renamed path, removed recipe, cookiecutter key rename)

**Bump workflow:** after editing a template, run `uv run tools/bump_version.py <template> {major|minor|patch}`. CI runs `sync_check.py --enforce-bumps` on every PR and fails if a template has file changes but no `_version` bump. Legacy (`legacy/cookiecutter-uv`) is exempt from bump enforcement and from the cross-family `.claude/` payload.

**Opt-out** (per generated project): set env `NO_TEMPLATE_UPDATE_CHECK=1` or `touch .claude/no-template-update-check`.

**v1 limitations:** the check resolves upstream via the absolute `template_source.path` captured at render time. If the cookiecutter-templates repo is moved, the check silently no-ops. Workspaces composed from multiple templates carry per-spoke `.claude/` payloads only; opening the workspace root fires no hook.

## Architecture

### Template families

Templates are grouped into families (python, typescript, rust, swift). Within a family, certain files and Justfile recipes **must stay identical** — enforced by `tools/sync_manifest.json` + `tools/sync_check.py`.

| Family | Templates | Shared identical files | Shared Justfile recipes |
|--------|-----------|----------------------|------------------------|
| python | cli, fastapi, flask | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json` | default, install, lint, lint-fix, format, format-check, typecheck, test, loc-check, dir-check, check, clean |
| typescript | node-api, node-cli, bun-package, node-lib, node-worker, react, sveltekit | `hooks/pre_gen_project.py` | default, install, lint, lint-fix, test, loc-check, dir-check, check, build, clean |
| swift | ios, macos | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json` | default, install, xcode, test, loc-check, dir-check, check, build, build-release, clean |
| rust | cli | `hooks/pre_gen_project.py`, `.gitignore` | default, lint, fmt, fmt-check, check, test, loc-check, dir-check, build-release, reinstall |

**Exceptions** are declared in `sync_manifest.json` under `justfile_exceptions` (e.g. SvelteKit skips `typecheck`/`clean`).

### Template anatomy

Each template follows this structure:
```
<language>/<template>/
├── cookiecutter.json              # Variables and options
├── hooks/
│   ├── pre_gen_project.py         # Validates project_name + project_slug
│   └── post_gen_project.py        # Writes .template-meta.json, MCP setup, prints instructions
└── {{cookiecutter.project_slug}}/
    ├── CLAUDE.md, agent.md, Justfile, README.md, .gitignore, .quality.json
    └── src/ (or language-specific layout)
```

### Tools

| Script | Purpose |
|--------|---------|
| `tools/sync_check.py` | SHA256 comparison of identical files; recipe-level Justfile comparison; workspace spoke ref validation |
| `tools/render_test.py` | Renders ~50 template variants (defined in `TEMPLATES` dict); runs language-specific smoke tests (compileall, bun install+lint+build+test, cargo build, swift build) |
| `tools/scaffold_workspace.py` | Composes templates into multi-project workspaces from JSON definitions in `workspace/` |
| `tools/inject_tracking.py` | Injects Umami analytics into rendered HTML with `<!-- TRACKING_PLACEHOLDER -->` |

### Workspace composition

`workspace/hub-and-spoke.json` defines a multi-project workspace (backend, browser, picker, monitor). Root files live in `workspace/_root_files/` as `.tmpl` files using `string.Template` substitution (`${slug}`, `${api_port}`).

## Conventions

- **Project slug**: kebab-case `[a-z][a-z0-9-]*[a-z0-9]`, min 2 chars, validated in pre-gen hooks
- **Hooks are safe**: no `git init`, no dependency installs, no commits
- **MCP options**: every template supports `mcp_servers` (none/minimal/standard/interactive) and `mcp_scope` (project/local) in cookiecutter.json
- **When editing a shared file** (identified in sync_manifest.json), apply the same change to all templates in the family
- **When editing a shared Justfile recipe**, apply the same change to all Justfiles in the family (respecting exceptions)
- **render_test.py variants**: when adding a new template option, add corresponding variant entries to the `TEMPLATES` dict in render_test.py
- **Tooling**: Python uses uv/ruff/mypy/pytest; TypeScript uses bun/Biome/Vitest; Rust uses cargo/clippy; Swift uses SPM
