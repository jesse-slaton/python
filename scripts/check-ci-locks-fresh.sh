#!/usr/bin/env bash
# Verify every hash lock under .github/ci-requirements/ is exactly what its
# .in source resolves to: re-compile each <name>.in into a temp file with the
# same uv flags and compare against the committed <name>.txt.
#
# Why this exists: CI installs these locks with `pip install --require-hashes`
# (Scorecard Pinned-Dependencies), so an .in edit without a re-compile, a
# hand-edited lock, or a bump to a `-r`-included project requirements file
# that the lock no longer satisfies would otherwise go unnoticed until an
# install breaks (or never, if the lock just silently keeps the old pin).
#
# Determinism: the committed lock is copied to the temp output first, so uv
# uses its pins as preferences (as `uv pip compile -o` always does) and only
# re-resolves what the sources force to move. A fresh lock therefore
# reproduces byte-for-byte. One known non-staleness cause of a diff: a package
# uploading a new wheel for an already-pinned version adds a hash; the fix is
# the same as for a stale lock (re-run with --write and commit).
#
# Header rule: uv's own header (two comment lines naming the compile command)
# names the output path, which differs for the temp file, so both sides are
# compared from their first line that is neither empty nor a comment through
# EOF. uv's `# via` annotations come after the first requirement and are
# still compared.
#
# Usage: scripts/check-ci-locks-fresh.sh [--write]
#   --write   regenerate every lock in place instead of checking.
#   UV=/path/to/uv overrides the uv binary (default: uv on PATH). CI pins uv
#   via .github/ci-tools/lock-tools.txt; another uv version may format output
#   differently and fail the comparison.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOCK_DIR="$REPO_ROOT/.github/ci-requirements"
UV="${UV:-uv}"
# The one compile recipe. --universal emits environment markers so a single
# lock serves every interpreter/OS CI uses (Linux 3.12 + 3.14, Windows 3.12);
# --python-version 3.12 is the floor (root requires-python).
UV_FLAGS=(pip compile --quiet --generate-hashes --universal --python-version 3.12)

mode="check"
case "${1:-}" in
"") ;;
--write) mode="write" ;;
*)
  echo "usage: $0 [--write]" >&2
  exit 2
  ;;
esac

if ! command -v "$UV" >/dev/null 2>&1; then
  echo "::error::uv not found (UV=$UV); install it (CI: pip install --require-hashes -r .github/ci-tools/lock-tools.txt)" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

strip_header() {
  awk 'started || ($0 != "" && $0 !~ /^#/) { started = 1; print }' "$1"
}

pins() {
  { grep -E '^[A-Za-z0-9][A-Za-z0-9._-]*==' "$1" || true; } | sed -E 's/ .*//' | sort -u
}

cd "$LOCK_DIR"
shopt -s nullglob
sources=(*.in)
if [ "${#sources[@]}" -eq 0 ]; then
  echo "::error::no .in sources found in $LOCK_DIR" >&2
  exit 1
fi

failed=0
for lock in *.txt; do
  if [ ! -f "${lock%.txt}.in" ]; then
    echo "::error file=.github/ci-requirements/$lock::$lock has no ${lock%.txt}.in source"
    failed=1
  fi
done

for src in "${sources[@]}"; do
  name="${src%.in}"
  lock="$name.txt"
  rel=".github/ci-requirements/$lock"

  if [ "$mode" = write ]; then
    "$UV" "${UV_FLAGS[@]}" "$src" -o "$lock"
    echo "$lock: regenerated from $src"
    continue
  fi

  if [ ! -f "$lock" ]; then
    echo "::error file=.github/ci-requirements/$src::$src has no compiled $lock; run scripts/check-ci-locks-fresh.sh --write"
    failed=1
    continue
  fi

  cp "$lock" "$tmp/$lock"
  if ! "$UV" "${UV_FLAGS[@]}" "$src" -o "$tmp/$lock"; then
    echo "::error file=$rel::uv could not resolve $src -- see output above"
    failed=1
    continue
  fi

  strip_header "$lock" >"$tmp/$name.committed"
  strip_header "$tmp/$lock" >"$tmp/$name.fresh"
  if [ ! -s "$tmp/$name.committed" ] || [ ! -s "$tmp/$name.fresh" ]; then
    echo "::error file=$rel::no requirement lines found after stripping the header of $lock"
    failed=1
    continue
  fi

  if cmp -s "$tmp/$name.committed" "$tmp/$name.fresh"; then
    echo "$lock: fresh (matches $src)"
    continue
  fi

  pins "$tmp/$name.committed" >"$tmp/$name.cpins"
  pins "$tmp/$name.fresh" >"$tmp/$name.fpins"
  only_committed="$(comm -23 "$tmp/$name.cpins" "$tmp/$name.fpins" | paste -sd' ' -)"
  only_fresh="$(comm -13 "$tmp/$name.cpins" "$tmp/$name.fpins" | paste -sd' ' -)"
  diff -u --label "$lock (committed)" --label "$lock (regenerated)" \
    "$tmp/$name.committed" "$tmp/$name.fresh" | head -n 200 || true
  echo "::error file=$rel::$lock does not match a fresh compile of $src. Committed-only pins: ${only_committed:-none}. Resolver's pins: ${only_fresh:-none} (if both are none, only hashes/annotations differ). Never edit a lock by hand: run scripts/check-ci-locks-fresh.sh --write and commit the .in and .txt together."
  failed=1
done

exit "$failed"
