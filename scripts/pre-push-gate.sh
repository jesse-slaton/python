#!/usr/bin/env bash
#
# pre-push-gate.sh -- full local gate before push.
#
# Steps (in order, every step runs; the gate exits non-zero if any failed):
#   1. ruff check          -- lint (ruff version pinned in ci.yml)
#   2. ruff format --check -- formatting
#   3. pre-commit          -- pre-commit run --all-files (gitleaks, typos, ...)
#   4. pytest              -- update-catalog-fetcher suite, as the Test legs run
#                             it; FAILS when 0 tests are collected (pytest exit 5)
#   5. bandit              -- same args as CI (-c pyproject.toml -r . -ll)
#   6. pip-audit           -- all four requirements files, as CI does
#   7. zizmor              -- .github/workflows; any finding fails, as CI does
#   8. mypy ratchet        -- error count must not exceed MYPY_BASELINE, which is
#                             READ from ci.yml so there is ONE number; a missing
#                             mypy summary line fails closed
#   9. actionlint          -- .github/workflows (only when installed)
#
# This script mirrors .github/workflows/ci.yml; change both together.
#
# Tool strategy: with uv installed every tool runs through
# `uv run --no-project --python 3.12 --with <tool>==<pin>` (pins are read from
# ci.yml), so a fresh clone needs only uv. Without uv a tool found on PATH is
# used instead. A tool unavailable both ways is SKIPPED with a loud WARN line;
# a tool that runs and fails fails the gate. A skip is never a silent pass.
#
# Exit 0 = every step passed or was skipped with a WARN; non-zero = a failure.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CI_YML=".github/workflows/ci.yml"
PY=3.12
# zizmor is not pinned in ci.yml (the action picks its own); pinned here.
ZIZMOR_VERSION="1.32.0"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Keep tool caches/artifacts out of the tree where we can.
export PYTHONDONTWRITEBYTECODE=1

failed=()
skipped=()

# have CMD -- true when CMD is on PATH.
have() { command -v "$1" >/dev/null 2>&1; }

# pin NAME -> "NAME==x.y.z" as pinned in ci.yml (first match); fails the gate
# loudly if the pin cannot be read, rather than running an unpinned tool.
pin() {
    local line
    line="$(grep -oE "(\"|' )?${1}(\[[a-z]+\])?==[0-9][0-9A-Za-z.]*" "$CI_YML" | head -n1 | tr -d "\"' ")" || true
    if [ -z "$line" ]; then
        echo "FAIL: cannot read the ${1} pin from $CI_YML" >&2
        exit 1
    fi
    printf '%s' "$line"
}

# step_ok / step_fail / step_skip -- print and record a step outcome.
step_ok() { echo "OK"; }
step_fail() { echo "FAIL: $1"; failed+=("$1"); }
step_skip() {
    echo "WARN: SKIP $1 -- $2 (this step did NOT run; install uv or the tool)"
    skipped+=("$1")
}

# run_step NAME COMMAND...  -- runs COMMAND, records the outcome, never aborts.
run_step() {
    local name="$1"
    shift
    if "$@"; then step_ok; else step_fail "$name (exit $?)"; fi
}

# uvrun "<with args>" cmd... : uv run --no-project --python 3.12 <with args> -- cmd...
# $1 is a space-separated list of requirement specs, each passed as --with.
uvrun() {
    local specs="$1" args=() s
    shift
    for s in $specs; do args+=(--with "$s"); done
    uv run --no-project --python "$PY" "${args[@]}" -- "$@"
}

# tool_run NAME SPEC CMD...  -- run CMD via uv (with SPEC) or from PATH.
# Returns 127 (and prints nothing) only when the tool is unavailable both ways.
tool_run() {
    local bin="$1" spec="$2"
    shift 2
    if have uv; then
        uvrun "$spec" "$@"
    elif have "$bin"; then
        "$@"
    else
        return 127
    fi
}

# available TOOL -- true when TOOL can run via uv or from PATH.
available() { have uv || have "$1"; }

RUFF="$(pin ruff)"
BANDIT="$(pin bandit)"
PIPAUDIT="$(pin pip-audit)"
MYPY="$(pin mypy)"
TYPES_REQUESTS="$(pin types-requests)"
BANDIT_SPEC="bandit[toml]==${BANDIT#*==}"

echo "=== ruff check ($RUFF) ==="
if available ruff; then
    run_step "ruff check" tool_run ruff "$RUFF" ruff check .
else step_skip "ruff check" "neither uv nor ruff on PATH"; fi

echo ""
echo "=== ruff format --check ==="
if available ruff; then
    run_step "ruff format" tool_run ruff "$RUFF" ruff format --check .
else step_skip "ruff format" "neither uv nor ruff on PATH"; fi

echo ""
echo "=== pre-commit run --all-files ==="
if have pre-commit; then
    run_step "pre-commit" pre-commit run --all-files
elif have uv; then
    run_step "pre-commit" uvrun "pre-commit" pre-commit run --all-files
else step_skip "pre-commit" "neither pre-commit nor uv installed"; fi

