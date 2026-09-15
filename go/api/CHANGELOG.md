# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.1.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [1.0.1] - 2026-07-31
- go directive 1.24 -> 1.25 (1.24 out of support)

## [1.0.0] - 2026-05-27
- Initial Go HTTP API template: net/http `ServeMux` pattern routing, `/healthz` endpoint, `slog` logging, graceful shutdown on SIGINT/SIGTERM, `go vet` + `gofmt` quality gates, Justfile task runner, Claude Code scaffold.
