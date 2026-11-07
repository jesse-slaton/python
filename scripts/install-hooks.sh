#!/usr/bin/env bash
# Install the repo's git hooks.
#
# Writes a small shim for each hook into the repository's SHARED hooks
# directory ($(git rev-parse --git-common-dir)/hooks), which every linked
# worktree uses. Each shim runs the checked-out worktree's .githooks/<hook>,
# and FAILS CLOSED when that worktree's branch has no such hook (a branch cut
# before the hooks existed), so no worktree can silently commit or push
# without the local checks. core.hooksPath must stay unset: it would bypass
# the shared directory. Run from anywhere inside the repo.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

HOOKS="pre-commit commit-msg pre-push"
MARKER="# installed by scripts/install-hooks.sh"

current=$(git config --get core.hooksPath 2>/dev/null || true)
if [ "$current" = ".githooks" ] &&
    [ "$(git config --show-scope --get core.hooksPath | cut -f1)" = "local" ]; then
    # The previous version of this installer set it; the shims replace it.
    git config --local --unset core.hooksPath
    echo "Removed the old core.hooksPath=.githooks setting (replaced by shims)."
elif [ -n "$current" ]; then
    # Name the config scope that sets it: the unset command differs per scope.
    scope=$(git config --show-scope --get core.hooksPath 2>/dev/null | cut -f1)
    echo "FAIL: core.hooksPath is set to '$current' (scope: ${scope:-unknown}); refusing to replace it." >&2
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

hooks_dir="$(git rev-parse --path-format=absolute --git-common-dir)/hooks"
mkdir -p "$hooks_dir"

# Refuse to overwrite a hook this installer did not write.
for h in $HOOKS; do
    f="$hooks_dir/$h"
    if [ -e "$f" ] && ! grep -qF "$MARKER" "$f"; then
        echo "FAIL: $f already exists and was not written by this installer; refusing to replace it." >&2
        echo "Move anything you still need from it into .githooks/$h, delete it, then re-run this script." >&2
        exit 1
    fi
done

chmod +x .githooks/* scripts/*.sh
for h in $HOOKS; do
    cat >"$hooks_dir/$h" <<EOF
#!/usr/bin/env bash
$MARKER
# Runs this worktree's .githooks/$h. Fails closed when the checked-out branch
# has none, so a worktree on an old branch cannot skip the local checks.
top="\$(git rev-parse --show-toplevel)" || exit 1
hook="\$top/.githooks/$h"
if [ ! -x "\$hook" ]; then
    echo "$h: \$hook is missing or not executable: this branch predates the repo hooks." >&2
    echo "$h: merge main into it (git merge origin/main) so the hooks exist, then retry." >&2
    exit 1
fi
exec "\$hook" "\$@"
EOF
    chmod +x "$hooks_dir/$h"
done

bash scripts/check-hooks.sh
