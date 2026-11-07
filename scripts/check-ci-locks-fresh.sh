#!/usr/bin/env bash
# Verify every hash lock under .github/ci-requirements/ is exactly what its
# .in source resolves to: compile each <name>.in from scratch into an EMPTY
# temp output with the one recipe below and compare against the committed
# <name>.lock.
#
# Why this exists: CI installs these locks with `pip install --require-hashes`
# (Scorecard Pinned-Dependencies), so an .in edit without a re-compile, a
# hand-edited lock, or a bump to a `-r`-included project requirements file
# that the lock no longer satisfies would otherwise go unnoticed until an
# install breaks (or never, if the lock just silently keeps the old pin).
#
# Determinism: the temp output starts empty, so uv has NO preferences from the
# committed lock (seeding it would let a hand-edited transitive pin that the
# .in still allows reproduce itself and pass). The fresh resolution is pinned
# in time instead by --exclude-newer EXCLUDE_NEWER: uv ignores every file
# uploaded after that instant, so neither a new release nor a wheel uploaded
# later for an already-pinned version changes the output.
#
# EXCLUDE_NEWER below is the ONE place the timestamp lives; check and --write
# both read it. A tool bump = edit the .in (and/or advance EXCLUDE_NEWER, which
# moves every transitive pin to the newest release before it), then --write.
#
# Resolver: CI installs uv from .github/ci-tools/lock-tools.lock; another uv
# version may resolve or format differently, so the script refuses to run with
# any uv whose version differs from that pin. It deliberately ignores $UV:
# `uv run` exports UV pointing at the OUTER uv, which would silently swap the
# resolver when this runs inside `uv run --with-requirements lock-tools.lock`.
#
# Header rule: --custom-compile-command makes uv's header name this script
# rather than the output path, so it is identical for the temp file; both
# sides are still compared from their first line that is neither empty nor a
# comment through EOF. uv's `# via` annotations come after the first
# requirement and are still compared.
#
# Usage: scripts/check-ci-locks-fresh.sh [--write]
#   --write   regenerate every lock in place (same recipe) instead of checking.
#   CI_LOCKS_UV=/path/to/uv overrides the uv binary (default: uv on PATH); its
#   version must still equal the lock-tools.lock pin.
set -euo pipefail

# RFC 3339, UTC. Must be in the past when committed.
EXCLUDE_NEWER="2026-11-07T00:00:00Z"

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOCK_DIR="$REPO_ROOT/.github/ci-requirements"
TOOLS_LOCK="$REPO_ROOT/.github/ci-tools/lock-tools.lock"
UV_BIN="${CI_LOCKS_UV:-uv}"
# The one compile recipe. --universal emits environment markers so a single
# lock serves every interpreter/OS CI uses (Linux 3.12 + 3.14, Windows 3.12);
# --python-version 3.12 is the floor (root requires-python).
UV_FLAGS=(pip compile --quiet --generate-hashes --universal --python-version 3.12
  --exclude-newer "$EXCLUDE_NEWER"
  --custom-compile-command "bash scripts/check-ci-locks-fresh.sh --write")

mode="check"
case "${1:-}" in
"") ;;
--write) mode="write" ;;
*)
  echo "usage: $0 [--write]" >&2
  exit 2
  ;;
esac

if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  echo "::error::uv not found ($UV_BIN); install the pinned copy: python -m pip install --require-hashes -r .github/ci-tools/lock-tools.lock" >&2
  exit 1
fi

pinned_uv="$(sed -n -E 's/^uv==([^ ;\\]+).*/\1/p' "$TOOLS_LOCK")"
if [ "$(printf '%s\n' "$pinned_uv" | grep -c .)" -ne 1 ]; then
  echo "::error file=.github/ci-tools/lock-tools.lock::expected exactly one uv==<version> pin in lock-tools.lock" >&2
  exit 1
fi
actual_uv="$("$UV_BIN" --version | awk '{print $2}')"
if [ "$actual_uv" != "$pinned_uv" ]; then
  echo "::error::$UV_BIN is uv $actual_uv but the locks are resolved with uv $pinned_uv (.github/ci-tools/lock-tools.lock). Run via the pinned copy, e.g. uv run --no-project --with-requirements .github/ci-tools/lock-tools.lock -- env -u UV bash scripts/check-ci-locks-fresh.sh" >&2
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
for lock in *.lock; do
  if [ ! -f "${lock%.lock}.in" ]; then
    echo "::error file=.github/ci-requirements/$lock::$lock has no ${lock%.lock}.in source"
    failed=1
  fi
done

for src in "${sources[@]}"; do
  name="${src%.in}"
  lock="$name.lock"
  rel=".github/ci-requirements/$lock"

  # Always compile into a path that does not exist yet: no preference seeding.
  if ! "$UV_BIN" "${UV_FLAGS[@]}" "$src" -o "$tmp/$lock"; then
    echo "::error file=$rel::uv could not resolve $src (exclude-newer $EXCLUDE_NEWER) -- see output above"
    failed=1
    continue
  fi

  if [ "$mode" = write ]; then
    mv "$tmp/$lock" "$lock"
    echo "$lock: regenerated from $src (exclude-newer $EXCLUDE_NEWER)"
    continue
  fi

  if [ ! -f "$lock" ]; then
    echo "::error file=.github/ci-requirements/$src::$src has no compiled $lock; run scripts/check-ci-locks-fresh.sh --write"
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
    echo "$lock: fresh (matches $src resolved at $EXCLUDE_NEWER)"
    continue
  fi

  pins "$tmp/$name.committed" >"$tmp/$name.cpins"
  pins "$tmp/$name.fresh" >"$tmp/$name.fpins"
  only_committed="$(comm -23 "$tmp/$name.cpins" "$tmp/$name.fpins" | paste -sd' ' -)"
  only_fresh="$(comm -13 "$tmp/$name.cpins" "$tmp/$name.fpins" | paste -sd' ' -)"
  diff -u --label "$lock (committed)" --label "$lock (regenerated)" \
    "$tmp/$name.committed" "$tmp/$name.fresh" | head -n 200 || true
  echo "::error file=$rel::$lock does not match a fresh resolution of $src at exclude-newer $EXCLUDE_NEWER. Committed-only pins: ${only_committed:-none}. Resolver's pins: ${only_fresh:-none} (if both are none, only hashes/annotations differ). Never edit a lock by hand: run scripts/check-ci-locks-fresh.sh --write and commit the .in and .lock together."
  failed=1
done

exit "$failed"
