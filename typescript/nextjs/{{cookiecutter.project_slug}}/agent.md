# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- Next.js 16 (App Router) + React 19
- next-intl for translations (`en` at `/`, `nl` at `/nl`)
- GSAP (+ `@gsap/react`) for animations

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + i18n-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just dev` / `just preview` — start dev server / run production build
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `tsc --noEmit`
- `just test` — run tests
- `just build` — production build
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just i18n-check` — check every language file has the base's keys and placeholders
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
├── app/
│   ├── [locale]/
│   │   ├── layout.tsx  # root layout
│   │   └── page.tsx    # home page
│   └── globals.css     # global styles
├── components/         # LanguageSwitcher.tsx
├── i18n/               # routing.ts (locales), request.ts, navigation.ts
└── proxy.ts            # locale detection and redirects
messages/               # en.json (base), nl.json
next.config.ts          # Next.js config
vitest.config.ts        # Vitest config
package.json            # project config, dependencies
tsconfig.json           # TypeScript config
biome.json              # linter/formatter config
Justfile                # task runner
```

## Conventions

- App Router (`src/app/[locale]/`) — file-based routing; `Link` and `redirect` come from `@/i18n/navigation`
- Server Components by default; add `'use client'` only when needed
- User-facing text lives in `messages/<locale>.json` (`en` base and fallback, `nl` informal je/jij) — never hardcode it; logs stay English
- Biome for linting and formatting (not ESLint/Prettier)
- Path alias `@/` maps to `src/`
- GSAP for animations (pre-installed) — not framer-motion or other animation libs
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

- Add a page: create `src/app/[locale]/<path>/page.tsx`
- Add an API route: create `src/app/api/<path>/route.ts`
- Add a layout: create `src/app/[locale]/<path>/layout.tsx`
- Add or change text: add the key to every `messages/<locale>.json`, read it with `useTranslations('<Namespace>')`, run `just i18n-check`
- Add a language: add `messages/<locale>.json`, add the locale to `locales` in `src/i18n/routing.ts`, run `just i18n-check`
- Add a Server Action: add `'use server'` to a function in a Server Component or separate file
- Add a Client Component: add `'use client'` at top of file
- Use path alias: `import { foo } from '@/lib/foo'`
- Add an animation: `'use client'` component with `useGSAP()` from `@gsap/react`
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
