# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [2.6.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [2.5.2] - 2026-08-16
- agent.md: defer lint-fix to after feature ships, same as loc-fix

## [2.5.1] - 2026-08-16
- agent.md: defer LOC split to after feature ships, while user tests

## [2.5.0] - 2026-08-05
- loc-fix: public methods extract behind delegating stubs when the facade stays too big
- loc-fix: import.meta blocks pin to the barrel instead of refusing the file
- loc-fix: adjacent groups fuse when parts would exceed dir.max_files
- loc-fix: relative imports copied into subdirectory parts are repointed

## [2.4.0] - 2026-08-05
- loc-fix: member-level splits for giant classes (self-taking free functions + facade) and annotated data arrays (spread reassembly)

## [2.3.1] - 2026-08-05
- split_oversize: skip regex literals when tracking brace depth; keep overload sets and merged declarations together

## [2.3.0] - 2026-08-05
- add 'just loc-fix' + .claude/scripts/split_oversize.py: propose (and optionally apply) a reference-graph split for files over loc.error, dir-check aware, barrel keeps the public surface unchanged
- add .claude/SPLITTING.md doctrine

## [2.2.1] - 2026-07-31
- bump @biomejs/biome to ^2.5.0 and migrate biome.json to the v2 schema
- bump vitest to ^4.1, @types/node to ^26, typescript floor to ^5.9

## [2.2.0] - 2026-07-30
- add starter vitest test
- biome ignore for json config files

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
