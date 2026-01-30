#!/usr/bin/env bash
# Pre-change quality checks executed by Claude Code hooks.
# The script is written to be resilient so it can run both inside the
# cookiecutter template repository (which contains unrendered Jinja
# placeholders) and inside generated projects where the placeholders
# have been rendered away.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

info() {
  printf '%s\n' "$1"
}

run_step() {
  local label="$1"
  shift

  info "🔸 $label"
  if ! "$@"; then
    info "❌ $label failed. See the output above for details."
    exit 1
  fi
}

# Skip when we are working on the cookiecutter template itself. The
# presence of "cookiecutter.json" together with unrendered Jinja
# placeholders is a strong indicator that we are *inside* the template,
# not a rendered project. Running uv tooling against those files would
# fail because pyproject.toml contains template expressions.
if [[ -f "cookiecutter.json" ]] && grep -q '{{' "{{cookiecutter.project_name}}/pyproject.toml" 2>/dev/null; then
  info "ℹ️ Cookiecutter template detected (unrendered Jinja placeholders). Skipping pre-change checks."
  exit 0
fi

# If uv is not available we cannot run the project tooling. Rather than
# failing every Claude hook invocation we emit a helpful hint and skip.
if ! command -v uv >/dev/null 2>&1; then
  info "ℹ️ 'uv' is not available on PATH. Install uv to enable pre-change checks."
  exit 0
fi

# Keep the lock file in sync with pyproject.toml when one exists.
if [[ -s "uv.lock" ]]; then
  run_step "Verifying lock file is in sync" uv lock --locked
else
  info "ℹ️ No uv.lock file yet; skipping lock verification."
fi

# Format and lint the code base. We rely on the dev dependency group so
# the behaviour matches the Makefile targets in generated projects.
run_step "Formatting Python files" uv run --group dev ruff format --quiet .
run_step "Linting with Ruff" uv run --group dev ruff check --fix --quiet .

# Run mypy only when a mypy configuration is present; this keeps things
# fast for minimal templates that have the tooling stripped out.
if [[ -f "pyproject.toml" ]] && grep -q "\[tool.mypy\]" pyproject.toml; then
  run_step "Type checking with mypy" uv run --group dev mypy
else
  info "ℹ️ No mypy configuration detected; skipping type checks."
fi

info "✅ Pre-change checks completed successfully."
