# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Swift, SwiftPM, SwiftUI
- macOS deployment target: {{ cookiecutter.deployment_target }}

## Commands

Use `just` as the task runner:

- `just install` — resolve package dependencies
- `just check` — run all checks (loc-check + build + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just run` — build and run
- `just build` — debug build
- `just build-release` — release build
- `just test` — run tests
- `just xcode` — open in Xcode

## Project Structure

```
{{ cookiecutter.project_slug }}/
└── ...             # SwiftUI app source
Package.swift       # SwiftPM manifest
Justfile            # task runner
```

## Conventions

- SwiftPM for dependency management
- SwiftUI for UI layer
- async/await for concurrency
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

See [agent.md](agent.md) for AI coding agent workflow and guidelines.
