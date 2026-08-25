# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A SvelteKit app that ships as a Samsung TV (Tizen) `.wgt` package. Same stack as our web projects — `bun` for install, Biome for lint + format, `svelte-check` for typechecking, Vitest for tests, GSAP for animation — with three TV-specific twists: static prerendering, remote-control focus, and Tizen packaging.

## Mental model

```
src/
├── routes/
│   ├── +layout.ts       # ssr = false, prerender = true
│   ├── +layout.svelte   # global 1920x1080 shell, installs the remote handler
│   └── +page.svelte     # home screen
├── lib/
│   ├── remote.ts        # key codes, focus movement, app exit
│   ├── spatial.ts       # pure geometry: which element is "to the right"
│   └── tizen.d.ts       # ambient types for window.tizen
static/
└── config.xml           # Tizen widget manifest (copied to build/ verbatim)
svelte.config.js         # adapter-static + relative paths
vite.config.ts           # build.target pinned to the TV's Chromium
```

The runtime path is `TV launches build/index.html → SvelteKit hydrates client-side → +layout.svelte installs the keydown handler`. There is no server: `build/` is a folder of static files that `just wgt` signs into a `.wgt`.

## Invariants

- **No SSR, ever.** `+layout.ts` sets `ssr = false` and `prerender = true`; `paths.relative` keeps asset URLs relative. A server-only load function or an absolute `/asset` URL breaks the app on-device with no error you can see.
- **`static/config.xml` is the source of truth for app identity.** `tizen:application@package` must match the package id in the signing certificate. Bumping `required_version` means bumping `build.target` in `vite.config.ts` in the same commit — the TV's Chromium is old and silently fails on syntax it doesn't know.
- Every element the remote can land on carries `data-focusable` and a visible `:focus` style. Arrow keys never scroll — the layout is a fixed 1920x1080 with `overflow: hidden`.
- `window.tizen` is undefined in a desktop browser. Always optional-chain it (`$lib/remote.ts` does).
- Keep meaningful UI inside the 5% overscan safe area (the `body` padding in `+layout.svelte`).
- GSAP is the animation tool (`gsap` ships by default) — Svelte `transition:` directives only for trivial enter/leave. TV GPUs are weak: animate `transform` and `opacity`, nothing else.
- `bun` owns the lockfile. Add deps with `bun add <pkg>`.

## Common change patterns

- **Add a screen** → new folder under `src/routes/` with a `+page.svelte`; every focusable child gets `data-focusable`.
- **Handle a media / colour key** → `registerKeys([...])` from `$lib/remote.ts` on mount, then match `event.keyCode` against `KEY`.
- **Change focus behaviour** → `pickNext()` in `$lib/spatial.ts` (pure, covered by `spatial.test.ts`).
- **Use a TV-only API** (avplay, productinfo) → those live on `window.webapis`, which needs `<script src="$WEBAPIS/webapis/webapis.js"></script>` added to `src/app.html`.
- **Add an animation** → GSAP inside `$effect` / `onMount`, killed on teardown.
- **Ship to a TV** → `just deploy <tv-ip>` (TV in developer mode, `TIZEN_PROFILE` set to your signing profile).

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `typecheck` + `test`

Recipe reference:

- `just install` — `bun install`
- `just dev` — Vite dev server, arrow keys stand in for the remote (agent must not run this)
- `just build` — static build into `build/`
- `just preview` — preview the production build
- `just sync` — regenerate `.svelte-kit/` types
- `just wgt` — package `build/` into `dist/*.wgt` (Tizen Studio CLI)
- `just deploy <ip>` — `sdb connect` + install + run on the TV
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
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (`src/lib/<feature>/`, `src/routes/<section>/`) following the `claude-md-tree` skill's context-packet pattern.
