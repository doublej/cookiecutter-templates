# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Raycast extension: React + TypeScript, built and run by the `ray` CLI (ships with the Raycast app). `bun` for install, ESLint (`@raycast` config) for lint. No test suite — verification is lint + build + manual run in Raycast.

## Mental model

```
package.json        # Raycast manifest — commands[], preferences[], deps
src/
├── hello.tsx       # one file per command (name matches commands[].name)
└── lib/prefs.ts    # typed preferences + PATH builder
assets/
└── command-icon.png
```

Each entry in `package.json` → `commands[]` maps to a `src/<name>.tsx` file whose default export is the command. Preferences declared in the manifest are read via `getPreferenceValues` (wrapped in `src/lib/prefs.ts`).

## Invariants

- `package.json` **is** the Raycast manifest — commands and preferences live there, not in code.
- Raycast spawns processes with a bare env: **no user PATH**. Any spawned binary must be resolved via the `extraPath` preference + `buildPath()` (`src/lib/prefs.ts`), never assumed on PATH.
- Spawn with argv arrays (`execFile`), never shell strings — filenames contain spaces/unicode.
- ESLint with the `@raycast` config is the only linter; `ray lint` runs it.

## Common change patterns

- **Add a command** → new `src/<name>.tsx` with a default-export component + entry in `commands[]` in `package.json`.
- **Add a preference** → entry in `preferences[]` + extend the `Prefs` interface in `src/lib/prefs.ts`.
- **Add a dependency** → `bun add <pkg>`.

## Verification

```sh
bun run lint       # ray lint
bun run build      # ray build — catches type/bundle errors
```

No tests. Verify behavior manually: `bun run dev` registers the extension in Raycast with hot reload.

## Related context

- [agent.md](agent.md) — verify loop, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook
