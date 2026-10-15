# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.2.2] - 2026-10-15
- post-gen hook: quotes in description/author no longer crash generation; relative template paths record the real repo
- account order table headers use plain Order/Date keys instead of 'Placed on '

## [1.2.1] - 2026-10-15
- update hook describes the 3-way merge instead of .upstream sidecars

## [1.2.0] - 2026-09-15
- add en+nl i18n: locales/nl.json + nl.schema.json, date_formats, t: schema defaults, just i18n-check active
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [1.1.0] - 2026-08-16
- add verify-runner + deploy-runner subagents, .claude/tickets/ convention

## [1.0.0] - 2026-06-23
- Initial Shopify Online Store 2.0 theme template (Liquid storefront): JSON templates, sections + theme blocks, settings schema, locales, Theme Check, Shopify CLI Justfile, .claude/ hooks.
