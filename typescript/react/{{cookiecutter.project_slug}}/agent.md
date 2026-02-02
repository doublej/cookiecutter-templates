# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- React + Vite

## Commands

Use `just` as the task runner:

- `just check` — run all checks (loc-check + lint + typecheck + test)
- `just loc-check` — check file lengths (warn >300, error >400 lines)
- `just dev` — start dev server
- `just build` — production build
- `just preview` — preview production build
- `just test` — run tests
- `just lint-fix` — auto-fix lint issues

## Project Structure

```
src/
├── App.tsx         # root component
└── main.tsx        # app entry point
index.html          # HTML template
vite.config.ts      # Vite config
package.json        # project config, dependencies
tsconfig.json       # TypeScript config
biome.json          # linter/formatter config
Justfile            # task runner
```

## Conventions

- ES modules (`"type": "module"`)
- Strict TypeScript config
- Biome for linting and formatting (not ESLint/Prettier)
- Functional components with hooks
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

- Add a component: create a `.tsx` file in `src/`
- Add a hook: create a `use*.ts` file in `src/`
- Add a route: if using a router, add a route entry and create the page component
- Add a CSS module: create a `.module.css` file next to the component
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.tsx` (co-located with source)
- Framework: Vitest (add `@testing-library/react` for component tests)
- Test component rendering and interaction
- Run a single test: `bun run vitest run src/foo.test.tsx`

### Boundaries

- Do not run `just dev` — never start the dev server
- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
- Do not modify `vite.config.ts` without asking
