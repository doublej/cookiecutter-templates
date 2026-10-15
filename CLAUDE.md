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

# Update every generated project under ~/dev that is behind its released template: tooling + .atlas only,
# one path-scoped commit per project, never pushes. Report only without --apply.
python3 tools/update_projects.py [--root ~/dev] [--apply]

# Local test for the batch updater (needs cookiecutter + full git history, so not in CI)
python3 tools/test_update_projects.py

# Local test for the 3-way scaffold merge (same constraints)
python3 tools/test_update_scaffold.py

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

Every `cookiecutter.json` carries a private `_version` field (not prompted). Every render writes it into the project's `.template-meta.json` as `template_version`. Every generated project ships a `.claude/` SessionStart hook that compares local version against the upstream template on every Claude Code session and prints `[template-update] <tmpl> <local> -> <upstream> available ...` when upstream has advanced — prompting the agent to run the `/update-scaffold` skill, which applies without asking (tooling overwritten, `.atlas` merged, everything else 3-way merged via `git merge-file` against a render of the project's own `template_version`, so files the template did not change are untouched and local edits survive), resolves conflict markers itself and asks only when both sides are mutually exclusive. Without a merge base (retrofit, unversioned) seeds fall back to `.upstream` sidecars. `update_scaffold.py` treats an unchanged `_version` as up to date: template edits are not an update until a bump releases them. It renders the template from the commit that released its current `_version` (`git archive`), so commits after a bump and uncommitted edits never reach a project. `tools/update_projects.py` applies the safe part of every pending update across `~/dev` in one pass (tooling overwritten, `.atlas` merged, one path-scoped commit per project) and bumps `template_version` only when nothing else differs, so the hook keeps prompting `/update-scaffold` for seeds and new files.

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
| python | cli, fastapi, flask | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `src/<pkg>/i18n.py`, `tests/test_i18n.py` | default, install, lint, lint-fix, format, format-check, typecheck, test, loc-check, dir-check, i18n-check, check, clean, claude-tree |
| typescript | node-api, node-cli, bun-package, node-lib, node-worker, react, sveltekit, tizen-tv, nextjs | `hooks/pre_gen_project.py` | default, install, lint, lint-fix, test, loc-check, dir-check, i18n-check, check, build, clean, claude-tree |
| swift | ios, macos | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `.swiftlint.yml`, `<slug>/L10n.swift` | default, install, xcode, lint, lint-fix, test, loc-check, dir-check, i18n-check, check, build, build-release, clean, claude-tree |
| rust | cli | `hooks/pre_gen_project.py`, `.gitignore` | default, lint, fmt, fmt-check, check, test, loc-check, dir-check, i18n-check, build-release, reinstall, claude-tree |
| go | cli, api | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `internal/i18n/i18n.go`, `internal/i18n/i18n_test.go` | default, install, lint, fmt, fmt-check, test, loc-check, dir-check, i18n-check, check, build, build-release, clean, claude-tree |
| shopify | theme | `hooks/pre_gen_project.py`, `.gitignore`, `.quality.json`, `.theme-check.yml` | default, dev, share, lint, lint-fix, loc-check, dir-check, i18n-check, check, pull, push, claude-tree |

Cross-family, every generated `.claude/scripts/` ships identical helper scripts: `_diag.py` (phone-home), `check_template_update.py`, `check_library_freshness.py`, `snooze_library_check.py`, and `check_i18n.py` (the `just i18n-check` verifier; dormant until `.quality.json` has an `i18n` block). The `claude-tree` recipe ships no script — it deep-links into the project-atlas viewer (`atlas-api` on :47891) by `pwd`, opening the ancestor + descendant `CLAUDE.md` tree at `/claude-tree?root=$(pwd)`.

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
    ├── en + nl language files (path per stack, see "Multilingual runtimes")
    └── src/ (or language-specific layout)
