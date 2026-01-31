# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- Python >= {{ cookiecutter.python_version }}
- [uv](https://docs.astral.sh/uv/)

## Getting Started

```bash
uv sync
uv run {{ cookiecutter.project_slug }} hello
```

## Common Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run {{ cookiecutter.project_slug }} --help` | Show CLI help |
| `uv run pytest` | Run tests |

## Project Structure

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
  __init__.py
  cli.py         # Click CLI commands
```
