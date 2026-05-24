# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- [Rust](https://rustup.rs/) (edition 2021)

## Getting Started

```bash
cargo build
cargo run -- --help
```

## Common Commands

| Command | Description |
|---------|-------------|
| `cargo build` | Build debug binary |
| `cargo run -- --help` | Show CLI help |
| `cargo test` | Run tests |
| `just reinstall` | Install binary from source |
| `just build-release` | Build optimized release binary |

## Project Structure

```
src/
  main.rs          # clap CLI entry point
```
