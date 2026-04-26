# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.


## [1.4.0] - 2026-04-27
- add _diag.py phone-home logger; check_template_update + check_library_freshness emit JSONL diagnostics to upstream repo for fleet-wide review

## [1.3.0] - 2026-04-27
- add: SessionStart library-freshness hook + snooze script

## [1.2.0] - 2026-04-20
- post_gen hook writes .atlas sidecar (description/type/framework/archived)
- update_scaffold.py shallow-merges .atlas on --apply; local values preserved

## [1.1.3] - 2026-04-20
- add per-template CHANGELOG.md surfaced in update-check hook
- bump_version.py now requires --note

## [1.1.2] - 2026-04-20
- First tracked changelog entry for this template. Prior bumps predate changelog tracking.
