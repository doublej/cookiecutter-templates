# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A Shopify **Online Store 2.0** theme (Liquid storefront). Pages are composed from
JSON templates that list **sections**; sections hold the markup and are
merchant-configurable via a `{% raw %}{% schema %}{% endraw %}` block. The Shopify CLI
owns local dev (`shopify theme dev`), linting (Theme Check), and deploy
(`shopify theme push`). No build step, no bundler.

## Mental model

```
layout/
├── theme.liquid        # global HTML shell — <head>, content_for_header, content_for_layout
└── password.liquid     # storefront password-page shell
templates/              # one entry per page type; JSON lists which sections render
├── index.json          # home
├── product.json        # product page
├── collection.json     # collection listing
├── page.json · cart.json · 404.json · search.json · blog.json · article.json …
└── customers/          # account, login, register, order, addresses …
sections/               # reusable, configurable blocks — each has a {% raw %}{% schema %}{% endraw %}
snippets/               # small Liquid partials, pulled in via {% raw %}{% render %}{% endraw %}
blocks/                 # theme blocks (nestable, app-block compatible)
config/
├── settings_schema.json   # global theme settings (Theme editor → Settings)
└── settings_data.json     # current values of those settings
locales/                # translations; <code>.default.json is the active storefront locale
assets/                 # CSS / JS / images, served via the asset_url filter
```

The render path is: **request → Shopify picks `templates/<type>.json` → renders the
listed sections in order → wraps them in `layout/theme.liquid`.** Markup belongs in
sections, not templates.

## Invariants

- **Online Store 2.0**: `templates/*.json` only *compose* sections — they hold no markup. Put markup in `sections/`.
- A **section** is the unit of merchant configuration. Each ships a `{% raw %}{% schema %}{% endraw %}` with `settings`, optional `blocks`, and a `presets` entry so it can be added in the theme editor.
- Reuse partials with `{% raw %}{% render 'name' %}{% endraw %}` (isolated scope). Do **not** use `{% raw %}{% include %}{% endraw %}` — it is deprecated.
- Every user-facing string goes through the `t` filter and lives in `locales/*.json` — no hard-coded copy.
- Reference assets with the `asset_url` filter — never hard-code `/assets/...` paths.
- Liquid objects and filters are Shopify-provided. Don't invent objects/filters; check the docs.
- **Theme Check is the source of truth for lint** — `just lint` must be clean.
- Keep section files focused; split shared markup into `snippets/`.

## Common change patterns

- **Add a section** → create `sections/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`, then reference `"type": "<name>"` in the relevant `templates/<type>.json`.
- **Add a reusable partial** → `snippets/<name>.liquid`; call it with `{% raw %}{% render '<name>', arg: value %}{% endraw %}`.
- **Add a theme block** → `blocks/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`; allow it from a section's schema `blocks`.
- **Add a global setting** → edit `config/settings_schema.json`; read it in Liquid as `{% raw %}{{ settings.<id> }}{% endraw %}`.
- **Add a string** → add the key to `locales/en.default.json`, render with `{% raw %}{{ 'group.key' | t }}{% endraw %}`.
- **Add an asset** → drop the file in `assets/`, reference via `{% raw %}{{ 'file.css' | asset_url | stylesheet_tag }}{% endraw %}`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint`

Recipe reference:

- `just dev` — `shopify theme dev` (agent must not run this; it's a long-lived server)
- `just lint` / `just lint-fix` — Theme Check / `--auto-correct`
- `just share` — `shopify theme share` (preview link)
- `just pull` — `shopify theme pull` (agent must not run this without asking)
- `just push` — `shopify theme push` (deploy; agent must not run this)
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- `.theme-check.yml` — Theme Check config
- As this theme grows, add nested `CLAUDE.md` files in high-value subfolders (`sections/`, `snippets/`, a design-system folder) following the `claude-md-tree` skill's context-packet pattern.
