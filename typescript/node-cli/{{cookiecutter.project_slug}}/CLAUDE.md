# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A TypeScript command-line tool. `bun` for install + run, `tsx` for dev watch, Biome for lint + format, Vitest for tests. Built artifact is published-shaped (single bin entry in `package.json`).

## Mental model

```
src/
├── cli.ts          # CLI entry — argument parsing + dispatch
└── index.ts        # main logic, importable as a library
package.json        # bin: { "{{ cookiecutter.project_slug }}": "dist/cli.js" }
tsconfig.json       # strict mode
biome.json          # lint + format rules
```

The runtime path is `bin → cli.ts → main logic`. `cli.ts` only knows about argv + I/O; the actual work lives in `index.ts` (or sibling modules) so it can be reused programmatically.

## Invariants

- ES modules everywhere (`"type": "module"`); imports use explicit `.js` extensions.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; the CLI translates them to exit codes + stderr.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a command / flag** → extend argv parsing in `cli.ts`, dispatch to a function in `index.ts`.
- **Add main-logic surface** → export a new function from `index.ts` (keep CLI-shaped concerns out).
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — watch mode (agent must not run this)
- `just run-cli` — run the CLI (alias `just run`)
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just build` — production build
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past `cli.ts` + `index.ts`, add nested `CLAUDE.md` files in high-value subfolders (commands, domain logic) following the `claude-md-tree` skill's context-packet pattern.
