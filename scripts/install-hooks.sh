#!/usr/bin/env bash
# Install the repo's git hooks: point core.hooksPath at .githooks (so every
# worktree inherits them), make the hooks and scripts executable, then verify.
# Run from anywhere inside the repo.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
current=$(git config --get core.hooksPath 2>/dev/null || true)
if [ -n "$current" ] && [ "$current" != ".githooks" ]; then
    echo "FAIL: core.hooksPath is already '$current'; refusing to replace it." >&2
    echo "Move any hooks you still need from '$current' into .githooks/, then run:" >&2
    echo "  git config --unset core.hooksPath && bash scripts/install-hooks.sh" >&2
    exit 1
fi
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh
bash scripts/check-hooks.sh
