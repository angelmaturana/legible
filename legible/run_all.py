#!/usr/bin/env python3
"""legible: run in order tests -> build + validation -> local server.

    python3 legible/run_all.py              # tests, build.py --all (builds and validates) and, if all goes well, dev.py
    python3 legible/run_all.py --no-dev     # same, but without starting the server (useful before publishing)
    python3 legible/run_all.py --skip-tests # without tests (when you only touched src/)

Stops at the first step that fails. `build.py --all` already validates, so check_site.py is not called separately.
Honours the environment variables of `build.py --all` (SITE_URL, CSS_MINIFY, CHECK_STRICT). Needs no bash.
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def step(title, cmd):
    print(f'\n━━━ {title} ━━━', flush=True)
    code = subprocess.run(cmd, cwd=REPO).returncode
    if code != 0:
        print(f'\n✗ "{title}" failed (exit code {code}). Stopping here.', file=sys.stderr)
        sys.exit(code)
    print(f'✓ {title}', flush=True)


def main():
    ap = argparse.ArgumentParser(description='Tests, build + validation and local server, in that order.')
    ap.add_argument('--no-dev', action='store_true', help='do not start the local server at the end')
    ap.add_argument('--skip-tests', action='store_true', help='skip the tests')
    ap.add_argument('--port', type=int, default=3001, help='local server port (default: 3001)')
    args = ap.parse_args()

    if not args.skip_tests:
        step('1/3 Tests', [sys.executable, '-B', '-m', 'unittest', 'discover', 'tests'])

    step('2/3 Build + validation (build.py --all)', [sys.executable, str(REPO / 'legible' / 'build.py'), '--all'])

    if args.no_dev:
        print('\nDone. No server (--no-dev). The site is in dist/.')
        return
    print('\n━━━ 3/3 Local server (Ctrl+C to quit) ━━━', flush=True)
    try:
        sys.exit(subprocess.run([sys.executable, str(REPO / 'legible' / 'dev.py'), '--port', str(args.port)],
                                cwd=REPO).returncode)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
