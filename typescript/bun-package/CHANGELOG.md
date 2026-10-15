# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [2.3.2] - 2026-10-15
- post-gen hook: quotes in description/author no longer crash generation; relative template paths record the real repo
- dep floors: biome 2.5.15 (schema too), vitest 4.1.11 (security)
- @types/bun 1.4.3

## [2.3.1] - 2026-10-15
- update hook describes the 3-way merge instead of .upstream sidecars

## [2.3.0] - 2026-09-15
- ship dormant check_i18n.py + i18n-check recipe (opt in with an i18n block in .quality.json)
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [2.2.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [2.1.2] - 2026-07-31
- bump @biomejs/biome to ^2.5.0 and migrate biome.json to the v2 schema
- bump @types/node to ^26, typescript floor to ^5.9

## [2.1.1] - 2026-07-30
- biome ignore for json config files
- add @types/bun
- explicit .js import in test

## [2.1.0] - 2026-05-25
- claude-tree recipe now delegates to the global atlas CLI (atlas tree)

## [2.0.0] - 2026-05-25
- remove bundled claude_tree.py; claude-tree recipe now launches the project-atlas viewer

## [1.7.1] - 2026-05-25
- claude-tree viewer: render graph at natural 1:1 size (fix nodes collapsing to ~33px under fit-to-width), fixed-width node cards, Space Grotesk + IBM Plex Mono type, refined theme

## [1.7.0] - 2026-05-24
- redesign claude-tree viewer: side-by-side compact graph + single lazy editor, richer node previews (path/title/blurb/section outline/line count)

## [1.6.2] - 2026-05-24
- slim [template-update] hook to delegate to the /update-scaffold skill (keeps just update-scaffold fallback)

## [1.6.1] - 2026-05-24
- fix: update_scaffold no longer overwrites CLAUDE.md/Justfile/.gitignore/seed files by default (writes .upstream sidecars); --force opt-in for old behavior; check_template_update prompt updated to match

## [1.6.0] - 2026-05-24
- feat: claude_tree.py interactive editor (server mode default; --static keeps old HTML); save/revert with CLAUDE.md.history.jsonl sidecar; node previews wired to editors

## [1.5.1] - 2026-05-24
- fix: update-scaffold falls back to .template-meta.json path when $COOKIECUTTER_TEMPLATES is unset

## [1.5.0] - 2026-05-24
- add claude_tree.py (.claude/scripts) and 'just claude-tree' recipe

## [1.4.0] - 2026-05-21
- restructure CLAUDE.md as context packet (claude-md-tree)

## [1.3.0] - 2026-04-27
- add _diag.py phone-home logger; check_template_update + check_library_freshness emit JSONL diagnostics to upstream repo for fleet-wide review

## [1.2.0] - 2026-04-27
- add: SessionStart library-freshness hook + snooze script

## [1.1.0] - 2026-04-20
- post_gen hook writes .atlas sidecar (description/type/framework/archived)
- update_scaffold.py shallow-merges .atlas on --apply; local values preserved

## [1.0.2] - 2026-04-20
- First tracked changelog entry for this template. Prior bumps predate changelog tracking.
