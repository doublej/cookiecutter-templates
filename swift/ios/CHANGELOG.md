# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

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
