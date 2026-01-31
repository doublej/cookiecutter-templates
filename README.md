# Cookiecutter Templates

Project templates organized by language and framework.

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
| `typescript/node-lib` | Library with declarations | -- |
| `typescript/node-worker` | Background worker | `worker_type`, `include_docker` |
| `typescript/sveltekit` | SvelteKit web app | `include_tracking` |
| `typescript/react` | React SPA (Vite) | `include_tracking` |

### Swift

| Template | Description | Options |
|----------|-------------|---------|
| `swift/macos` | macOS SwiftUI app | `deployment_target` |
| `swift/ios` | iOS SwiftUI app | `deployment_target` |

### Legacy

| Template | Description | Options |
|----------|-------------|---------|
| `legacy/cookiecutter-uv` | Full Python project | `layout`, `include_github_actions`, `publish_to_pypi`, `mkdocs`, `codecov`, `dockerfile`, `devcontainer`, `open_source_license` |

## Usage

```bash
# Install cookiecutter
uv tool install cookiecutter

# Generate a project
cookiecutter python/fastapi
cookiecutter typescript/node-api
cookiecutter swift/macos
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

## Tools

| Script | Description |
|--------|-------------|
| `tools/render_test.py` | Render and smoke-test all templates |
| `tools/inject_tracking.py` | Inject Umami tracking into rendered projects |

## Contributing

1. Make changes to template files
2. Run `python tools/render_test.py` to verify all templates render correctly
3. Test the rendered output manually for your specific changes
