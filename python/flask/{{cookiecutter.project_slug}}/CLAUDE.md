# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Flask web application. Python sources live under `src/`, managed by `uv`, with `ruff` / `mypy` / `pytest` enforcing style, typing, and behaviour against the `.quality.json` thresholds.

## Mental model

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
├── __init__.py
└── app.py          # `app = Flask(__name__)` + view functions
pyproject.toml      # project config, dependencies
```

The runtime path is `flask run → {{ cookiecutter.project_slug.replace('-', '_') }}.app → view functions`. Views are functions decorated with `@app.route(...)`. When `app.py` outgrows itself, extract `Blueprint` modules and register them via `app.register_blueprint(...)`.

## Invariants

- `src/` layout with hatchling — do not move code to a top-level package.
- Module name is `{{ cookiecutter.project_slug.replace('-', '_') }}`; the WSGI app reference is `{{ cookiecutter.project_slug.replace('-', '_') }}.app`.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; Flask error handlers translate domain errors to HTTP responses.
- `uv` owns the lockfile. Add deps with `uv add <pkg>`.

## Common change patterns

- **Add a view** → function with `@app.route("/path")` in `app.py`.
- **Add a blueprint** → `Blueprint("name", __name__)` in a new module; register with `app.register_blueprint(...)`.
- **Add error handling** → `@app.errorhandler(SomeException)` decorator.
- **Add a dependency** → `uv add <pkg>`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `format-check` + `typecheck` + `test`

Recipe reference:

- `just install` — `uv sync`
- `just dev` — start Flask debug server (agent must not run this)
- `just lint` / `just lint-fix` — ruff check / `--fix`
- `just format` / `just format-check` — ruff format / `--check`
- `just typecheck` — mypy
- `just test` — pytest
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `app.py`, add nested `CLAUDE.md` files in high-value subfolders (blueprints, domain logic, integrations) following the `claude-md-tree` skill's context-packet pattern.
