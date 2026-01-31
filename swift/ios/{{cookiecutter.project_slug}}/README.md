# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Author: {{ cookiecutter.author }}

## Requirements

- Swift 5.9+
- iOS {{ cookiecutter.deployment_target }}+
- Xcode 15+

## Getting Started

```bash
swift build
open Package.swift  # Opens in Xcode
```

## Common Commands

| Command | Description |
|---------|-------------|
| `swift build` | Build the project |
| `swift test` | Run tests |
| `open Package.swift` | Open in Xcode |

## Project Structure

```
{{ cookiecutter.project_slug }}/
  main.swift     # SwiftUI app entry point
Package.swift    # SPM manifest
```
