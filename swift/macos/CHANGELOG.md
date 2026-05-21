# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [2.3.0] - 2026-05-21
- restructure CLAUDE.md as context packet (claude-md-tree)

## [2.2.0] - 2026-04-27
- add _diag.py phone-home logger; check_template_update + check_library_freshness emit JSONL diagnostics to upstream repo for fleet-wide review

## [2.1.0] - 2026-04-27
- add: SessionStart library-freshness hook + snooze script

## [2.0.0] - 2026-04-25
- deployment target raised to macOS 26 (Tahoe), swift-tools-version 6.2

## [1.2.1] - 2026-04-25
- module_name default now PascalCases input — works with lowercase project_name

## [1.2.0] - 2026-04-22
- rename 'run' to 'run-app' with retro-compat alias

## [1.1.0] - 2026-04-20
- post_gen hook writes .atlas sidecar (description/type/framework/archived)
- update_scaffold.py shallow-merges .atlas on --apply; local values preserved

## [1.0.2] - 2026-04-20
- First tracked changelog entry for this template. Prior bumps predate changelog tracking.
