"""Pruebas del servidor de desarrollo (legible/dev.py). Solo librería estándar."""
import http.client
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'legible'))
import dev  # noqa: E402


class TestServidorDev(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name).resolve()
        (root / 'servicios').mkdir()
        (root / 'index.html').write_text('<h1>home</h1>', encoding='utf-8')
        (root / 'servicios' / 'index.html').write_text('<h1>servicios</h1>', encoding='utf-8')
        (root / '404.html').write_text('<h1>no existe</h1>', encoding='utf-8')
        (root / 'robots.txt').write_text('User-agent: *', encoding='utf-8')
        cls._old = dev.DEV_DIST
        dev.DEV_DIST = root
        cls.server = dev.HTTPServer(('127.0.0.1', 0), dev.DevHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        dev.DEV_DIST = cls._old
        cls._tmp.cleanup()

    def get(self, path, method='GET'):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            conn.request(method, path)
            resp = conn.getresponse()
            return resp.status, resp.getheader('Location'), resp.read().decode('utf-8')
        finally:
            conn.close()

    def test_la_raiz_sirve_el_index_sin_redirigir(self):
        # Regresión: "/" daba 301 a http://index.html/ porque se reescribía a "//index.html".
        status, location, body = self.get('/')
        self.assertEqual((status, location), (200, None))
        self.assertIn('home', body)

    def test_carpeta_con_barra_sirve_su_index(self):
        status, _, body = self.get('/servicios/')
        self.assertEqual(status, 200)
        self.assertIn('servicios', body)

    def test_carpeta_sin_barra_redirige_conservando_la_query(self):
        self.assertEqual(self.get('/servicios')[:2], (301, '/servicios/'))
        self.assertEqual(self.get('/servicios?x=1')[:2], (301, '/servicios/?x=1'))

    def test_archivo_estatico(self):
        status, _, body = self.get('/robots.txt')
        self.assertEqual(status, 200)
        self.assertIn('User-agent', body)

    def test_ruta_inexistente_sirve_la_404_real(self):
        status, _, body = self.get('/nada/')
        self.assertEqual(status, 404)
        self.assertIn('no existe', body)

    def test_head_de_la_raiz_y_de_una_404(self):
        self.assertEqual(self.get('/', 'HEAD')[0], 200)
        status, _, body = self.get('/nada', 'HEAD')
        self.assertEqual((status, body), (404, ''))

    def test_no_sale_de_dev_dist(self):
        for path in ('/../etc/passwd', '/%2e%2e/%2e%2e/etc/passwd'):
            self.assertEqual(self.get(path)[0], 404, path)


if __name__ == '__main__':
    unittest.main()
