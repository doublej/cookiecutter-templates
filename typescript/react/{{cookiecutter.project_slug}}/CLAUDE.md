# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A React single-page app built with Vite. `bun` for install, Biome for lint + format, Vitest for tests. Vite handles the dev server, HMR, and production bundling.

## Mental model

```
src/
├── App.tsx         # root component
└── main.tsx        # createRoot(...).render(<App/>)
index.html          # script src → /src/main.tsx
vite.config.ts      # Vite + Vitest config
package.json        # type: module, scripts, dependencies
tsconfig.json       # strict mode
biome.json          # lint + format rules
```

The runtime path is `index.html → main.tsx → <App/> → component tree`. New surfaces are functional components composed under `App.tsx`. Routing / state / data-fetching libraries are not included by default — add them when the app needs them, not before.

## Invariants

- ES modules everywhere (`"type": "module"`); Vite resolves imports.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter.
- Functional components with hooks; no class components.
- Functions / components stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; use React error boundaries for render-time recovery, not `try/catch` inside hooks.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a component** → new `.tsx` file under `src/`, import where it's used.
- **Add a hook** → new `useThing.ts` co-located with the component(s) that consume it.
- **Add a route** → introduce a router library (e.g. react-router) and split `App.tsx` into route components.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — start Vite dev server (agent must not run this)
- `just build` — production build
- `just preview` — preview the production build
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `App.tsx`, add nested `CLAUDE.md` files in high-value subfolders (`components/`, `routes/`, `hooks/`, design system, integrations) following the `claude-md-tree` skill's context-packet pattern.
