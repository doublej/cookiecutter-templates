# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Swift, SwiftPM, SwiftUI
- macOS deployment target: {{ cookiecutter.deployment_target }}

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + build + test)
- `just install` — resolve package dependencies (warns if SwiftLint missing)
- `just lint` — run SwiftLint strict
- `just lint-fix` — autocorrect + relint strict
- `just run-app` — build and run (alias: `just run`)
- `just build` — debug build
- `just build-release` — release build
- `just test` — run tests
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove `.build/` artifacts
- `just xcode` — open in Xcode
- `just update-scaffold` — pull updates from the cookiecutter template

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
