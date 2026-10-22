#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit
from http.server import HTTPServer, SimpleHTTPRequestHandler

REPO = Path(__file__).resolve().parent.parent
DEV_DIST = REPO / '.dev-dist'

class DevHandler(SimpleHTTPRequestHandler):
    """Sirve exclusivamente desde .dev-dist, independientemente del cwd."""
    def translate_path(self, path):
        raw_path = unquote(urlsplit(path).path)
        parts = [part for part in raw_path.split('/') if part not in ('', '.', '..')]
        candidate = (DEV_DIST / Path(*parts)).resolve()
        try:
            candidate.relative_to(DEV_DIST.resolve())
        except ValueError:
            return str(DEV_DIST / '__blocked_path__')
        return str(candidate)

    def _prepare(self):
        """Resuelve redirecciones, índices y 404. Devuelve True si ya ha respondido por su cuenta."""
        parts = urlsplit(self.path)
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if not parts.path.endswith('/'):
                location = parts.path + '/' + (f'?{parts.query}' if parts.query else '')
                self.send_response(301)
                self.send_header('Location', location)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return True
            if os.path.exists(os.path.join(path, 'index.html')):
                # Se reescribe solo la ruta (parts.path ya termina en "/"); concatenar otra "/" daria
                # "//index.html", que urlsplit interpreta como un host y provocaba un 301 a http://index.html/.
                self.path = parts.path + 'index.html'
        elif not os.path.exists(path):
            notfound = DEV_DIST / '404.html'
            if notfound.exists():
                body = notfound.read_bytes()
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(body)
                return True
        return False

    def do_GET(self):
        if not self._prepare():
            super().do_GET()

    def do_HEAD(self):
        if not self._prepare():
            super().do_HEAD()

def build_dev(minify):
    args = [sys.executable, str(REPO / 'legible' / 'build.py'), '--out', str(DEV_DIST), '--minify', 'true' if minify else 'false']
    result = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def watch_src(callback, interval=0.5):
    mtimes = {}
    for p in (REPO / 'src').rglob('*'):
        if p.is_file():
            mtimes[p] = p.stat().st_mtime
    while True:
        changed = False
        for p in list(mtimes.keys()):
            if not p.exists():
                del mtimes[p]
                changed = True
            else:
                mtime = p.stat().st_mtime
                if mtime != mtimes.get(p):
                    mtimes[p] = mtime
                    changed = True
        for p in (REPO / 'src').rglob('*'):
            if p.is_file() and p not in mtimes:
                mtimes[p] = p.stat().st_mtime
                changed = True
        if changed:
            callback()
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description='Development server for the configured static site')
    parser.add_argument('--port', type=int, default=3001)
    parser.add_argument('--minify', action='store_true')
    args = parser.parse_args()

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True
    server = ReusableHTTPServer(('localhost', args.port), DevHandler)
    print(f'Serving .dev-dist on http://localhost:{args.port}')

    last_error = None

    def rebuild():
        nonlocal last_error
        code, out, err = build_dev(args.minify)
        if code != 0:
            last_error = out + err
            print('Build failed:')
            print(last_error)
        else:
            last_error = None
            print('Build OK')

    rebuild()

    def signal_handler(sig, frame):
        print('\nStopping dev server')
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    def watcher():
        watch_src(rebuild)

    import threading
    t = threading.Thread(target=watcher, daemon=True)
    t.start()

    server.serve_forever()

if __name__ == '__main__':
    main()
