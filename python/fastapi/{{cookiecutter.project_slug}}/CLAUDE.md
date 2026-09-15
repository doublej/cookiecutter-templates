# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A FastAPI HTTP service served by Uvicorn. Python sources live under `src/`, managed by `uv`, with `ruff` / `mypy` / `pytest` enforcing style, typing, and behaviour against the `.quality.json` thresholds.

## Mental model

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
├── __init__.py
├── main.py         # `app = FastAPI()` + route handlers + `get_locale` dependency
├── i18n.py         # `t()` + `negotiate()`: Accept-Language → locale → en
└── locales/        # en.json (base, fallback) + nl.json — every user-facing string
pyproject.toml      # project config, dependencies
```

The runtime path is `uvicorn → {{ cookiecutter.project_slug.replace('-', '_') }}.main:app → route handlers`. Handlers are `async def` functions decorated with `@app.get` / `@app.post` etc. When `main.py` outgrows itself, extract `APIRouter` modules and include them with `app.include_router(...)`.

## API docs

The scaffold ships three OpenAPI UIs:

- `/docs` — **Scalar** (default, via `scalar-fastapi`)
- `/swagger` — Swagger UI (manually mounted; `docs_url=None` on `FastAPI(...)` frees `/docs` for Scalar)
- `/redoc` — ReDoc (FastAPI default)

Enrich docs by adding `summary` / `description` / `responses` to route decorators and `Field(..., description=..., examples=...)` to Pydantic models — all four UIs read from the same `/openapi.json`.

## Invariants

- `src/` layout with hatchling — do not move code to a top-level package.
- Module name is `{{ cookiecutter.project_slug.replace('-', '_') }}`; ASGI app reference is `{{ cookiecutter.project_slug.replace('-', '_') }}.main:app`.
- Route handlers are `async def`. Use Pydantic `BaseModel` for request / response shapes.
- Tests use `httpx.AsyncClient` with `ASGITransport` — do not spin up a real server in tests.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; FastAPI's exception handlers translate domain errors to HTTP responses.
- `uv` owns the lockfile. Add deps with `uv add <pkg>`.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.

## Common change patterns

- **Add a route** → `async def` with `@app.get` / `@app.post` / etc. in `main.py`.
- **Add request / response models** → Pydantic `BaseModel` subclasses in `main.py` or a sibling `schemas.py`.
- **Extract a router** → `APIRouter` in a new module; register with `app.include_router(...)`.
- **Add middleware / lifespan** → `@app.middleware("http")` or the `lifespan=` parameter on `FastAPI()`.
- **Add a dependency** → `uv add <pkg>`.
- **Add or change text** → edit `src/{{ cookiecutter.project_slug.replace('-', '_') }}/locales/*.json`, call `t("root.message", locale, ...)` with `locale: Annotated[str, Depends(get_locale)]` on the route (it also sets `Content-Language` and `Vary`), run `just i18n-check`.
- **Add a language** → add `src/{{ cookiecutter.project_slug.replace('-', '_') }}/locales/<locale>.json` (no registration: `LOCALES` discovers it and `negotiate()` offers it), run `just i18n-check`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint` + `format-check` + `typecheck` + `test`

Recipe reference:

- `just install` — `uv sync`
- `just dev` — start Uvicorn with auto-reload (agent must not run this)
- `just lint` / `just lint-fix` — ruff check / `--fix`
- `just format` / `just format-check` — ruff format / `--check`
- `just typecheck` — mypy
- `just test` — pytest
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just i18n-check` — every language file has the base's keys and placeholders
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `main.py`, add nested `CLAUDE.md` files in high-value subfolders (routers, domain logic, integrations) following the `claude-md-tree` skill's context-packet pattern.
