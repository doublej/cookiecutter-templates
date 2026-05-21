# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

An iOS SwiftUI application built with SwiftPM. Deployment target: `{{ cookiecutter.deployment_target }}`. SwiftLint is the lint bar; tests are SwiftPM-driven.

## Mental model

```
{{ cookiecutter.project_slug }}/
└── ...             # SwiftUI app source (views, models, services)
Package.swift       # SwiftPM manifest — executable target + tests
Justfile            # task runner
.swiftlint.yml      # strict ruleset
```

The runtime path is `App entry (`@main struct ... : App`) → root `Scene` → `View` hierarchy`. New surfaces are SwiftUI `View` types composed from the root scene; persistence / network work belongs in `@Observable` services owned at the app or scene level.

## Invariants

- SwiftPM is the build system — no Xcode project files committed. `just xcode` opens the package in Xcode for editing.
- SwiftUI for the UI layer (UIKit only where SwiftUI cannot reach).
- `async` / `await` for concurrency; avoid completion handlers and explicit `DispatchQueue` work in new code.
- SwiftLint `--strict` must pass — no warnings.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; throw, propagate with `try`, handle at the SwiftUI layer.

## Common change patterns

- **Add a view** → new `struct ...: View` in a dedicated file.
- **Add a model** → `struct` (value-typed) or `@Observable` class for state that survives across views.
- **Add a service** → class with `async` methods, injected via environment or initializer.
- **Add a dependency** → declare in `Package.swift` `dependencies:` and the executable target's `dependencies:`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `build` + `test`

Recipe reference:

- `just install` — resolve SwiftPM dependencies (warns if SwiftLint missing)
- `just lint` — `swiftlint --strict`
- `just lint-fix` — `swiftlint --fix` then relint
- `just build` / `just build-release` — debug / release build
- `just test` — SwiftPM test
- `just xcode` — open in Xcode (required for running on a simulator / device)
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove `.build/` artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- `.swiftlint.yml` — strict lint ruleset
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (Views, Services, Models, integrations) following the `claude-md-tree` skill's context-packet pattern.
