#!/usr/bin/env bash
# Install the repo's git hooks: point core.hooksPath at .githooks (so every
# worktree inherits them), make the hooks and scripts executable, then verify.
# Run from anywhere inside the repo.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh
bash scripts/check-hooks.sh
