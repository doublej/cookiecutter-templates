# Changelog

Per-template changelog. The SessionStart update-check hook reads this file
from the upstream template and surfaces entries between the project's
pinned version and the upstream version.

Strict [semver]: `MAJOR.MINOR.PATCH`, no pre-release suffixes.

## [1.3.0] - 2026-09-15
- ship dormant check_i18n.py; i18n stays off because the Raycast Store requires US English
- update-check hook tells agents to apply scaffold updates safely and ask only about conflicts

## [1.2.0] - 2026-08-16
- add verify-runner subagent + .claude/tickets/ convention; agent.md delegates checks to it instead of blocking on new-feature work

## [1.1.0] - 2026-07-31
- migrate ESLint to flat config: replace .eslintrc.json with eslint.config.mjs
- bump eslint to ^10, @raycast/eslint-config and @raycast/utils to ^2.2
- bump @raycast/api floor to ^1.104, @types/node to ^26, typescript floor to ^5.9

## [1.0.0] - 2026-07-23
- initial template: minimal Raycast extension scaffold (hello view command, prefs lib, ray toolchain)
