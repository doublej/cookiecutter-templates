# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Shopify Online Store 2.0 theme (Liquid)
- Shopify CLI (`shopify theme dev` / `check` / `push`)
- Theme Check (linting)
- `just` task runner

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint)
- `just dev` — start the local dev server (long-lived; agent must not run this)
- `just lint` / `just lint-fix` — Theme Check / `--auto-correct`
- `just share` — generate a shareable preview link
- `just pull` — pull theme files from a store (ask first)
- `just push` — deploy theme files to a store (ask first)
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
layout/         # theme.liquid (HTML shell), password.liquid
templates/      # JSON page templates + customers/ account pages
sections/       # configurable blocks with {% raw %}{% schema %}{% endraw %}
snippets/       # reusable Liquid partials ({% raw %}{% render %}{% endraw %})
blocks/         # theme blocks
config/         # settings_schema.json, settings_data.json
locales/        # translation files (*.default.json is active)
assets/         # css / js / images
.theme-check.yml
Justfile
```

## Conventions

- Online Store 2.0: templates are JSON composing sections; markup lives in `sections/`.
- Every section has a `{% raw %}{% schema %}{% endraw %}` with `settings`, optional `blocks`, and a `presets` entry.
- Reuse with `{% raw %}{% render %}{% endraw %}` (not the deprecated `{% raw %}{% include %}{% endraw %}`).
- All copy goes through the `t` filter, backed by `locales/*.json`.
- Reference assets with the `asset_url` filter, not hard-coded paths.
- Don't invent Liquid objects/filters — verify against Shopify docs.
- Keep sections focused; extract shared markup into snippets.

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + lint (Theme Check).

Step-by-step alternative:

1. `just lint-fix`
2. `just lint`

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- `shopify theme check --auto-correct` (a.k.a. `just lint-fix`) — fix auto-correctable Theme Check offenses.

### Deploying

Once the user has explicitly approved a push, hand it to the `deploy-runner` subagent
(`just push`) rather than blocking your own turn on it. It files a ticket in
`.claude/tickets/` if the push fails; it never retries and never touches theme config to
work around a failure. The explicit-approval requirement below is unchanged — only invoke
it after the user has said to deploy.

### Common Tasks

- Add a section: create `sections/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`, then add `"type": "<name>"` to the page's `templates/<type>.json`.
- Add a snippet: create `snippets/<name>.liquid`; call it with `{% raw %}{% render '<name>' %}{% endraw %}`.
- Add a theme block: create `blocks/<name>.liquid` with a `{% raw %}{% schema %}{% endraw %}`.
- Add a setting: edit `config/settings_schema.json`; read via `{% raw %}{{ settings.<id> }}{% endraw %}`.
- Add a string: add the key to `locales/en.default.json`; render with `{% raw %}{{ 'group.key' | t }}{% endraw %}`.

### Testing

- Themes have no unit tests. Correctness = a clean Theme Check (`just lint`) plus a manual look via `just dev` / `just share`.
- Validate JSON templates and locales parse (Theme Check covers this).

### Boundaries

- Do not run `just dev` — never start the long-lived dev server.
- Do not run `just push` / `just pull` — never deploy to or overwrite from a store without explicit approval.
- Do not edit `config/settings_data.json` by hand to fake content; it holds merchant data.
- Use `{% raw %}{% render %}{% endraw %}`, never `{% raw %}{% include %}{% endraw %}`.
