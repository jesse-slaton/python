#!/usr/bin/env bash
# Install the repo's git hooks: point core.hooksPath at .githooks (so every
# worktree inherits them), make the hooks and scripts executable, then verify.
# Run from anywhere inside the repo.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
current=$(git config --get core.hooksPath 2>/dev/null || true)
if [ -n "$current" ] && [ "$current" != ".githooks" ]; then
    # Name the config scope that sets it: the unset command differs per scope.
    scope=$(git config --show-scope --get core.hooksPath 2>/dev/null | cut -f1)
    echo "FAIL: core.hooksPath is already '$current' (scope: ${scope:-unknown}); refusing to replace it." >&2
    echo "Move any hooks you still need from '$current' into .githooks/, then:" >&2
    case "$scope" in
        local | global | system | worktree)
            echo "  git config --$scope --unset core.hooksPath && bash scripts/install-hooks.sh" >&2
            ;;
        *)
            echo "  remove it where it is set (it comes from the '${scope:-unknown}' scope, e.g. GIT_CONFIG_* or -c);" >&2
            echo "  locate it with: git config --show-origin --show-scope --get-all core.hooksPath" >&2
            ;;
    esac
    exit 1
fi
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh
bash scripts/check-hooks.sh
