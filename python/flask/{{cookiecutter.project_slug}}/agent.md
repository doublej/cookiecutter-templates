# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Python {{ cookiecutter.python_version }}, uv, ruff, mypy, pytest
- Web framework: Flask

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + format-check + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just dev` — start dev server with debug mode
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues
- `just format` — format code

## Project Structure

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
├── __init__.py
└── app.py          # Flask app and routes
pyproject.toml      # project config, dependencies
Justfile            # task runner
```

## Conventions

- src/ layout with hatchling build backend
- Module name: `{{ cookiecutter.project_slug.replace('-', '_') }}`
- App instance: `{{ cookiecutter.project_slug.replace('-', '_') }}.app`
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change:

1. `just lint-fix`
2. `just format`
3. `just typecheck`
4. `just test`

Or use `just check` to run lint + format-check + typecheck + test in one go.

### Auto-fixable

- `uv run ruff check --fix src/ tests/` — auto-fix lint issues
- `uv run ruff format src/ tests/` — format code

### Common Tasks

- Add a route: define a function decorated with `@app.route()` in `app.py`
- Add a Blueprint: create a new module with `Blueprint`, register with `app.register_blueprint()`
- Add a dependency: `uv add <package>`

### Testing

- Test files: `tests/test_*.py`
- Use `app.test_client()` for request tests (no async patterns)
- Run a single test: `uv run pytest tests/test_foo.py::test_name -v`

### Boundaries

- Do not run `just dev` — never start the dev server
- Do not deploy, publish, or push
- Do not modify `[tool.*]` sections in `pyproject.toml` without asking
