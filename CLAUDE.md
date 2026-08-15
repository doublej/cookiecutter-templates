# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A unified cookiecutter template collection for scaffolding projects across Python, TypeScript, Rust, Swift, Go, and Shopify (Liquid themes), with validation tooling to keep templates consistent.

## Commands

```bash
# Validate sync across template families (identical files, Justfile recipes)
uv run tools/sync_check.py

# CI-only: also fail when a changed template did not bump its _version
uv run tools/sync_check.py --enforce-bumps --bump-base origin/main

# Render all templates with multiple context variants and run smoke tests
uv run tools/render_test.py

# Offline unit test for the SessionStart update-check hook
uv run tools/test_update_check.py

# Aggregate phone-home diagnostics from deployed-template hooks
uv run tools/review_diagnostics.py [--since 7d] [--errors-only]

# Bump a template version (strict MAJOR.MINOR.PATCH only)
uv run tools/bump_version.py python/fastapi {major|minor|patch}

# Generate a single project
cookiecutter python/fastapi
cookiecutter typescript/node-api
cookiecutter rust/cli
cookiecutter go/api
cookiecutter swift/macos
cookiecutter shopify/theme
```

Always run `sync_check.py` then `render_test.py` after changes. CI runs both on push/PR to main.

## Template versioning

Every `cookiecutter.json` carries a private `_version` field (not prompted). Every render writes it into the project's `.template-meta.json` as `template_version`. Every generated project ships a `.claude/` SessionStart hook that compares local version against the upstream template on every Claude Code session and prints `[template-update] <tmpl> <local> -> <upstream> available ...` when upstream has advanced — prompting the agent to ask the user whether to run `update_scaffold.py`.

**Semver semantics (strict `MAJOR.MINOR.PATCH`, no pre-release suffixes):**

- `patch` — file content tweak, dep bump, lint fix
- `minor` — new file, new Justfile recipe, added feature
- `major` — breaking scaffold change (renamed path, removed recipe, cookiecutter key rename)

**Bump workflow:** after editing a template, run `uv run tools/bump_version.py <template> {major|minor|patch}`. CI runs `sync_check.py --enforce-bumps` on every PR and fails if a template has file changes but no `_version` bump.

**Opt-out** (per generated project): set env `NO_TEMPLATE_UPDATE_CHECK=1` or `touch .claude/no-template-update-check`.

**v1 limitations:** the check resolves upstream via the absolute `template_source.path` captured at render time. If the cookiecutter-templates repo is moved, the check silently no-ops.

## Architecture

### Template families

Templates are grouped into families (python, typescript, rust, swift, go, shopify). Within a family, certain files and Justfile recipes **must stay identical** — enforced by `tools/sync_manifest.json` + `tools/sync_check.py`.

| Family | Templates | Shared identical files | Shared Justfile recipes |
|--------|-----------|----------------------|------------------------|
| python | cli, fastapi, flask | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json` | default, install, lint, lint-fix, format, format-check, typecheck, test, loc-check, dir-check, check, clean, claude-tree |
| typescript | node-api, node-cli, bun-package, node-lib, node-worker, react, sveltekit, nextjs | `hooks/pre_gen_project.py` | default, install, lint, lint-fix, test, loc-check, dir-check, check, build, clean, claude-tree |
| swift | ios, macos | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `.swiftlint.yml` | default, install, xcode, lint, lint-fix, test, loc-check, dir-check, check, build, build-release, clean, claude-tree |
| rust | cli | `hooks/pre_gen_project.py`, `.gitignore` | default, lint, fmt, fmt-check, check, test, loc-check, dir-check, build-release, reinstall, claude-tree |
| go | cli, api | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json` | default, install, lint, fmt, fmt-check, test, loc-check, dir-check, check, build, build-release, clean, claude-tree |
| shopify | theme | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `.theme-check.yml` | default, dev, share, lint, lint-fix, loc-check, dir-check, check, pull, push, claude-tree |

Cross-family, every generated `.claude/scripts/` ships identical helper scripts: `_diag.py` (phone-home), `check_template_update.py`, `check_library_freshness.py`, and `snooze_library_check.py`. The `claude-tree` recipe ships no script — it deep-links into the project-atlas viewer (`atlas-api` on :47891) by `pwd`, opening the ancestor + descendant `CLAUDE.md` tree at `/claude-tree?root=$(pwd)`.

**Exceptions** are declared in `sync_manifest.json` under `justfile_exceptions` (e.g. SvelteKit skips `typecheck`/`clean`).

**`typescript/node-lib` carries a deliberately detached PoC** — `.claude/scripts/split_oversize.py`, `.claude/SPLITTING.md` and the `just loc-fix` recipe (the LOC autofix experiment, covered by `tools/test_loc_split.py`). It is intentionally **absent from `cross_family.identical_files` and `justfile_shared_recipes`**: `sync_check.py` only compares paths and recipe names the manifest lists, so an extra file and an extra recipe are invisible to it. Do not "fix" the asymmetry by copying it to the other 18 templates — rollout waits until the PoC has proven itself on real oversized files. Registering it in the manifest is what makes the rollout mandatory, so that edit is the rollout decision.

### Template anatomy

