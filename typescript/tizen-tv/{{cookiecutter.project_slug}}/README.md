# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

A SvelteKit app packaged as a Samsung TV (Tizen {{ cookiecutter.tizen_required_version }}+) web app.

## Requirements

- [Bun](https://bun.sh/)
- [Tizen Studio CLI](https://developer.tizen.org/development/tizen-studio/download) (`tizen`, `sdb` on `PATH`) — only for packaging and deploying
- A signing certificate profile (`tizen certificate` / `tizen security-profiles`), referenced via `TIZEN_PROFILE`

## Getting Started

```bash
bun install
bun run dev     # http://localhost:{{ cookiecutter.port }} — arrow keys act as the remote
```

## Ship to a TV

1. Enable Developer Mode on the TV (Apps → `12345` → on, enter your dev machine's IP).
2. `export TIZEN_PROFILE=<your-signing-profile>`
3. `just deploy <tv-ip>` — builds, packages a `.wgt`, connects over `sdb`, installs and launches.

`just wgt` stops after packaging if you want to install by hand.

## Common Commands

| Command | Description |
|---------|-------------|
| `bun install` | Install dependencies |
| `bun run dev` | Start Vite dev server |
| `bun run build` | Static build into `build/` |
| `bun run check` | Type-check with svelte-check |
| `bun run test` | Run tests |
| `bun run lint` | Lint with Biome |
| `just wgt` | Package `build/` into `dist/*.wgt` |
| `just deploy <ip>` | Install and run on a TV |

## Project Structure

```
src/
  app.html                # HTML shell
  routes/+layout.ts       # ssr = false, prerender = true
  routes/+layout.svelte   # 1920x1080 shell, remote handler
  routes/+page.svelte     # home screen
  lib/remote.ts           # remote key codes + focus movement
  lib/spatial.ts          # directional-focus geometry
static/
  config.xml              # Tizen widget manifest
```

## Notes

- The app id in `static/config.xml` is `{{ cookiecutter.tizen_package_id }}.{{ cookiecutter.project_slug.replace('-', ' ').title().replace(' ', '') }}` — the package part must match your certificate.
- No SSR and no server routes: a `.wgt` is static files on the TV's filesystem.
- `window.tizen` only exists on-device; the code optional-chains it so the browser preview works.
