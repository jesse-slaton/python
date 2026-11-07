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

# Every check runs BEFORE anything changes, so a refusal leaves the old setup
# exactly as it was.
#
# core.hooksPath must be unset in every scope that applies to any worktree
# (system, global, local, and each linked worktree's own config). The one
# value tolerated is the earlier installer's local `.githooks`, which this run
# migrates away. Anything else would bypass the shared shims.
# shellcheck source=scripts/lib-hookspath.sh
. scripts/lib-hookspath.sh
hookspath_scan || { echo "FAIL: could not read core.hooksPath everywhere; nothing was changed." >&2; exit 1; }
legacy=0
nconf=0
for i in ${HP_WT[@]+"${!HP_WT[@]}"}; do
    scope="${HP_SCOPE[$i]}" value="${HP_VALUE[$i]}" wt="${HP_WT[$i]}"
    if [ "$scope" = "local" ] && [ "$value" = ".githooks" ]; then
        legacy=1
        continue
    fi
    # Shared scopes repeat once per worktree; report each only once.
    if [ "$scope" != "worktree" ]; then
        [ "$wt" = "$(pwd -P)" ] || continue
    fi
    if [ "$nconf" -eq 0 ]; then
        echo "FAIL: core.hooksPath is set where it would bypass the shared hook shims; nothing was changed." >&2
    fi
    nconf=$((nconf + 1))
    echo "  worktree $wt: '$value' (scope: $scope)" >&2
    case "$scope" in
        local | global | system | worktree)
            echo "    move any hooks you need from '$value' into .githooks/, then: git -C '$wt' config --$scope --unset core.hooksPath" >&2
            ;;
        *)
            echo "    it comes from the '$scope' scope (GIT_CONFIG_* or -c); remove it there" >&2
            ;;
    esac
done
if [ "$nconf" -gt 0 ]; then
    echo "Then re-run: bash scripts/install-hooks.sh" >&2
    exit 1
fi

hooks_dir="$(git rev-parse --path-format=absolute --git-common-dir)/hooks"

# Refuse to overwrite a hook this installer did not write.
for h in $HOOKS; do
    f="$hooks_dir/$h"
    if [ -e "$f" ] && ! grep -qF "$MARKER" "$f"; then
        echo "FAIL: $f already exists and was not written by this installer; nothing was changed." >&2
        echo "Move anything you still need from it into .githooks/$h, delete it, then re-run this script." >&2
        exit 1
    fi
done

# All checks passed. If anything below fails, put the legacy setting back so
# the clone is never left with no active hooks.
if [ "$legacy" -eq 1 ]; then
    trap 'git config --local core.hooksPath .githooks; echo "install-hooks: failed; restored core.hooksPath=.githooks" >&2' ERR
fi
mkdir -p "$hooks_dir"
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

if [ "$legacy" -eq 1 ]; then
    git config --local --unset core.hooksPath
    echo "Removed the old core.hooksPath=.githooks setting (replaced by the shims)."
fi
bash scripts/check-hooks.sh
trap - ERR
