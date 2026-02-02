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

See [agent.md](agent.md) for AI coding agent workflow and guidelines.
