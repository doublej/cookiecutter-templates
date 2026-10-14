# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Author: {{ cookiecutter.author }}

## Requirements

- Swift 5.9+
- macOS {{ cookiecutter.deployment_target }}+

## Getting Started

```bash
swift build
just run
```

Or open in Xcode:

```bash
open Package.swift
```

## Common Commands

| Command | Description |
|---------|-------------|
| `swift build` | Build the project |
| `just run` | Build `.build/<Module>.app` and open it (a real app: Dock, Cmd-Tab, focus) |
| `swift test` | Run tests |

## Project Structure

```
{{ cookiecutter.project_slug }}/
  main.swift     # SwiftUI app entry point
Package.swift    # SPM manifest
```
