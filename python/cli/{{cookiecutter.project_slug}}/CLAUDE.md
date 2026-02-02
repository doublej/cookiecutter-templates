# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Python {{ cookiecutter.python_version }}, uv, ruff, mypy, pytest
- CLI framework: Click

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + format-check + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just run` — run the CLI
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues
- `just format` — format code

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
