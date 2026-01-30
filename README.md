# Cookiecutter Templates

Project templates organized by language and framework.

## Templates

### Python

| Template | Description | Features |
|----------|-------------|----------|
| `python/fastapi` | FastAPI web API | uvicorn, async, health endpoint |
| `python/flask` | Flask web application | jsonify, debug mode |
| `python/cli` | Command-line tool | Click, subcommands, entry point |

### TypeScript

| Template | Description | Features |
|----------|-------------|----------|
| `typescript/node` | Node.js application | ESM, tsx watch, vitest |
| `typescript/sveltekit` | SvelteKit web app | Svelte 5, Vite, SSR |
| `typescript/react` | React SPA | React 18, Vite, strict mode |

### Swift

| Template | Description | Features |
|----------|-------------|----------|
| `swift/macos` | macOS application | SwiftUI, SPM, macOS 14+ |
| `swift/ios` | iOS application | SwiftUI, SPM, iOS 17+ |

### Legacy

| Template | Description | Features |
|----------|-------------|----------|
| `legacy/cookiecutter-uv` | Full Python project | GitHub Actions, pytest, mkdocs, codecov, Docker, devcontainer, multiple licenses, flat/src layout |

## Usage

```bash
# Install cookiecutter
uv tool install cookiecutter

# Generate a project
cookiecutter python/fastapi
cookiecutter typescript/sveltekit
cookiecutter swift/macos
cookiecutter legacy/cookiecutter-uv
```

## Quick Start

### Python (uv)

```bash
cd my-project
uv sync
uv run uvicorn my_project.main:app --reload  # FastAPI
uv run flask run                              # Flask
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
