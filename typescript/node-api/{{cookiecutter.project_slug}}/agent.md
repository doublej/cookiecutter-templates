# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- HTTP server with tsx for dev

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just dev` — start dev server with watch mode
- `just start` — run production build
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues

## Project Structure

```
src/
├── env.ts          # environment config
├── index.ts        # server entry point
└── logger.ts       # logging utility
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

Run after every change:

1. `just lint-fix`
2. `just typecheck`
3. `just test`

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command

### Common Tasks

- Add an HTTP route handler: define a handler in `src/` and wire it to the server in `index.ts`
- Add middleware: create a middleware function and apply it before route handlers
- Add an env var: add the variable to `src/env.ts` with validation
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not run `just dev` or `just start` — never start the server
- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
