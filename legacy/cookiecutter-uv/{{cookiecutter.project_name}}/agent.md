# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Python 3.9+, uv, pre-commit, ruff, mypy, pytest
- Build: hatchling
- Layout: {{ cookiecutter.layout }}

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just install` — create venv and install pre-commit hooks
- `just test` — run tests
- `just lint` — run pre-commit hooks
- `just typecheck` — run mypy
- `just build` — build wheel
- `just clean` — remove build artifacts

## Project Structure

```
{% if cookiecutter.layout == "src" -%}
src/{{ cookiecutter.project_slug }}/
{%- else -%}
{{ cookiecutter.project_slug }}/
{%- endif %}
└── ...             # package source
tests/              # test files
pyproject.toml      # project config, dependencies, tool settings
Justfile            # task runner
```

## Conventions

- {{ cookiecutter.layout }} layout with hatchling build backend
- Module name: `{{ cookiecutter.project_slug }}`
- Pre-commit hooks for code quality
- ruff for linting and formatting (line-length: 120)
- mypy with strict settings
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change:

1. `just lint` (runs pre-commit, includes auto-fixes)
2. `just typecheck`
3. `just test`

Or use `just check` to run lint + typecheck + test in one go.

### Auto-fixable

- `just lint` — runs pre-commit hooks which auto-fix some issues (ruff, trailing whitespace, etc.)

### Common Tasks

- Add a module: create a new `.py` file in the package directory
- Add a dependency: `uv add <package>` (or add to `[dependency-groups]` for dev deps)
- Add a CLI entry point: define it in `pyproject.toml` under `[project.scripts]`
- After cloning: run `uv run pre-commit install` to set up hooks

### Testing

- Test files: `tests/test_*.py`
- Framework: pytest (with optional `--cov` for coverage)
- Layout-aware: tests import from `src/` or flat layout depending on `{{ cookiecutter.layout }}`
- Run a single test: `uv run pytest tests/test_foo.py::test_name -v`

### Boundaries

- Do not deploy, publish, or push
- Do not modify `[tool.*]` sections in `pyproject.toml` without asking
- Do not modify `.pre-commit-config.yaml` without asking
