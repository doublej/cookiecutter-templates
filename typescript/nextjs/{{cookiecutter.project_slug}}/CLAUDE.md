# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Next.js 15 application using the App Router and React 19. `bun` for install, Biome for lint + format, Vitest for tests. Turbopack runs the dev server.

## Mental model

```
src/
└── app/
    ├── layout.tsx      # root layout
    ├── page.tsx        # home page (server component by default)
    └── globals.css     # global styles
next.config.ts          # Next.js config
vitest.config.ts        # Vitest config
package.json            # type: module, scripts, dependencies
tsconfig.json           # strict mode, `@/*` → src/*
biome.json              # lint + format rules
```

The runtime path is `request → src/app/<segment>/page.tsx → server-rendered HTML → hydration where `"use client"` is declared`. Layouts wrap nested segments; `loading.tsx` / `error.tsx` are framework-reserved.

## Invariants

- App Router only (`src/app/`); do not introduce a `pages/` directory.
- Server Components are the default; opt into client with `"use client"` at the top of the file, and only for components that need it.
- Path alias `@/` maps to `src/` — use it consistently.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter — do not add ESLint or Prettier configs.
- Functions / components stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; use `error.tsx` for render-time recovery.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a route** → new folder under `src/app/` with `page.tsx`.
- **Add a layout** → `layout.tsx` next to the routes it wraps.
- **Add a server action** → exported `async function` with `"use server"`, called from a client component.
- **Add an API route** → `route.ts` with `GET` / `POST` / etc. exports.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — Next.js dev server with Turbopack (agent must not run this)
- `just preview` — `next start` against the production build
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just build` — production build
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (`src/app/<section>/`, `src/components/`, `src/lib/`, integrations) following the `claude-md-tree` skill's context-packet pattern.
