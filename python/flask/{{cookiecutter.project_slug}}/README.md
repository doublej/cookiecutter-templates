# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- Python >= {{ cookiecutter.python_version }}
- [uv](https://docs.astral.sh/uv/)

## Getting Started

```bash
uv sync
uv run flask --app {{ cookiecutter.project_slug.replace('-', '_') }}.app run
```

Use `flask --debug run` for development with auto-reload.

## Common Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run flask --app ... run` | Start dev server |
| `uv run pytest` | Run tests |

## Project Structure

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
  __init__.py
  app.py         # Flask app and routes
```
