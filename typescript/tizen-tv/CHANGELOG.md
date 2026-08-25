# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.0.1] - 2026-08-25
- add @types/node so svelte-check can resolve vite/kit node types
- biome ignores generated .svelte-kit/, build/ and dist/ — lint failed once those existed

## [1.0.0] - 2026-08-25
- initial template: SvelteKit on Samsung Tizen TV — adapter-static + relative paths, `static/config.xml` widget manifest, remote-control spatial focus (`$lib/spatial.ts` + `$lib/remote.ts`), `just wgt` / `just deploy <ip>` packaging via the Tizen CLI
- same stack as typescript/sveltekit: bun, Biome, stylelint, Vitest, GSAP
- biome.json override turns off noUnusedVariables for `*.svelte` (Biome can't see `$props()` bindings used in markup; svelte-check still catches real ones)
