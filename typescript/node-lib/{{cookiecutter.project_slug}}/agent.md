# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- Library (no server/CLI)

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `tsc --noEmit`
- `just test` — run tests
- `just build` — compile TypeScript
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just loc-fix` — propose a split for each file `loc-check` rejected (advisory, writes nothing)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
└── index.ts        # library entry point
package.json        # project config, dependencies, exports
tsconfig.json       # TypeScript config
biome.json          # linter/formatter config
Justfile            # task runner
```

## Conventions

- ES modules (`"type": "module"`)
- Strict TypeScript config
- Biome for linting and formatting (not ESLint/Prettier)
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + i18n-check + lint + typecheck + test.

Step-by-step alternative:

1. `just lint-fix`
2. `just typecheck`
3. `just test`
4. `just build` — verify type declarations compile

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command

Mid-feature, a lint failure does not block delivery either: ship the feature and let the user
test it first, then run `lint-fix` while they're testing.

### Common Tasks

- Add an exported function or class: create it in `src/` and re-export from `src/index.ts`
- Update barrel exports: keep `src/index.ts` as the single public entry point
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Test the public API surface (what's exported from `index.ts`)
- Run a single test: `bun run vitest run src/foo.test.ts`

### Splitting an oversized file

`loc-check` failing means the file has more than one job — never trim it to fit. Run
`just loc-fix` for a proposed split, then read [.claude/SPLITTING.md](.claude/SPLITTING.md)
before accepting it: it covers seam selection, the `dir-check` interaction, and the rule that
a split must not add anything to the public surface.

Mid-feature, a `loc-check` failure does not block delivery: ship the feature and let the user
test it first. The split is a pure refactor with no behavior change — do it while the user is
testing, not before they get to try the feature.

### Boundaries

- Do not deploy, publish, or push
- Do not install ESLint or Prettier — this project uses Biome
- Do not modify `declaration` or `outDir` settings in `tsconfig.json`
