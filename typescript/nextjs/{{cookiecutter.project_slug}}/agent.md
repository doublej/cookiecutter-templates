# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- Next.js 15 (App Router) + React 19

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just dev` / `just preview` — start dev server / run production build
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `tsc --noEmit`
- `just test` — run tests
- `just build` — production build
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
└── app/
    ├── layout.tsx      # root layout
    ├── page.tsx        # home page
    └── globals.css     # global styles
next.config.ts          # Next.js config
vitest.config.ts        # Vitest config
package.json            # project config, dependencies
tsconfig.json           # TypeScript config
biome.json              # linter/formatter config
Justfile                # task runner
```

## Conventions

- App Router (`src/app/`) — file-based routing
- Server Components by default; add `'use client'` only when needed
- Biome for linting and formatting (not ESLint/Prettier)
- Path alias `@/` maps to `src/`
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

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command

### Common Tasks

- Add a page: create `src/app/<path>/page.tsx`
- Add an API route: create `src/app/api/<path>/route.ts`
- Add a layout: create `src/app/<path>/layout.tsx`
- Add a Server Action: add `'use server'` to a function in a Server Component or separate file
- Add a Client Component: add `'use client'` at top of file
- Use path alias: `import { foo } from '@/lib/foo'`
- Add a dependency: `bun add <package>`

### Testing

- Test files: `src/**/*.test.ts` or `src/**/*.test.tsx` (co-located with source)
- Framework: Vitest with jsdom environment
- Run a single test: `bun run vitest run src/foo.test.ts`

### Boundaries

- Do not run `just dev` — never start the dev server
- Do not deploy or push
- Do not install ESLint or Prettier — this project uses Biome
- Do not use the Pages Router (`pages/`) — this project uses App Router
