# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Author: {{ cookiecutter.author }}

## Requirements

- Swift 5.9+
- macOS {{ cookiecutter.deployment_target }}+

## Getting Started

```bash
swift build
swift run {{ cookiecutter.project_slug }}
```

Or open in Xcode:

```bash
open Package.swift
```

## Common Commands

| Command | Description |
|---------|-------------|
| `swift build` | Build the project |
| `swift run` | Run the app |
| `swift test` | Run tests |

## Project Structure

```
{{ cookiecutter.project_slug }}/
  main.swift     # SwiftUI app entry point
Package.swift    # SPM manifest
```
