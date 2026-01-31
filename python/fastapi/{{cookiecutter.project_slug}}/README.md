# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Requirements

- Python >= {{ cookiecutter.python_version }}
- [uv](https://docs.astral.sh/uv/)

## Getting Started

```bash
uv sync
uv run uvicorn {{ cookiecutter.project_slug.replace('-', '_') }}.main:app --reload
```

## Common Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run uvicorn ... --reload` | Start dev server |
| `uv run pytest` | Run tests |

## Project Structure

```
src/{{ cookiecutter.project_slug.replace('-', '_') }}/
  __init__.py
  main.py        # FastAPI app and routes
```
