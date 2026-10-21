#!/usr/bin/env python3
"""legible: lanza en orden pruebas -> build + validación -> servidor local.

    python3 legible/run_all.py              # pruebas, build.sh (compila y valida) y, si todo va bien, dev.py
    python3 legible/run_all.py --no-dev     # igual, pero sin arrancar el servidor (útil antes de publicar)
    python3 legible/run_all.py --skip-tests # sin pruebas (cuando solo has tocado src/)

Se detiene en el primer paso que falle. build.sh ya ejecuta check_site.py, así que no se llama aparte.
Respeta las variables de entorno de build.sh (SITE_URL, CSS_MINIFY, CHECK_STRICT).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def paso(titulo, cmd):
    print(f'\n━━━ {titulo} ━━━', flush=True)
    code = subprocess.run(cmd, cwd=REPO).returncode
    if code != 0:
        print(f'\n✗ «{titulo}» ha fallado (código {code}). Me detengo aquí.', file=sys.stderr)
        sys.exit(code)
    print(f'✓ {titulo}', flush=True)


def main():
    ap = argparse.ArgumentParser(description='Pruebas, build + validación y servidor local, en ese orden.')
    ap.add_argument('--no-dev', action='store_true', help='no arrancar el servidor local al final')
    ap.add_argument('--skip-tests', action='store_true', help='saltar las pruebas')
    ap.add_argument('--port', type=int, default=3001, help='puerto del servidor local (por defecto 3001)')
    args = ap.parse_args()

    if not args.skip_tests:
        paso('1/3 Pruebas', [sys.executable, '-m', 'unittest', 'discover', 'tests'])

    bash = shutil.which('bash')
    if not bash:
        sys.exit('✗ No encuentro bash para ejecutar build.sh. En Windows usa Git Bash o WSL.')
    paso('2/3 Build + validación (build.sh)', [bash, str(REPO / 'legible' / 'build.sh')])

    if args.no_dev:
        print('\nListo. Sin servidor (--no-dev). La web está en dist/.')
        return
    print('\n━━━ 3/3 Servidor local (Ctrl+C para salir) ━━━', flush=True)
    try:
        sys.exit(subprocess.run([sys.executable, str(REPO / 'legible' / 'dev.py'), '--port', str(args.port)],
                                cwd=REPO).returncode)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
