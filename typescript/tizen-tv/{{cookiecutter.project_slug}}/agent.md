# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- TypeScript, bun, Biome, Vitest
- SvelteKit + Vite, `@sveltejs/adapter-static` (no SSR — the TV runs static files)
- Samsung Tizen TV web app: `static/config.xml`, packaged with the Tizen Studio CLI
- GSAP for animations

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + typecheck + test)
- `just install` — install dependencies (`bun install`)
- `just dev` — start dev server (arrow keys stand in for the remote)
- `just build` — static build into `build/`
- `just preview` — preview production build
- `just sync` — sync SvelteKit types
- `just wgt` — package `build/` into `dist/*.wgt`
- `just deploy <ip>` — connect to a TV over sdb, install and run
- `just lint` / `just lint-fix` — Biome check / --fix
- `just typecheck` — `svelte-check`
- `just test` — run tests
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/
├── routes/
│   ├── +layout.ts       # ssr = false, prerender = true
│   ├── +layout.svelte   # 1920x1080 shell + remote handler
│   └── +page.svelte     # home screen
├── lib/
│   ├── remote.ts        # key codes, focus movement, exit
│   ├── spatial.ts       # pure directional-focus geometry
│   └── tizen.d.ts       # window.tizen ambient types
└── app.html             # HTML shell
static/config.xml        # Tizen widget manifest
svelte.config.js         # adapter-static config
vite.config.ts           # Vite config (build.target = TV Chromium)
Justfile                 # task runner
```

## Conventions

- ES modules (`"type": "module"`)
- Strict TypeScript config
- Biome for linting and formatting (not ESLint/Prettier)
- SvelteKit file-based routing (`src/routes/`), shared code in `src/lib/`
- Everything prerendered, no server code — no `+page.server.ts`, no `+server.ts`
- Focusable elements carry `data-focusable`; no scrolling, fixed 1920x1080
- User-facing text lives in `messages/{en,nl}.json` (en base, nl informal) and is read via `m.<key>()` — never hardcoded
- GSAP for animations — `transform`/`opacity` only, TV GPUs are weak
- Keep functions small (5–10 lines target, 20 max)
- Handle errors at boundaries; let unexpected errors surface

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + i18n-check + lint + typecheck + test.

Step-by-step alternative:

1. `just lint-fix`
2. `just sync` (after adding/renaming routes)
3. `just typecheck`
4. `just test`

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- `bun run biome check --write src/` — auto-fix lint and format issues in one command
- `just sync` — regenerate SvelteKit types after route changes

### Common Tasks

- Add a screen: create `src/routes/<path>/+page.svelte`, mark focusables with `data-focusable`
- Handle a media/colour key: `registerKeys([...])` on mount, match `event.keyCode` against `KEY` in `$lib/remote.ts`
- Change focus behaviour: edit `pickNext()` in `$lib/spatial.ts` and its test
- Add a shared component: create it in `src/lib/components/`
- Add an animation: GSAP inside `$effect`/`onMount`, kill tweens on teardown
- Add a dependency: `bun add <package>`
- Add or change text: edit every `messages/*.json`, call `m.<key>()` from `$lib/paraglide/messages`, run `just i18n-check`

### Testing

- Test files: `src/**/*.test.ts` (co-located with source)
- Framework: Vitest
- Keep TV logic pure and testable — DOM/Tizen glue in `remote.ts`, geometry in `spatial.ts`
- Run a single test: `bun run vitest run src/lib/spatial.test.ts`

### Boundaries

- Do not run `just dev` — never start the dev server
- Do not deploy (`just wgt` / `just deploy`) or push
- Do not add SSR or server routes — the TV has no server
- Do not edit `static/config.xml` identity fields (package id, app id) without asking
- Do not install ESLint or Prettier — this project uses Biome
