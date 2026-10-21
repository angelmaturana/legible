#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo "python3 no está disponible"; exit 1; }
python3 --version
upper() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }

# 1) Compilar (la validación la hace check_site.py justo después)
if [ "$(upper "${CSS_MINIFY:-TRUE}")" = "FALSE" ]; then
  echo "CSS_MINIFY=FALSE: compongo sin minimizar"
  python3 scripts/build.py --minify false --no-validate
else
  echo "Compongo y minimizo"
  python3 scripts/build.py --minify true --no-validate
fi

# 2) Validar: con CHECK_STRICT=TRUE (por defecto) los avisos también hacen fallar
if [ "$(upper "${CHECK_STRICT:-TRUE}")" = "TRUE" ]; then
  echo "Ejecutando check_site.py (estricto)..."
  python3 scripts/check_site.py --strict
else
  echo "Ejecutando check_site.py (solo errores)..."
  python3 scripts/check_site.py
fi

echo "Build completado en dist/"
