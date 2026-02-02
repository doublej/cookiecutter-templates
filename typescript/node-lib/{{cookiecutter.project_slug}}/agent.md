# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- Library (no server/CLI)

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just build` — compile TypeScript
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues

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

Run after every change:

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
- Framework: Vitest
- Test the public API surface (what's exported from `index.ts`)
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not deploy, publish, or push
- Do not install ESLint or Prettier — this project uses Biome
- Do not modify `declaration` or `outDir` settings in `tsconfig.json`
