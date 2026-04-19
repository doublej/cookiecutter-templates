# Cookiecutter Templates

Project templates organized by language and framework, plus workspace scaffolding for multi-project setups.

## Templates

### Python

| Template | Description | Options |
|----------|-------------|---------|
| `python/fastapi` | FastAPI web API | `python_version` |
| `python/flask` | Flask web application | `python_version` |
| `python/cli` | Command-line tool (Click) | `python_version` |

### TypeScript

| Template | Description | Options |
|----------|-------------|---------|
| `typescript/node-api` | Elysia API server | `include_docker` |
| `typescript/node-cli` | Commander CLI | -- |
| `typescript/bun-package` | Bun package starter | -- |
| `typescript/node-lib` | Library with declarations | -- |
| `typescript/node-worker` | Background worker | `worker_type`, `include_docker` |
| `typescript/sveltekit` | SvelteKit web app | `include_tracking` |
| `typescript/react` | React SPA (Vite) | `include_tracking` |

### Rust

| Template | Description | Options |
|----------|-------------|---------|
| `rust/cli` | CLI tool (clap + anyhow) | -- |

### Swift

| Template | Description | Options |
|----------|-------------|---------|
| `swift/macos` | macOS SwiftUI app | `deployment_target` |
| `swift/ios` | iOS SwiftUI app | `deployment_target` |

### Android

| Template | Description | Options |
|----------|-------------|---------|
| `android/quest-vr` | Native Quest VR app (C++17, OpenXR, Gradle+CMake, GameActivity) | `graphics_api`, `min_sdk_version`, `target_sdk_version` |

### Legacy

| Template | Description | Options |
|----------|-------------|---------|
| `legacy/cookiecutter-uv` | Full Python project | `layout`, `include_github_actions`, `publish_to_pypi`, `mkdocs`, `codecov`, `dockerfile`, `devcontainer`, `open_source_license` |

## Workspaces

Workspace scaffolding composes multiple templates into a unified multi-project workspace.

| Workspace | Description |
|-----------|-------------|
| `hub-and-spoke` | Backend API + browser UI + Rust picker + cron monitor |

### Scaffold a workspace

```bash
uv run tools/scaffold_workspace.py hub-and-spoke --output ~/projects/ --name "my project"
```

This creates a workspace root with shared config, root Justfile, daemon configs, and one directory per spoke.

## Usage

```bash
# Install cookiecutter
uv tool install cookiecutter

# Generate a project
cookiecutter python/fastapi
cookiecutter typescript/node-api
cookiecutter typescript/bun-package
cookiecutter rust/cli
cookiecutter swift/macos
cookiecutter android/quest-vr
cookiecutter legacy/cookiecutter-uv
```

## Quick Start

### Python (uv)

```bash
cd my-project
uv sync
uv run uvicorn my_project.main:app --reload  # FastAPI
uv run flask --app my_project.app run        # Flask
uv run my-project hello                       # CLI
```

### TypeScript (bun)

```bash
cd my-project
bun install
bun run dev
```

### Rust (cargo)

```bash
cd my-project
cargo build
cargo run -- --help
```

### Swift (SPM)

```bash
cd MyProject
swift build
swift run
```

## Common Variables

All templates share these variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Human-readable project name | varies |
| `project_slug` | Directory/package name (auto-derived) | from `project_name` |
| `description` | Short project description | varies |
| `author` | Author name | "Your Name" |

## Template Standards

- Hooks are safe: no `git init`, no dependency installs, no commits
- Pre-generation validation on `project_name` and `project_slug`
- Unified `.gitignore` baseline across all templates
- Every template includes a `README.md` with getting started instructions
- Every non-legacy template ships a `.claude/` SessionStart hook that notifies the agent when the upstream template has advanced

## Versioning

Every `cookiecutter.json` has a private `_version` field (strict `MAJOR.MINOR.PATCH`, no pre-release suffixes). The version travels into each rendered project as `template_version` in `.template-meta.json`. A SessionStart hook compares local vs. upstream and nudges the agent when upstream is newer.

```bash
# Bump a template version
uv run tools/bump_version.py python/fastapi patch     # 1.0.0 -> 1.0.1
uv run tools/bump_version.py python/fastapi minor     # 1.0.1 -> 1.1.0
uv run tools/bump_version.py python/fastapi major     # 1.1.0 -> 2.0.0
```

Bump semantics: `patch` for content tweaks/dep bumps, `minor` for additions (files, recipes, options), `major` for breaking scaffold changes. CI runs `sync_check.py --enforce-bumps` on every PR and fails if a template has file changes without a `_version` bump.

Opt-out per generated project: `export NO_TEMPLATE_UPDATE_CHECK=1` or `touch .claude/no-template-update-check`.

## Tools

| Script | Description |
|--------|-------------|
| `tools/render_test.py` | Render and smoke-test all templates + workspaces |
| `tools/sync_check.py` | Validate file sync across template families + workspace refs (`--enforce-bumps` for CI) |
| `tools/bump_version.py` | Bump `_version` in a template's cookiecutter.json |
| `tools/update_scaffold.py` | Diff a rendered project against its source template and optionally `--apply` the delta |
| `tools/test_update_check.py` | Offline test for the SessionStart update-check hook |
| `tools/scaffold_workspace.py` | Scaffold multi-project workspaces from definitions |
| `tools/inject_tracking.py` | Inject Umami tracking into rendered projects |

## Contributing

1. Make changes to template files
2. `uv run tools/bump_version.py <template> {major|minor|patch}` — bump the template you changed
3. `uv run tools/sync_check.py` — verify cross-family and in-family sync
4. `uv run tools/render_test.py` — verify every template still renders
5. `uv run tools/test_update_check.py` — verify the update-check hook still behaves
6. Test the rendered output manually for your specific changes
