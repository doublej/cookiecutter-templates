# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.2.0] - 2026-09-15
- add en+nl i18n: internal/i18n (embed), -lang + LANG detection, plural keys, just i18n-check active
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [1.1.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [1.0.1] - 2026-07-31
- go directive 1.24 -> 1.25 (1.24 out of support)

## [1.0.0] - 2026-05-27
- Initial Go CLI template: stdlib `flag` parsing, `go vet` + `gofmt` quality gates, Justfile task runner, Claude Code scaffold (CLAUDE.md/agent.md, update-check + library-freshness hooks, diagnostics).
