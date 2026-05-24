# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Rust (edition 2021), cargo, clippy, rustfmt
- CLI framework: clap (derive)
- Error handling: anyhow

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + fmt-check + lint + test)
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
└── main.rs         # clap CLI entry point
Cargo.toml          # project config, dependencies
Justfile            # task runner
```

## Conventions

- Edition 2021 with release profile optimizations (LTO, strip, abort on panic)
- Entry point returns `anyhow::Result<()>`
- Keep functions small (5-10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + fmt-check + lint + test.

Step-by-step alternative:

1. `just fmt`
2. `just lint`
3. `just test`

### Auto-fixable

- `cargo fmt` — format all Rust files
- `cargo clippy --fix --allow-dirty` — auto-fix clippy warnings

### Common Tasks

- Add a subcommand: define a new `#[derive(Parser)]` struct and add as `#[command(subcommand)]` variant
- Add a dependency: `cargo add <crate>`
- Add a module: create `src/<name>.rs` and add `mod <name>;` in `main.rs`

### Testing

- Test files: inline `#[cfg(test)] mod tests` or `tests/*.rs` integration tests
- Run a single test: `cargo test test_name`

### Boundaries

- Do not deploy, publish, or push
- Do not modify `[profile.*]` sections in `Cargo.toml` without asking