echo ""
echo "=== pytest (update-catalog-fetcher) ==="
# pytest exits 5 when it collects no tests; that must fail the gate, as in CI.
# fetcher_tests -- run the update-catalog-fetcher suite as the CI Test legs do.
fetcher_tests() {
    (
        cd update-catalog-fetcher
        if have uv; then
            uv run --no-project --python "$PY" --with-requirements requirements-dev.txt -- python -m pytest
        elif have python3 && python3 -c 'import pytest' 2>/dev/null; then
            python3 -m pytest
        else
            exit 127
        fi
    )
}
if have uv || { have python3 && python3 -c 'import pytest' 2>/dev/null; }; then
    run_step "pytest" fetcher_tests
else step_skip "pytest" "neither uv nor a python3 with pytest installed"; fi

echo ""
echo "=== bandit ($BANDIT) ==="
# -x adds .venv, which bandit's exclude_dirs does not cover (CI has no .venv).
if available bandit; then
    run_step "bandit" tool_run bandit "$BANDIT_SPEC" bandit -c pyproject.toml -r . -ll -x ./.venv
else step_skip "bandit" "neither uv nor bandit on PATH"; fi

echo ""
echo "=== pip-audit ($PIPAUDIT) ==="
# pip-audit builds a throwaway venv per requirements file. A uv-MANAGED CPython
# on macOS cannot do that (the copied interpreter aborts: dyld cannot find
# libpython, so ensurepip dies with SIGABRT), so prefer a system interpreter
# >= 3.12 (e.g. Homebrew) and fall back to uv's managed 3.12 (fine on Linux).
# Only the audit uses this; resolution of these pins does not depend on 3.12.
# audit_all -- pip-audit every requirements file; nonzero if any audit fails.
audit_all() {
    local req rc=0 audit_py
    audit_py="$PY"
    if have uv; then
        audit_py="$(uv python find --python-preference only-system ">=${PY}" 2>/dev/null)" || audit_py="$PY"
    fi
    for req in requirements-dev.txt \
        packagemanager-tui/requirements.txt \
        update-catalog-fetcher/requirements.txt \
        update-catalog-fetcher/requirements-dev.txt; do
        echo "--- pip-audit ${req}"
        if have uv; then
            uv run --no-project --python "$audit_py" --with "$PIPAUDIT" -- pip-audit -r "$req" || rc=$?
        else
            pip-audit -r "$req" || rc=$?
        fi
    done
    return "$rc"
}
if available pip-audit; then
    run_step "pip-audit" audit_all
else step_skip "pip-audit" "neither uv nor pip-audit on PATH"; fi

echo ""
echo "=== zizmor ($ZIZMOR_VERSION) ==="
if have uvx; then
    run_step "zizmor" uvx --python "$PY" "zizmor==${ZIZMOR_VERSION}" .github/workflows
elif have zizmor; then
    run_step "zizmor" zizmor .github/workflows
else step_skip "zizmor" "neither uvx nor zizmor on PATH"; fi

echo ""
echo "=== mypy ratchet ($MYPY) ==="
# mypy_ratchet -- fail when mypy errors exceed MYPY_BASELINE from ci.yml.
mypy_ratchet() {
    local baseline log="$TMP/mypy.log" count
    baseline="$(grep -oE 'MYPY_BASELINE: "[0-9]+"' "$CI_YML" | head -n1 | grep -oE '[0-9]+')" || true
    if [ -z "$baseline" ]; then
        echo "cannot read MYPY_BASELINE from $CI_YML"
        return 1
    fi
    # Judged by the count below, not mypy's exit code.
    mypy_cmd >"$log" 2>&1 || true
    cat "$log"
    # A crash or config error prints no summary line; never read that as 0 errors.
    if ! grep -qE '^(Found [0-9]+ errors? in|Success: no issues found)' "$log"; then
        echo "mypy did not produce a result summary"
        return 1
    fi
    count="$(grep -c ': error:' "$log" || true)"
    echo "mypy errors: ${count} (baseline ${baseline})"
    if [ "$count" -gt "$baseline" ]; then
        echo "mypy errors rose from ${baseline} to ${count}"
        return 1
    fi
}
# mypy_cmd -- run mypy via uv, or from PATH when uv is absent.
mypy_cmd() {
    if have uv; then
        uv run --no-project --python "$PY" \
            --with "$MYPY" --with "$TYPES_REQUESTS" \
            --with-requirements update-catalog-fetcher/requirements.txt \
            --with-requirements packagemanager-tui/requirements.txt \
            -- mypy .
    else
        mypy .
    fi
}
if available mypy; then
    run_step "mypy ratchet" mypy_ratchet
else step_skip "mypy ratchet" "neither uv nor mypy on PATH"; fi

echo ""
echo "=== actionlint ==="
if have actionlint; then
    run_step "actionlint" actionlint
else step_skip "actionlint" "actionlint not installed (pre-commit also runs it)"; fi

echo ""
if [ "${#skipped[@]}" -gt 0 ]; then
    echo "WARN: skipped steps: ${skipped[*]}"
fi
if [ "${#failed[@]}" -gt 0 ]; then
    echo "GATE FAILED: ${failed[*]}"
    exit 1
fi
echo "All hard checks passed."
