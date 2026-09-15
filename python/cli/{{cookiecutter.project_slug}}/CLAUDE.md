# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Python command-line tool built on Click. Single binary entry point declared in `pyproject.toml`, dependencies managed by `uv`, quality enforced by `ruff` / `mypy` / `pytest` and the `.quality.json` thresholds.

## Mental model

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
├── __init__.py
├── cli.py          # Click entry point — function `main`
├── i18n.py         # `t()` + locale resolution: --lang → LC_ALL / LC_MESSAGES / LANG → en
└── locales/        # en.json (base, fallback) + nl.json — every user-facing string
pyproject.toml      # [project.scripts] binds `{{ cookiecutter.project_slug }}` → `{{ cookiecutter.project_slug.replace('-', '_') }}.cli:main`
```

The runtime path is `console_script → cli.main → Click command tree`. New commands are decorators attached to a `click.Group`. The package is intentionally flat: add modules under `{{ cookiecutter.project_slug.replace('-', '_') }}/` only when `cli.py` outgrows itself.

## Invariants

- `src/` layout with hatchling — do not move code to a top-level package.
- Module name is `{{ cookiecutter.project_slug.replace('-', '_') }}` (slug with `-` → `_`); script entry point is `{{ cookiecutter.project_slug.replace('-', '_') }}.cli:main`.
- Functions stay small (5–10 lines target, 20 max — enforced by code review, not lint).
- Errors surface at the boundary; do not wrap unexpected exceptions in `try/except`.
- `uv` owns the lockfile. Add deps with `uv add <pkg>`, never edit `[project.dependencies]` by hand.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.

## Common change patterns

- **Add a command** → new `@cli.command()` (or `@<group>.command()`) function in `cli.py`.
- **Add a flag** → `@click.option()` decorator above the command function.
- **Extract a subcommand group** → `click.Group()` in a new module, registered via `cli.add_command(...)`.
- **Add a dependency** → `uv add <pkg>` (or `uv add --dev <pkg>`).
- **Add or change text** → edit `src/{{ cookiecutter.project_slug.replace('-', '_') }}/locales/*.json`, call `t("hello.greeting", locale, name=...)` with the locale from `@click.pass_obj`, run `just i18n-check`.
- **Add a language** → add `src/{{ cookiecutter.project_slug.replace('-', '_') }}/locales/<locale>.json` (no registration: `LOCALES` discovers it and `--lang` offers it), run `just i18n-check`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint` + `format-check` + `typecheck` + `test`

Recipe reference:

- `just install` — `uv sync`
- `just run-cli` — run the CLI (alias `just run`)
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
- As this project grows past a single `cli.py`, add nested `CLAUDE.md` files in high-value subfolders (domain logic, integrations) following the `claude-md-tree` skill's context-packet pattern.
