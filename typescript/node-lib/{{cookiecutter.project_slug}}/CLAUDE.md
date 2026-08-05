# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A TypeScript library (no server, no CLI). `bun` for install, Biome for lint + format, Vitest for tests. The build produces `dist/` outputs consumed by other packages.

## Mental model

```
src/
└── index.ts        # public entry — exports the library surface
package.json        # exports, types, files
tsconfig.json       # strict mode, declaration emit
biome.json          # lint + format rules
```

The runtime path is `consumer import → dist/index.js (and .d.ts) → src/index.ts at dev time`. Everything exposed lives in `index.ts`; internals stay in sibling modules and are not re-exported.

## Invariants

- ES modules everywhere (`"type": "module"`); imports use explicit `.js` extensions.
- Strict TypeScript with declaration emit — public types must be stable.
- Biome is the only linter / formatter.
- Functions stay small (5–10 lines target, 20 max).
- Errors surface at the boundary — consumers handle them, the library does not log or `process.exit`.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a public export** → declare it in `src/index.ts`; cover it with a test.
- **Add an internal helper** → sibling module, imported by `index.ts`, not re-exported.
- **Bump the surface** → version + `exports` field in `package.json`.
- **Add a dependency** → `bun add <pkg>` (or `bun add -d <pkg>` for dev).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just lint` / `just lint-fix` — Biome check / `--write`
- `just typecheck` — `tsc --noEmit`
- `just test` — Vitest
- `just build` — compile TypeScript
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just loc-fix` — propose how to split the files `loc-check` rejected (advisory, writes nothing)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- [.claude/SPLITTING.md](.claude/SPLITTING.md) — how to split a file `loc-check` rejected without widening the public surface
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `index.ts`, add nested `CLAUDE.md` files in high-value subfolders (subpackages, integrations) following the `claude-md-tree` skill's context-packet pattern.
