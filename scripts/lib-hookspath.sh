# shellcheck shell=bash
# Sourced by scripts/install-hooks.sh and scripts/check-hooks.sh.
#
# hookspath_scan: fill HP_WT / HP_SCOPE / HP_VALUE with every core.hooksPath
# value that applies to any worktree of this repository (system, global,
# local, worktree and command scopes). Paths and values are read NUL-delimited
# (`git worktree list --porcelain -z`, `git config -z`), so a newline in a
# path cannot truncate it. A worktree whose directory no longer exists is
# skipped (nothing can commit there; `git worktree prune` removes it). Any
# other read error makes the scan FAIL (return 1) rather than look clean;
# only "setting absent" (git config exit 1) counts as no value.
hookspath_scan() {
    HP_WT=()
    HP_SCOPE=()
    HP_VALUE=()
    local rec wt rc scope value tmp
    tmp="$(mktemp -d)" || return 1
    if ! git worktree list --porcelain -z >"$tmp/list"; then
        echo "FAIL: cannot list worktrees" >&2
        rm -rf "$tmp"
        return 1
    fi
    while IFS= read -r -d '' rec; do
        case "$rec" in
            "worktree "*) wt="${rec#worktree }" ;;
            *) continue ;;
        esac
        [ -d "$wt" ] || continue
        rc=0
        git -C "$wt" config -z --show-scope --get-all core.hooksPath >"$tmp/cfg" 2>"$tmp/err" || rc=$?
        if [ "$rc" -eq 1 ]; then
            continue
        elif [ "$rc" -ne 0 ]; then
            echo "FAIL: cannot read core.hooksPath for worktree $wt: $(cat "$tmp/err")" >&2
            rm -rf "$tmp"
            return 1
        fi
        while IFS= read -r -d '' scope && IFS= read -r -d '' value; do
            HP_WT+=("$wt")
            HP_SCOPE+=("$scope")
            HP_VALUE+=("$value")
        done <"$tmp/cfg"
    done <"$tmp/list"
    rm -rf "$tmp"
    return 0
}