```

### Multilingual runtimes

Each stack uses its native i18n mechanism; the contract and `just i18n-check` are the same everywhere (see Conventions).

| Template(s) | Runtime | Language files | `i18n.format` |
|-------------|---------|----------------|---------------|
| python/cli, fastapi, flask | zero-dep `src/<pkg>/i18n.py` (`importlib.resources` + json) | `src/<pkg>/locales/{en,nl}.json` | json |
| go/cli, api | zero-dep `internal/i18n` (`embed` + `encoding/json`) | `internal/i18n/locales/{en,nl}.json` | json |
| rust/cli | zero-dep `src/i18n.rs` (`include_str!` + serde_json) | `locales/{en,nl}.json` | json |
| typescript/node-api, node-cli | zero-dep `src/i18n.ts` (`Intl.PluralRules`) | `src/locales/{en,nl}.json` | json |
| typescript/sveltekit, tizen-tv, react | Paraglide JS 2, compiled (`prepare` script; plugin loaded from `node_modules`, never a CDN) | `messages/{en,nl}.json` + `project.inlang/settings.json` | json |
| typescript/nextjs | next-intl, `localePrefix: 'as-needed'`, locale via `next/root-params` | `messages/{en,nl}.json` | json |
| swift/ios, macos | Foundation `.strings` + `L10n.swift` (SPM executables have no Info.plist, so `Bundle.module` alone ignores the preferred language) | `<slug>/Resources/{en,nl}.lproj/Localizable.strings` | strings |
| android/quest-vr | Android resources | `app/src/main/res/values{,-nl}/strings.xml` | android |
| shopify/theme | Shopify locales (`t` filter, `t:` schema keys) | `locales/{en.default,nl}{,.schema}.json` | json + `base_file` |

### Tools

| Script | Purpose |
|--------|---------|
| `tools/sync_check.py` | SHA256 comparison of identical files; recipe-level Justfile comparison |
| `tools/render_test.py` | Renders ~50 template variants (defined in `TEMPLATES` dict); runs language-specific smoke tests (compileall, bun install+lint+build+test, cargo build, swift build) |
| `tools/inject_tracking.py` | Replaces the tracking placeholder with a Umami `<script>` tag, indentation-preserving — handles both `.html` (`<!-- TRACKING_PLACEHOLDER -->`) and `.tsx` (`{/* TRACKING_PLACEHOLDER */}`) |
| `tools/test_i18n_check.py` | Offline fixtures for `check_i18n.py`: missing/extra key, placeholder and plural mismatch, `.strings` (UTF-8/16), Android, Shopify `en.default`, not-configured mode, phone-home record, and a guard that the script contains no Jinja delimiters |
| `tools/update_projects.py` | Batch scaffold update across `~/dev`: skips unversioned, retrofit, non-git and up-to-date projects and any project with uncommitted changes in a file it would write; writes only tooling + `.atlas`; commits exactly those paths. Covered by `tools/test_update_projects.py` |
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

- **Multilingual by default**: every template except the exempt four ships `en` (base, fallback) + `nl` (informal je/jij) language files from the first render, a stack-native runtime (see "Multilingual runtimes") and a configured `just i18n-check`. The contract: user-facing strings are looked up by key, never hardcoded; logs and developer errors stay English; `nl` has exactly `en`'s keys and placeholders; placeholders are `{name}` (Shopify keeps Liquid double braces, Apple `.strings` use `%@`); plurals are `{"one": …, "other": …}` objects; locale resolves explicit choice (flag, URL, cookie, setting) → `LC_ALL`/`LC_MESSAGES`/`LANG`, `Accept-Language` or system language → `en`; adding a language is one file plus at most one registration. Language files and `.claude/scripts/` are rendered by Jinja, so they never contain `{{`, `{%`, `{#` or ICU `#` unless the path is in `_copy_without_render`. Exempt, with the checker shipped dormant (opt in by adding an `i18n` block to `.quality.json`): typescript/node-worker, node-lib, bun-package (no user-facing text) and raycast-extension (the Raycast Store requires US English). `render_test.py` fails any non-exempt template whose checker does not report `i18n: ok`.
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

<!-- agent-log:policy -->
### Shared agent journal

Use `./agent-log` (a shim for `atlas agent-log` — both are identical) for short-lived
operational awareness between concurrent agents. It is not chat and not a task tracker: the
issue tracker remains the source of truth for ownership, blockers, and durable findings.

- Run `./agent-log recent` before interpreting shared state.
- Before an action that can change another agent's observations, write an intent with every
  affected scope. This includes shared-worktree edits, generated artifacts, git/index
  mutations, and shared ports, processes, or services.
- Run builds, tests, and deployments through the wrapper so start, commit, dirty state,
  duration, exit code, and outcome are recorded even on failure:
  `./agent-log run build|test|deploy --scope <resource> [--bead <id>] -- <command...>`.
- For manual operations, use `./agent-log begin <operation> --scope <resource> [--bead <id>]
  -- <summary>` and always close the returned id with `./agent-log end <id> --outcome
  ok|failed|cancelled -- <result>`. `<operation>` is one of build, commit, deploy, edit, implement, investigate, merge, push, review, sync, test — what
  makes this particular run specific goes in the summary, never in an invented operation name.
- Record a temporary result-affecting discovery with `./agent-log finding --scope <resource>
  --evidence <fact> [--bead <id>] -- <summary>`. This is the entry that saves another agent a
  wasted run, and the one most often skipped — write one whenever you learn something that
  would change what a concurrent agent does next, especially a dead end. Promote lasting
  knowledge to the issue tracker or the relevant doc.
- At session end, write `./agent-log handoff -- <stopping point + next step>` — the durable
  baton the next session's briefing picks up. Handoffs never expire; the latest one is
  always shown by `recent`.
- Intents expire after 20 minutes and findings after 4 hours unless `--ttl` overrides them.
  Renew by closing and reopening an intent; never treat an expired entry as current.
- Keep summaries factual and short. Do not reply, ask questions, mention agents, narrate
  routine progress, or log isolated reads/edits/tests that cannot affect anyone else.

Canonical scopes are `path:<repo-relative-path>`, `artifact:<name>`, `service:<name>`,
`host:<name>`, `port:<number>`, and `git:<worktree-or-ref>`; a repo may define additional
canonical scopes of its own. Add multiple `--scope` flags when needed. The journal SQLite db
lives in the git common directory, so linked worktrees share it without dirtying the repo.
