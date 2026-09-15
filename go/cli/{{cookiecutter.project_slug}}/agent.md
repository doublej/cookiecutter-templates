# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Go 1.24, standard library only
- CLI parsing: `flag` (stdlib)
- Tooling: `go vet`, `gofmt`, `go test`

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + i18n-check + fmt-check + lint + test)
- `just i18n-check` — every language file has the base's keys and placeholders
- `just lint` — `go vet ./...`
- `just fmt` — format with `gofmt`
- `just fmt-check` — fail if any file is unformatted
- `just test` — `go test ./...`
- `just run -- <args>` — run the CLI
- `just build` — `go build ./...`
- `just build-release` — stripped release binary into `bin/`
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
main.go          # flag-based CLI entry point
main_test.go     # unit tests
internal/i18n/   # translator + locales/{en,nl}.json
go.mod           # module config
Justfile         # task runner
```

## Conventions

- Stdlib-first; add dependencies only with a reason (`go get` + `go mod tidy`)
- `main` stays thin; logic lives in functions returning `error`
- Keep functions small (5-10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface (no silent `_`)
- User-facing text goes through `i18n.T`/`i18n.N` with keys in every `internal/i18n/locales/*.json` (en base, nl informal); logs and developer errors stay English

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

- `gofmt -w .` — format all Go files
- `go mod tidy` — sync go.mod/go.sum with imports

### Common Tasks

- Add or change text: edit `internal/i18n/locales/en.json` and `nl.json`, call `i18n.T(locale, "key")`, run `just i18n-check`
- Add a flag: register on the `FlagSet` in `run`, thread into `process`
- Add a dependency: `go get <module>` then `go mod tidy`
- Add a package: new dir with `package <name>`, import via module path

### Testing

- Test files: `*_test.go` next to the code, `func TestXxx(t *testing.T)`
- Run a single test: `go test -run TestName ./...`

### Boundaries

- Do not deploy, publish, or push
- Do not add dependencies or edit `go.mod`'s module path without asking
