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
locales/
├── en.default.json · nl.json                 # storefront strings (t filter); en is base and fallback
└── en.default.schema.json · nl.schema.json   # theme editor strings (t: keys in schemas)
assets/                 # CSS / JS / images, served via the asset_url filter
```

The render path is: **request → Shopify picks `templates/<type>.json` → renders the
listed sections in order → wraps them in `layout/theme.liquid`.** Markup belongs in
sections, not templates.

## Invariants

- **Online Store 2.0**: `templates/*.json` only *compose* sections — they hold no markup. Put markup in `sections/`.
- A **section** is the unit of merchant configuration. Each ships a `{% raw %}{% schema %}{% endraw %}` with `settings`, optional `blocks`, and a `presets` entry so it can be added in the theme editor.
- Reuse partials with `{% raw %}{% render 'name' %}{% endraw %}` (isolated scope). Do **not** use `{% raw %}{% include %}{% endraw %}` — it is deprecated.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English. Storefront copy goes through the `t` filter (`locales/*.json`), schema text (`name`, `label`, `info`, text `default`) through `t:` keys (`locales/*.schema.json`), and dates through `date: format: 'month_day_year'` (`date_formats`).
- Reference assets with the `asset_url` filter — never hard-code `/assets/...` paths.
- Liquid objects and filters are Shopify-provided. Don't invent objects/filters; check the docs.
- **Theme Check is the source of truth for lint** — `just lint` must be clean.
- Keep section files focused; split shared markup into `snippets/`.

## Common change patterns

- **Add a section** → create `sections/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`, then reference `"type": "<name>"` in the relevant `templates/<type>.json`.
- **Add a reusable partial** → `snippets/<name>.liquid`; call it with `{% raw %}{% render '<name>', arg: value %}{% endraw %}`.
- **Add a theme block** → `blocks/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`; allow it from a section's schema `blocks`.
- **Add a global setting** → edit `config/settings_schema.json`; read it in Liquid as `{% raw %}{{ settings.<id> }}{% endraw %}`.
- **Add or change text** → edit `locales/en.default.json` and `locales/nl.json` (schema text: the `*.schema.json` pair), call `{% raw %}{{ 'group.key' | t }}{% endraw %}` (schema: `"t:group.key"`), run `just i18n-check`.
- **Add a language** → add `locales/<code>.json` and `locales/<code>.schema.json` (no registration in code; publish the language in Shopify admin), run `just i18n-check`.
- **Add an asset** → drop the file in `assets/`, reference via `{% raw %}{{ 'file.css' | asset_url | stylesheet_tag }}{% endraw %}`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint`

Recipe reference:

- `just i18n-check` — every language file has the base's keys and placeholders
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
