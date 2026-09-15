# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [3.2.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [3.1.0] - 2026-05-25
- claude-tree recipe now delegates to the global atlas CLI (atlas tree)

## [3.0.0] - 2026-05-25
- remove bundled claude_tree.py; claude-tree recipe now launches the project-atlas viewer

## [2.6.1] - 2026-05-25
- claude-tree viewer: render graph at natural 1:1 size (fix nodes collapsing to ~33px under fit-to-width), fixed-width node cards, Space Grotesk + IBM Plex Mono type, refined theme

## [2.6.0] - 2026-05-24
- redesign claude-tree viewer: side-by-side compact graph + single lazy editor, richer node previews (path/title/blurb/section outline/line count)

## [2.5.2] - 2026-05-24
- slim [template-update] hook to delegate to the /update-scaffold skill (keeps just update-scaffold fallback)

## [2.5.1] - 2026-05-24
- fix: update_scaffold no longer overwrites CLAUDE.md/Justfile/.gitignore/seed files by default (writes .upstream sidecars); --force opt-in for old behavior; check_template_update prompt updated to match

## [2.5.0] - 2026-05-24
- feat: claude_tree.py interactive editor (server mode default; --static keeps old HTML); save/revert with CLAUDE.md.history.jsonl sidecar; node previews wired to editors

## [2.4.1] - 2026-05-24
- fix: update-scaffold falls back to .template-meta.json path when $COOKIECUTTER_TEMPLATES is unset

## [2.4.0] - 2026-05-24
- add claude_tree.py (.claude/scripts) and 'just claude-tree' recipe

## [2.3.0] - 2026-05-21
- restructure CLAUDE.md as context packet (claude-md-tree)

## [2.2.0] - 2026-04-27
- add _diag.py phone-home logger; check_template_update + check_library_freshness emit JSONL diagnostics to upstream repo for fleet-wide review

## [2.1.0] - 2026-04-27
- add: SessionStart library-freshness hook + snooze script

## [2.0.0] - 2026-04-25
- deployment target raised to iOS 26, swift-tools-version 6.2

## [1.1.1] - 2026-04-25
- module_name default now PascalCases input — works with lowercase project_name

## [1.1.0] - 2026-04-20
- post_gen hook writes .atlas sidecar (description/type/framework/archived)
- update_scaffold.py shallow-merges .atlas on --apply; local values preserved

## [1.0.2] - 2026-04-20
- First tracked changelog entry for this template. Prior bumps predate changelog tracking.
