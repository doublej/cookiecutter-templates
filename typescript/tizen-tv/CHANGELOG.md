# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.1.2] - 2026-10-15
- post-gen hook: quotes in description/author no longer crash generation; relative template paths record the real repo
- dep floors: biome 2.5.15 (schema too), vitest 4.1.11 (security)
- @sveltejs/kit 2.70.3 and svelte 5.57.2 (security)
- String.prototype.replaceAll polyfill so Tizen 6.0 (Chrome 76) mounts
- biome ignore globs without trailing /**

## [1.1.1] - 2026-10-15
- update hook describes the 3-way merge instead of .upstream sidecars

## [1.1.0] - 2026-09-15
- add en+nl i18n: Paraglide JS 2 following the TV system language, localized tiles + config.xml name, just i18n-check active
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [1.0.1] - 2026-08-25
- add @types/node so svelte-check can resolve vite/kit node types
- biome ignores generated .svelte-kit/, build/ and dist/ — lint failed once those existed

## [1.0.0] - 2026-08-25
- initial template: SvelteKit on Samsung Tizen TV — adapter-static + relative paths, `static/config.xml` widget manifest, remote-control spatial focus (`$lib/spatial.ts` + `$lib/remote.ts`), `just wgt` / `just deploy <ip>` packaging via the Tizen CLI
- same stack as typescript/sveltekit: bun, Biome, stylelint, Vitest, GSAP
- biome.json override turns off noUnusedVariables for `*.svelte` (Biome can't see `$props()` bindings used in markup; svelte-check still catches real ones)
