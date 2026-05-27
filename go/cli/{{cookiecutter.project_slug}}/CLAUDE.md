# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Go command-line tool built on the standard library. `go` manages the module, the `flag` package parses args, errors bubble up to `main` which sets the exit code. No third-party dependencies by default.

## Mental model

```
main.go          # entry — main() → run(args) → process(inputs, verbose)
main_test.go     # table-free unit tests for run/process
go.mod           # module path + Go version
Justfile         # task runner
```

The runtime path is `binary → main → run (flag parse) → process`. `main` does nothing but call `run` and translate a returned error into a non-zero exit. New behaviour goes in `process` or sibling functions; new flags are registered on the `FlagSet` in `run`.

## Invariants

- Go 1.24, stdlib-only. Add a dependency only with a reason (`go get <module>`); keep `go.mod`/`go.sum` committed.
- `go vet ./...` must be clean — it is the lint bar.
- `gofmt` is non-negotiable: all `.go` files stay formatted (`just fmt`).
- `main` is thin; real logic lives in testable functions that return `error`.
- Errors surface — return them up to `main`. Do not `panic` for expected failures or discard errors with `_`.
- Functions stay small (5–10 lines target, 20 max); ≤2 params where practical.

## Common change patterns

- **Add a flag** → register it on the `FlagSet` in `run`, thread the value into `process`.
- **Add a subcommand** → switch on `fs.Args()[0]` in `run`, or split into a `cmd/` layout if it grows.
- **Add a package** → new dir with its own `package <name>`, import via the module path in `go.mod`.
- **Add a dependency** → `go get <module>` then `go mod tidy`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `fmt-check` + `lint` (`go vet`) + `test`

Recipe reference:

- `just lint` — `go vet ./...`
- `just fmt` / `just fmt-check` — `gofmt -w .` / fail if any file is unformatted
- `just test` — `go test ./...`
- `just run -- <args>` — `go run .`
- `just build` / `just build-release` — compile all packages / stripped release binary into `bin/`
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this grows past a single `main.go`, add nested `CLAUDE.md` files in high-value packages (`internal/<pkg>/`, `cmd/<name>/`) following the `claude-md-tree` skill's context-packet pattern.
