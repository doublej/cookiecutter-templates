# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- Background worker with tsx for dev

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just dev` / `just start` — watch / run the worker
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `tsc --noEmit`
- `just test` — run tests
- `just build` — production build
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
└── index.ts        # worker entry point
package.json        # project config, dependencies
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

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command

### Common Tasks

- Add a job handler: define a handler function in `src/` and register it in `index.ts`
- Add a scheduled task: create a cron/interval-based task in the worker entry point
- Add queue processing logic: define a processor function and wire it to the queue
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Mock timers for cron/interval tests (`vi.useFakeTimers()`)
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not run `just dev` or `just start` — never start the worker
- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
