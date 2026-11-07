#!/usr/bin/env bash
# Verify the git hooks are correctly wired up (see scripts/install-hooks.sh).
# Exits 0 when configuration is correct, non-zero otherwise.

set -euo pipefail

# Hook paths are relative to the repo root; resolve them from there.
cd "$(git rev-parse --show-toplevel)"

MARKER="# installed by scripts/install-hooks.sh"
FIX="Fix: run 'bash scripts/install-hooks.sh' from this repo"

# core.hooksPath set anywhere that applies to any worktree bypasses the shims.
bad=0
while IFS= read -r wt; do
    while IFS=$'\t' read -r scope value; do
        [ -n "${scope:-}" ] || continue
        echo "FAIL: worktree $wt has core.hooksPath='$value' (scope: $scope); it must be unset so the shared hook shims run" >&2
        bad=1
    done < <(git -C "$wt" config --show-scope --get-all core.hooksPath 2>/dev/null || true)
done < <(git worktree list --porcelain | sed -n 's/^worktree //p')
if [ "$bad" -ne 0 ]; then
    echo "$FIX" >&2
    exit 1
fi

hooks_dir="$(git rev-parse --path-format=absolute --git-common-dir)/hooks"
for h in pre-commit commit-msg pre-push; do
    shim="$hooks_dir/$h"
    if [ ! -x "$shim" ] || ! grep -qF "$MARKER" "$shim"; then
        echo "FAIL: $shim is missing, not executable, or not the installer's shim" >&2
        echo "      (\`pre-commit install\` replaces it; do not run that here)" >&2
        echo "$FIX" >&2
        exit 1
    fi
    if [ ! -x ".githooks/$h" ]; then
        echo "FAIL: .githooks/$h missing or not executable" >&2
        echo "$FIX" >&2
        exit 1
    fi
done

if [ ! -x "scripts/pre-push-gate.sh" ]; then
    echo "FAIL: scripts/pre-push-gate.sh missing or not executable" >&2
    echo "$FIX" >&2
    exit 1
fi

echo "OK: hook shims installed in $hooks_dir; .githooks/{pre-commit,commit-msg,pre-push} and scripts/pre-push-gate.sh executable"
