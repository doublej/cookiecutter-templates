# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Swift, SwiftPM, SwiftUI
- iOS deployment target: {{ cookiecutter.deployment_target }}

## Commands

Use `just` as the task runner:

- `just install` — resolve package dependencies
- `just check` — run all checks (loc-check + build + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
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

## Agent

### Verify Loop

Run after every change:

1. `just build`
2. `just test`

### Auto-fixable

None — fix compiler errors manually.

### Common Tasks

- Add a SwiftUI view: create a new `.swift` file with a `View` struct
- Add a model: create a `Codable` + `Identifiable` struct
- Add a service: create a class/struct with `async`/`await` methods
- Add a dependency: add the package URL to `Package.swift` dependencies

### Testing

- Test files: `Tests/*Tests.swift`
- Framework: XCTest
- Run a single test: `swift test --filter FooTests/testBar`

### Boundaries

- Do not run `just xcode` — never open Xcode
- Do not deploy, archive, or push
- Do not modify the deployment target without asking
