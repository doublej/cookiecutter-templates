# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

A Shopify [Online Store 2.0](https://shopify.dev/docs/storefronts/themes) theme
built with Liquid, JSON templates, and sections.

## Prerequisites

- [Shopify CLI](https://shopify.dev/docs/api/shopify-cli) — `npm i -g @shopify/cli`
- [`just`](https://github.com/casey/just) — task runner
- A Shopify store (or development store) you can connect to

## Getting started

```bash
# Connect and run a live-reloading dev server against your store
shopify theme dev --store your-store.myshopify.com

# or via just
just dev
```

The first run prompts you to authenticate and pick a store.

## Layout

```
layout/      theme.liquid (HTML shell), password.liquid
templates/   JSON page templates + customers/ account pages
sections/    configurable, schema-driven blocks
snippets/    reusable Liquid partials
blocks/      theme blocks
config/      settings_schema.json + settings_data.json
locales/     translations: en.default.json (base) + nl.json, and their .schema.json pairs
assets/      css / js / images
```

## Workflow

```bash
just lint         # Theme Check
just lint-fix     # Theme Check --auto-correct
just check        # lint + Justfile/loc/dir checks
just share        # shareable preview link
just push         # deploy to the connected store
```

See [CLAUDE.md](CLAUDE.md) and [agent.md](agent.md) for the mental model,
conventions, and the agent verify loop.
