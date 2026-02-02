# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- CLI entry point with tsx for dev

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just run` — run the CLI
- `just dev` — start dev mode with watch
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues

## Project Structure

```
src/
├── cli.ts          # CLI entry point
└── index.ts        # main logic
package.json        # project config, dependencies, bin entry
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

- Add a CLI command: define the command logic in `src/` and wire it in `cli.ts`
- Add argument parsing: use the project's argument parsing approach in `cli.ts`
- Add a subcommand: create a new module in `src/` and import it in the CLI entry point
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Test command output by invoking the CLI function and asserting on results
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
