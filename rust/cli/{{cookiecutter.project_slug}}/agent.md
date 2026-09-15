# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Rust (edition 2021), cargo, clippy, rustfmt
- CLI framework: clap (derive)
- Error handling: anyhow

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + i18n-check + fmt-check + lint + test)
- `just lint` — run clippy with -D warnings
- `just fmt` — format code with rustfmt
- `just fmt-check` — verify formatting
- `just test` — run tests
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just build-release` — optimized release build
- `just reinstall` — install binary from source
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
├── main.rs         # clap CLI entry point
└── i18n.rs         # t(locale, key, params), locale resolution
locales/            # en.json (base) + nl.json
Cargo.toml          # project config, dependencies
Justfile            # task runner
```

## Conventions

- Edition 2021 with release profile optimizations (LTO, strip, abort on panic)
- Entry point returns `anyhow::Result<()>`
- Keep functions small (5-10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface
- User-facing text goes through `i18n::t` with keys in `locales/en.json` (base) and `locales/nl.json` (informal je/jij); logs and developer errors stay English

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + i18n-check + fmt-check + lint + test.

Step-by-step alternative:

1. `just fmt`
2. `just lint`
3. `just test`

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- `cargo fmt` — format all Rust files
- `cargo clippy --fix --allow-dirty` — auto-fix clippy warnings

### Common Tasks

- Add a subcommand: define a new `#[derive(Parser)]` struct and add as `#[command(subcommand)]` variant
- Add a dependency: `cargo add <crate>`
- Add a module: create `src/<name>.rs` and add `mod <name>;` in `main.rs`
- Add or change text: edit the key in `locales/en.json` and `locales/nl.json`, call `i18n::t(lang, "section.key", &[])`, run `just i18n-check`

### Testing

- Test files: inline `#[cfg(test)] mod tests` or `tests/*.rs` integration tests
- Run a single test: `cargo test test_name`

### Boundaries

- Do not deploy, publish, or push
- Do not modify `[profile.*]` sections in `Cargo.toml` without asking
