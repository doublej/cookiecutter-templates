# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A TypeScript HTTP server. Runs under `bun` for dev (with `tsx` watch) and ships as a built `dist/` artifact. Biome handles lint + format (replacing ESLint / Prettier). Vitest runs the tests.

## Mental model

```
src/
├── env.ts          # parsed, typed environment config
├── i18n.ts         # t(), negotiate(Accept-Language), localeFromEnv() — zero-dep
├── index.ts        # server entry — wires env → server → port
├── locales/        # en.json (base, fallback), nl.json
└── logger.ts       # logging utility
package.json        # type: module, scripts, dependencies
tsconfig.json       # strict mode
biome.json          # lint + format rules
```

The runtime path is `bun → tsx → src/index.ts → server`. `env.ts` is the one place runtime config is parsed; `index.ts` composes it. New routes / middleware live in dedicated modules that `index.ts` imports.

## Invariants

- ES modules everywhere (`"type": "module"`); imports use explicit `.js` extensions for compiled output.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter — do not add ESLint or Prettier configs.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; do not swallow with `try/catch`.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.

## Common change patterns

- **Add or change text** → edit `src/locales/*.json`, call `t(locale, 'key', params)` with the `locale` that `index.ts` derives from `Accept-Language`, run `just i18n-check`.
- **Add a language** → add `src/locales/<locale>.json` (+ register in `catalogs` in `src/i18n.ts`), run `just i18n-check`.
- **Add a route / handler** → new module under `src/`, wire it into `index.ts`.
- **Add config** → extend the parser in `env.ts`; consume the typed result everywhere else.
- **Add middleware** → compose it in `index.ts` between env load and server start.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — start dev server with watch (agent must not run this)
- `just start` — run the built artifact
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just build` — production build
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just i18n-check` — every language file has the base's keys and placeholders
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past `index.ts` + `env.ts`, add nested `CLAUDE.md` files in high-value subfolders (routes, domain logic, integrations) following the `claude-md-tree` skill's context-packet pattern.
