#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo "python3 is not available"; exit 1; }
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
  echo "Python 3.8 or newer is required (found $(python3 --version 2>&1))." >&2
  exit 1
fi
python3 --version
upper() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }

# 1) Build (validation is done by check_site.py right after). With CHECK_STRICT=TRUE (the default) the
#    build's own warnings, such as sample values that would be published, also fail.
STRICT_FLAG=""
if [ "$(upper "${CHECK_STRICT:-TRUE}")" = "TRUE" ]; then
  STRICT_FLAG="--strict"
fi
if [ "$(upper "${CSS_MINIFY:-TRUE}")" = "FALSE" ]; then
  echo "CSS_MINIFY=FALSE: building without minifying"
  python3 legible/build.py --minify false --no-validate $STRICT_FLAG
else
  echo "Building and minifying"
  python3 legible/build.py --minify true --no-validate $STRICT_FLAG
fi

# 2) Validate: with CHECK_STRICT=TRUE (the default) warnings also fail
if [ "$(upper "${CHECK_STRICT:-TRUE}")" = "TRUE" ]; then
  echo "Running check_site.py (strict)..."
  python3 legible/check_site.py --strict
else
  echo "Running check_site.py (errors only)..."
  python3 legible/check_site.py
fi

# 3) Warn (without failing) if the sample domain is still in the output
if grep -q 'YOUR-DOMAIN' dist/robots.txt 2>/dev/null; then
  echo "WARNING: dist/ still uses the sample domain YOUR-DOMAIN.com. Set SITE_URL or site_url in src/data/site.json before publishing." >&2
fi

echo "Build finished in dist/"
