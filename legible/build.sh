#!/usr/bin/env bash
# Thin wrapper: everything (build, validation, pre-launch notice) lives in `build.py --all`, which also
# runs without bash (`python3 legible/build.py --all`). Variables: SITE_URL, CSS_MINIFY, CHECK_STRICT.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 legible/build.py --all "$@"
