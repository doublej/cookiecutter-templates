# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Rust command-line tool. Cargo manages the workspace, `clap` (derive) parses args, `anyhow` carries errors. Built as a single release binary tuned for size + speed (LTO, strip, abort-on-panic).

## Mental model

```
src/
├── main.rs         # clap derive entry — `fn main() -> anyhow::Result<()>`
└── i18n.rs         # `t(locale, key, params)`, locale resolution (--lang → LC_ALL/LC_MESSAGES/LANG → en)
locales/            # en.json (base, fallback) + nl.json, embedded at compile time
Cargo.toml          # package metadata, deps, release profile
```

The runtime path is `binary → main → clap parse → command dispatch`. New subcommands extend the `clap` derive struct; complex logic moves into sibling modules and is called from `main`.

## Invariants

- Edition 2024. Release profile keeps `lto = true`, `strip = true`, `panic = "abort"` — do not relax these without reason.
- `clippy -D warnings` is the lint bar — code must compile clean.
- `main` returns `anyhow::Result<()>` so `?` propagates errors to the binary exit code.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; do not swallow with `let _ = ...` or `.unwrap()` outside of true infallibility.
- `cargo` owns `Cargo.lock`. Add deps with `cargo add <crate>`.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.

## Common change patterns

- **Add a subcommand / arg** → extend the `clap` derive struct in `main.rs`, branch on the parsed enum.
- **Add a module** → new file under `src/`, declared with `mod <name>;` in `main.rs`.
- **Add a dependency** → `cargo add <crate>` (or `cargo add --dev <crate>` for tests).
- **Add or change text** → edit `locales/en.json` and `locales/nl.json`, call `i18n::t(lang, "section.key", &[("name", value)])`, run `just i18n-check`.
- **Add a language** → add `locales/<code>.json` (+ register in `FILES` in `src/i18n.rs`), run `just i18n-check`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `fmt-check` + `lint` + `test`

Recipe reference:

- `just lint` — `cargo clippy -- -D warnings`
- `just fmt` / `just fmt-check` — `cargo fmt` / `--check`
- `just test` — `cargo test`
- `just build-release` — optimised release build
- `just reinstall` — `cargo install --path . --force`
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just i18n-check` — every language file has the base's keys and placeholders
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `main.rs`, add nested `CLAUDE.md` files in high-value subfolders (`src/<module>/`, integrations, FFI surfaces) following the `claude-md-tree` skill's context-packet pattern.
