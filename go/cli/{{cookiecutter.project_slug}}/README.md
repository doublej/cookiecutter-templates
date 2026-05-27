# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- [Go](https://go.dev/dl/) 1.24+

## Getting Started

```bash
go build ./...
go run . --help
```

## Common Commands

| Command | Description |
|---------|-------------|
| `go run . -- <args>` | Run the CLI |
| `go build ./...` | Compile all packages |
| `go test ./...` | Run tests |
| `just build-release` | Build a stripped release binary into `bin/` |
| `just check` | Run all quality gates |

## Project Structure

```
main.go          # flag-based CLI entry point
main_test.go     # unit tests
```
