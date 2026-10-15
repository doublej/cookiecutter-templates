# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.2.2] - 2026-10-15
- post-gen hook: quotes in description/author no longer crash generation; relative template paths record the real repo
- go 1.27 (1.25 is EOL)
- http.Server gets read/write/idle timeouts (Slowloris)
- package comment reads correctly

## [1.2.1] - 2026-10-15
- update hook describes the 3-way merge instead of .upstream sidecars

## [1.2.0] - 2026-09-15
- add en+nl i18n: internal/i18n (embed), Accept-Language middleware + Content-Language, just i18n-check active
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [1.1.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [1.0.1] - 2026-07-31
- go directive 1.24 -> 1.25 (1.24 out of support)

## [1.0.0] - 2026-05-27
- Initial Go HTTP API template: net/http `ServeMux` pattern routing, `/healthz` endpoint, `slog` logging, graceful shutdown on SIGINT/SIGTERM, `go vet` + `gofmt` quality gates, Justfile task runner, Claude Code scaffold.
