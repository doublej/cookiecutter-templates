# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Python {{ cookiecutter.python_version }}, uv, ruff, mypy, pytest
- CLI framework: Click

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + format-check + typecheck + test)
- `just install` — sync dependencies (`uv sync`)
- `just run-cli` — run the CLI (alias: `just run`)
- `just lint` — run ruff check
- `just lint-fix` — auto-fix lint issues
- `just format` — format with ruff
- `just format-check` — verify formatting
- `just typecheck` — run mypy
- `just test` — run pytest
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
├── __init__.py
└── cli.py          # Click CLI entry point
pyproject.toml      # project config, dependencies, script entry point
Justfile            # task runner
```

## Conventions

- src/ layout with hatchling build backend
- Module name: `{{ cookiecutter.project_slug.replace('-', '_') }}`
- Entry point: `{{ cookiecutter.project_slug.replace('-', '_') }}.cli:main`
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

See [agent.md](agent.md) for AI coding agent workflow and guidelines.
