# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Go HTTP service built on the standard library. `net/http`'s `ServeMux` (Go 1.22+ method+path patterns) routes requests, `log/slog` handles structured logging, and the server drains gracefully on SIGINT/SIGTERM. No third-party dependencies by default.

## Mental model

```
main.go          # entry — wires signal ctx + logger, reads $PORT, calls run
server.go        # run (listen + drain) · routes (mux) · handlers
server_test.go   # httptest-based handler tests
go.mod           # module path + Go version
Justfile         # task runner
```

The runtime path is `main → run → ListenAndServe`. A goroutine watches the signal-derived context and calls `shutdown` (10s drain) when it cancels. `routes` is the single place every endpoint is registered; handlers are plain `http.HandlerFunc`s.

## Invariants

- Go 1.24, stdlib-only. Add a dependency only with a reason (`go get <module>`); keep `go.mod`/`go.sum` committed.
- `go vet ./...` must be clean — it is the lint bar.
- `gofmt` is non-negotiable: all `.go` files stay formatted (`just fmt`).
- The server reads its port from `$PORT` (default `{{ cookiecutter.port }}`) — keep config env-driven.
- Shutdown stays graceful: route registration in `routes`, no `log.Fatal` inside handlers.
- Errors surface — return them up to `run`/`main`. Handlers write an explicit status; do not `panic` for expected failures.
- Functions stay small (5–10 lines target, 20 max); ≤3 params.

## Common change patterns

- **Add an endpoint** → register `mux.HandleFunc("METHOD /path", handler)` in `routes`, add the handler + a `httptest` test.
- **Add middleware** → wrap the `http.Handler` returned by `routes` (logging, auth, recovery).
- **Add config** → read another env var alongside `addr()`; thread it into `run`.
- **Add a package** → new dir with its own `package <name>`, import via the module path in `go.mod`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `fmt-check` + `lint` (`go vet`) + `test`

Recipe reference:

- `just lint` — `go vet ./...`
- `just fmt` / `just fmt-check` — `gofmt -w .` / fail if any file is unformatted
- `just test` — `go test ./...`
- `just run` — `go run .` (serves on `$PORT`, default {{ cookiecutter.port }})
- `just build` / `just build-release` — compile all packages / stripped release binary into `bin/`
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this grows past `main.go` + `server.go`, add nested `CLAUDE.md` files in high-value packages (`internal/<pkg>/`, `handlers/`) following the `claude-md-tree` skill's context-packet pattern.
