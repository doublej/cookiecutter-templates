# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome
- Bun test runner, package exports via `dist/`

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `tsc --noEmit`
- `just test` — run tests
- `just build` — compile TypeScript declarations
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template
- `bun run dev` — run package entry in watch mode

## Project Structure

```
src/
├── index.ts        # package entry point
└── index.test.ts   # bun tests
package.json        # project config, dependencies, exports
tsconfig.json       # TypeScript config
biome.json          # linter/formatter config
Justfile            # task runner
```

## Conventions

- ES modules (`"type": "module"`)
- Strict TypeScript config
- Bun test with `bun:test`
- Biome for linting and formatting (not ESLint/Prettier)
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + lint + typecheck + test.

Step-by-step alternative:

1. `just lint-fix`
2. `just typecheck`
3. `just test`
4. `just build` — verify type declarations compile

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command

### Common Tasks

- Add an exported function or class: create it in `src/` and re-export from `src/index.ts`
- Update barrel exports: keep `src/index.ts` as the single public entry point
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Bun test (`bun:test`)
- Test the public API surface (what's exported from `index.ts`)
- Run a single test: `bun test src/index.test.ts`

### Boundaries

- Do not deploy, publish, or push
- Do not install Jest or Vitest — this project uses Bun test
- Do not install ESLint or Prettier — this project uses Biome
- Do not modify `declaration` or `outDir` settings in `tsconfig.json`
