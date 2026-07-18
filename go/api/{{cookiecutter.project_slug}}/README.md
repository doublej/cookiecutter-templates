# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- [Go](https://go.dev/dl/) 1.24+

## Getting Started

```bash
go run .
curl localhost:{{ cookiecutter.port }}/healthz
```

Set `PORT` to change the listen address (default `{{ cookiecutter.port }}`).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness check (`{"status":"ok"}`) |
| `GET` | `/` | Default greeting |

## Common Commands

| Command | Description |
|---------|-------------|
| `go run .` | Start the server |
| `go test ./...` | Run tests |
| `just build-release` | Build a stripped release binary into `bin/` |
| `just check` | Run all quality gates |

## Project Structure

```
main.go          # entry point (signal ctx, logger, $PORT)
server.go        # run / routes / handlers
server_test.go   # handler tests
```
