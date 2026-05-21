# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A TypeScript background worker — a long-running process that consumes from a queue / scheduler / stream rather than serving HTTP. `bun` for install + run, `tsx` for dev watch, Biome for lint + format, Vitest for tests.

## Mental model

```
src/
└── index.ts        # worker entry — connect, loop, graceful shutdown
package.json        # type: module, scripts, dependencies
tsconfig.json       # strict mode
biome.json          # lint + format rules
```

The runtime path is `bun → tsx → src/index.ts → consume loop`. The worker owns its lifecycle: connect on start, drain on `SIGTERM` / `SIGINT`, exit only after the in-flight job finishes (or times out).

## Invariants

- ES modules everywhere (`"type": "module"`); imports use explicit `.js` extensions.
- Strict TypeScript — no `// @ts-ignore`, no `any` without justification.
- Biome is the only linter / formatter.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary; a failed job should not bring down the worker silently — surface, log, ack/nack explicitly.
- Shutdown is cooperative: trap signals, stop accepting work, drain, then exit.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a job handler** → new module under `src/`, dispatched from the loop in `index.ts`.
- **Add a transport** (queue, stream, scheduler) → connect / disconnect lives next to the loop in `index.ts`.
- **Add config** → centralise env parsing so handlers receive typed config, not raw `process.env`.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — watch mode (agent must not run this)
- `just start` — run the built worker
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
- As this project grows past a single `index.ts`, add nested `CLAUDE.md` files in high-value subfolders (handlers, transports, integrations) following the `claude-md-tree` skill's context-packet pattern.
