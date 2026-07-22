# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- SvelteKit + Vite
- GSAP for animations

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just dev` — start dev server
- `just build` — production build
- `just preview` — preview production build
- `just sync` — sync SvelteKit types
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `svelte-check`
- `just test` — run tests
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
├── routes/
│   └── +page.svelte    # home page
├── lib/                # shared modules
└── app.html            # HTML shell
svelte.config.js        # SvelteKit config
vite.config.ts          # Vite config
package.json            # project config, dependencies
tsconfig.json           # TypeScript config
biome.json              # linter/formatter config
Justfile                # task runner
```

## Conventions

- ES modules (`"type": "module"`)
- Strict TypeScript config
- Biome for linting and formatting (not ESLint/Prettier)
- SvelteKit file-based routing (`src/routes/`)
- Shared code in `src/lib/`
- GSAP for animations (pre-installed) — Svelte `transition:` directives only for trivial enter/leave
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + lint + typecheck + test.

Step-by-step alternative:

1. `just lint-fix`
2. `just sync` (after adding/renaming routes)
3. `just typecheck`
4. `just test`

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command
- `just sync` — regenerate SvelteKit types after route changes

### Common Tasks

- Add a page: create `src/routes/<path>/+page.svelte`
- Add a server route: create `src/routes/<path>/+server.ts`
- Add a load function: create `+page.ts` or `+page.server.ts` alongside the page
- Add a shared component: create it in `src/lib/components/`
- Use the `$lib/` alias for imports from `src/lib/`
- Add an animation: GSAP inside `$effect`/`onMount` (client-only), kill tweens on teardown
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Test load functions by importing directly and mocking fetch/params
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not run `just dev` — never start the dev server
- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
- Do not modify `svelte.config.js` without asking