Each template follows this structure:
```
<language>/<template>/
├── cookiecutter.json              # Variables and options
├── hooks/
│   ├── pre_gen_project.py         # Validates project_name + project_slug
│   └── post_gen_project.py        # Writes .template-meta.json, MCP setup, prints instructions
└── {{cookiecutter.project_slug}}/
    ├── CLAUDE.md, agent.md, Justfile, README.md, .gitignore, .quality.json
    └── src/ (or language-specific layout)
```

### Tools

| Script | Purpose |
|--------|---------|
| `tools/sync_check.py` | SHA256 comparison of identical files; recipe-level Justfile comparison |
| `tools/render_test.py` | Renders ~50 template variants (defined in `TEMPLATES` dict); runs language-specific smoke tests (compileall, bun install+lint+build+test, cargo build, swift build) |
| `tools/inject_tracking.py` | Replaces the tracking placeholder with a Umami `<script>` tag, indentation-preserving — handles both `.html` (`<!-- TRACKING_PLACEHOLDER -->`) and `.tsx` (`{/* TRACKING_PLACEHOLDER */}`) |
| `tools/umami_register.py` | Creates a website in Umami via `POST /api/websites` and prints the new website id (`--json` adds the resolved URL). Credentials resolve from env, falling back to the onenv `umami` namespace; auth is `UMAMI_API_KEY` (x-umami-api-key, Umami Cloud) or `UMAMI_USERNAME`/`UMAMI_PASSWORD` (login → bearer, self-hosted) |

**Tracking flow (sveltekit/react/nextjs).** `include_tracking` is the up-front gate — and the only question ever asked. When `n`, the post-gen hook strips the placeholder. When `y`, the hook automatically registers `<slug>` in Umami (`umami_register.py --json`) and injects the tracking script (`inject_tracking.py`) — no prompts. Credentials resolve inside `umami_register.py`: env vars first, then the onenv `umami` namespace (`UMAMI_URL` + `UMAMI_USERNAME`/`UMAMI_PASSWORD` for self-hosted login→bearer, or `UMAMI_API_KEY` for Umami Cloud). Test renders (`render_test.py` sets `TEMPLATE_RENDER_TEST=1`) skip the network and leave the placeholder. The whole flow is best-effort and never fails generation.

## Maintenance

**Any maintenance session in this repo MUST include a dependency-freshness pass.** Before other maintenance work, audit every template manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Package.swift`, `*.gradle.kts`) against the live registries (npm, PyPI, crates.io, Go proxy, Google Maven) and upgrade — don't just report:

- Bump pins/floors to current stable; apply any config/source migrations the new majors require (e.g. biome config schema, eslint flat config, vite plugin matrix).
- Security advisories and EOL toolchains (EOL Go directive, EOL eslint/vite lines) are never left in place.
- Deliberate holds are allowed (e.g. TypeScript 5.x floor over the 7.x native line, AGP 8.x while render_test has no gradle smoke test) but must be listed in the session's report with the reason.
- Then run `sync_check.py` + `render_test.py`, and `bump_version.py <template> patch` (minor if files were added) for every changed template.

## Conventions

- **Project slug**: kebab-case `[a-z][a-z0-9-]*[a-z0-9]`, min 2 chars, validated in pre-gen hooks
- **Hooks are safe**: no `git init`, no dependency installs, no commits. `atlas new` does the git bootstrap after cookiecutter returns (`main` + scaffold commit + `develop`), so the branch flow stays in one place instead of in every template's post-gen hook. No `flow`/branch question belongs in `cookiecutter.json`

- **MCP options**: every template supports `mcp_servers` (none/minimal/standard/interactive) and `mcp_scope` (project/local) in cookiecutter.json
- **When editing a shared file** (identified in sync_manifest.json), apply the same change to all templates in the family
- **When editing a shared Justfile recipe**, apply the same change to all Justfiles in the family (respecting exceptions)
- **render_test.py variants**: when adding a new template option, add corresponding variant entries to the `TEMPLATES` dict in render_test.py
- **Tooling**: Python uses uv/ruff/mypy/pytest; TypeScript uses bun/Biome/Vitest; Rust uses cargo/clippy; Swift uses SPM

## Diagnostic logging (deployed templates)

Any hook or script that ships inside a generated project's `.claude/` (e.g. `check_template_update.py`, future SessionStart/PostToolUse hooks, post-render scripts) **must emit a diagnostic log entry back to this cookiecutter-templates repo** so we can review aggregate health on a scheduled basis.

**Why:** these scripts run on every Claude Code session in every spawned project, swallow exceptions (so they never block sessions), and are otherwise invisible. Without phone-home logging we cannot tell if a hook is silently broken across the fleet, or detect regressions introduced by a template bump.

**Convention:**

- Resolve the log dir via `template_source.path` in the project's `.template-meta.json` → write to `<repo>/_diagnostics/<template>/<YYYY-MM>.jsonl`.
- One JSON line per invocation. Required keys: `ts` (ISO8601 UTC), `template`, `template_version`, `project_path`, `hook` (script identifier), `status` (`ok` | `noop` | `error`), `duration_ms`. Optional: `error` (truncated message + type), `meta` (script-specific payload).
- Best-effort: logging failure must never raise. Wrap in try/except and exit 0.
- Diag-specific opt-out (separate from per-hook opt-outs): `NO_TEMPLATE_DIAG=1` env or `.claude/no-template-diag` sentinel.
- `_diagnostics/` is gitignored at the repo root; reviewed via a tool (see below) and pruned manually.
