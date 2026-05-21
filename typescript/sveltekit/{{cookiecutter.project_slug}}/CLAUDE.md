# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A SvelteKit application built with Vite. `bun` for install, Biome for lint + format, `svelte-check` for typechecking, Vitest for tests. SvelteKit owns routing, SSR, and the build adapter.

## Mental model

```
src/
├── routes/
│   └── +page.svelte    # home page (file-based routing)
├── lib/                # shared modules — import via `$lib/...`
└── app.html            # HTML shell
svelte.config.js        # SvelteKit + adapter config
vite.config.ts          # Vite + Vitest config
package.json            # type: module, scripts, dependencies
tsconfig.json           # extends .svelte-kit/tsconfig.json
biome.json              # lint + format rules
```

The runtime path is `request → src/routes/<path>/+page(.server).svelte → render`. `src/lib/` holds anything reusable; consume via the `$lib` alias. `.svelte-kit/` is generated — never edit by hand.

## Invariants

- File-based routing under `src/routes/` — folder name = URL segment, `+page.svelte` / `+page.ts` / `+page.server.ts` are SvelteKit-reserved.
- Shared code lives in `src/lib/` and imports via `$lib/...`.
- Strict TypeScript — `svelte-check` is the source of truth for types in `.svelte` files.
- Biome handles `.ts` / `.js` / `.json`; Svelte file formatting follows Svelte / Prettier conventions when needed.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; SvelteKit's `+error.svelte` / `hooks.server.ts` translate them to responses.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a route** → new folder under `src/routes/` with a `+page.svelte`.
- **Add data loading** → sibling `+page.ts` (universal) or `+page.server.ts` (server-only).
- **Add an API endpoint** → `+server.ts` with `GET` / `POST` / etc. exports.
- **Add shared code** → module under `src/lib/`, imported via `$lib/...`.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — Vite dev server (agent must not run this)
- `just build` — production build
- `just preview` — preview the production build
- `just sync` — regenerate `.svelte-kit/` types
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `svelte-check`
- `just test` — Vitest
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (`src/lib/<feature>/`, `src/routes/<section>/`, design system, integrations) following the `claude-md-tree` skill's context-packet pattern.
