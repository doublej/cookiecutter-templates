# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.0.0] - 2026-05-27
- Initial Go HTTP API template: net/http `ServeMux` pattern routing, `/healthz` endpoint, `slog` logging, graceful shutdown on SIGINT/SIGTERM, `go vet` + `gofmt` quality gates, Justfile task runner, Claude Code scaffold.
