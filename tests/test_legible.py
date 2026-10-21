#!/usr/bin/env python3
"""Pruebas mínimas de legible. Solo librería estándar.

    python3 -m unittest discover tests

Qué cubre (y nada más; el HTML de cada página ya lo valida check_site.py):
  1. Humo: la plantilla compila y pasa check_site en modo estricto.
  2. minify_css.
  3. minify_html.
  4. Guías y blog: front matter correcto e incorrecto.
  5. Dominio (SITE_URL) y marcadores sin resolver.
  +  Errores conocidos (expectedFailure): minify_css y el primer índice de guías/blog en estricto.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / 'scripts'

# build.py lee SITE_URL al importarse: que el entorno de quien ejecuta no influya en las pruebas.
os.environ.pop('SITE_URL', None)
sys.path.insert(0, str(SCRIPTS))
import build  # noqa: E402


# --------------------------------------------------------------------------- utilidades

def copy_project(dest):
    """Copia src/ y scripts/ a `dest` para poder modificar el proyecto sin tocar el original."""
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', 'dist', '.dev-dist')
    shutil.copytree(REPO / 'src', dest / 'src', ignore=ignore)
    shutil.copytree(SCRIPTS, dest / 'scripts', ignore=ignore)
    return dest


def run_build(project, out, site_url=None, minify=True):
    """Ejecuta build.py del proyecto indicado (sin validar). Devuelve CompletedProcess."""
    env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
    if site_url is not None:
        env['SITE_URL'] = site_url
    return subprocess.run(
        [sys.executable, str(project / 'scripts' / 'build.py'),
         '--out', str(out), '--minify', 'true' if minify else 'false', '--no-validate'],
        capture_output=True, text=True, env=env, cwd=project)


def run_check(project, out, site_url=None, strict=True):
    """Ejecuta check_site.py sobre `out`. Devuelve CompletedProcess."""
    env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
    if site_url is not None:
        env['SITE_URL'] = site_url
    cmd = [sys.executable, str(project / 'scripts' / 'check_site.py'), '--dir', str(out)]
    if strict:
        cmd.append('--strict')
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=project)


def read_all(out):
    """Texto de todos los archivos de texto de `out`, por ruta relativa."""
    data = {}
    for f in Path(out).rglob('*'):
        if f.is_file() and f.suffix in ('.html', '.txt', '.xml', '.css', '.json'):
            data[f.relative_to(out).as_posix()] = f.read_text(encoding='utf-8')
    return data


def lorem(n_words):
    """Texto de relleno sin marcadores ni palabras prohibidas por el validador."""
    base = ('Explicamos con calma qué conviene hacer primero, qué se puede dejar para más adelante '
            'y qué errores se repiten en negocios parecidos, sin prometer resultados concretos. ')
    words = base.split()
    return ' '.join((words * (n_words // len(words) + 1))[:n_words]) + '.'


def pieza_html(coll, slug, **over):
    """HTML de una guía o artículo válido. `over` sustituye o (con None) quita campos del front matter."""
    front = {
        'title': f'Pieza de prueba {slug} para el negocio | {{{{site_name}}}}',
        'description': f'Pieza de ejemplo «{slug}» para las pruebas automáticas: explica un caso concreto '
                       'sin promesas ni resultados garantizados.',
        'robots': 'index, follow',
        'canonical': 'auto',
        'type': 'guia' if coll == 'guias' else 'articulo',
        'topic': 'Tema 1',
        'published': '2026-01-10',
        'updated': '2026-02-15',
        'summary': 'Resumen breve de la pieza de prueba.',
        'service': '/servicios/servicio-generico/',
    }
    front.update(over)
    fm = '\n'.join(f'{k}: {v}' for k, v in front.items() if v is not None)
    url = f'{{{{site_url}}}}/{coll}/{slug}/'
    ld = json.dumps({'@context': 'https://schema.org', '@graph': [{
        '@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': front['title'],
        'description': front['description'], 'inLanguage': 'es-ES', 'dateModified': front['updated'],
        'isPartOf': {'@id': '{{site_url}}/#website'}, 'about': {'@id': '{{site_url}}/#business'}}]}, ensure_ascii=False)
    return f"""---
{fm}
---

<script type="application/ld+json">{ld}</script>

<main id="main">
    <section class="inner-hero page-width">
        <h1>Pieza de prueba {slug}</h1>
        <p class="lead">{lorem(60)}</p>
    </section>
    <section class="section page-width">
        <h2>Primeros pasos</h2>
        <p>{lorem(130)}</p>
        <p>{lorem(80)} Si quieres que lo hagamos nosotros, mira el
        <a href="/servicios/servicio-generico/">servicio relacionado</a>.</p>
    </section>
</main>
"""


def add_pieza(project, coll, slug, **over):
    d = project / 'src' / 'pages' / coll / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(pieza_html(coll, slug, **over), encoding='utf-8')


class ProyectoTemporal(unittest.TestCase):
    """Base: una copia del proyecto y una carpeta de salida por prueba."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.project = copy_project(self.tmp / 'proyecto')
        self.out = self.tmp / 'salida'

    def build_ok(self, **kw):
        r = run_build(self.project, self.out, **kw)
        self.assertEqual(r.returncode, 0, f'el build debía pasar:\n{r.stdout}\n{r.stderr}')
        return r

    def check_ok(self, **kw):
        r = run_check(self.project, self.out, **kw)
        modo = 'estricto' if kw.get('strict', True) else 'solo errores'
        self.assertEqual(r.returncode, 0, f'check_site debía pasar ({modo}):\n{r.stdout}')
        return r


# --------------------------------------------------------------------------- 1. humo

class TestHumo(unittest.TestCase):
    """Compila la plantilla tal cual y exige un check_site limpio (errores y avisos)."""

    def _compilar_y_validar(self, minify):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'salida'
            r = run_build(REPO, out, minify=minify)
            self.assertEqual(r.returncode, 0, f'build falló:\n{r.stdout}\n{r.stderr}')
            r = run_check(REPO, out)
            self.assertEqual(r.returncode, 0, f'check_site falló en estricto:\n{r.stdout}')
            self.assertTrue((out / 'index.html').is_file())
            self.assertTrue((out / 'sitemap.xml').is_file())

    def test_plantilla_minimizada(self):
        self._compilar_y_validar(minify=True)

    def test_plantilla_sin_minimizar(self):
        self._compilar_y_validar(minify=False)

    def test_check_site_detecta_un_error(self):
        """El humo solo vale si check_site de verdad falla cuando algo está mal."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'salida'
            run_build(REPO, out)
            index = out / 'index.html'
            index.write_text(index.read_text(encoding='utf-8').replace('<h1', '<h2').replace('</h1>', '</h2>'),
                             encoding='utf-8')
            self.assertNotEqual(run_check(REPO, out).returncode, 0)

    def test_modo_sin_validar_no_toca_la_salida_del_proyecto(self):
        """Compilar con --out no puede escribir en dist/ del proyecto."""
        existia = (REPO / 'dist').exists()
        with tempfile.TemporaryDirectory() as tmp:
            run_build(REPO, Path(tmp) / 'salida')
        self.assertEqual((REPO / 'dist').exists(), existia)


# --------------------------------------------------------------------------- 2. minify_css

class TestMinifyCss(unittest.TestCase):
    def m(self, css):
        return build.minify_css(css)

    def test_calc_conserva_espacios_de_los_operadores(self):
        self.assertEqual(self.m('a{width:calc(100% - 2rem)}'), 'a{width:calc(100% - 2rem)}')
        self.assertEqual(self.m('a{width:calc(100%   +   2rem)}'), 'a{width:calc(100% + 2rem)}')

    def test_calc_anidado_y_con_parentesis(self):
        self.assertEqual(self.m('a{width:calc( 100%  -  (2rem + 1px) )}'),
                         'a{width:calc(100% - (2rem + 1px))}')

    def test_clamp_min_max(self):
        self.assertEqual(self.m('a{width:clamp(1rem, 2.5vw, 2rem)}'), 'a{width:clamp(1rem,2.5vw,2rem)}')
        self.assertEqual(self.m('a{width:min(10px , 5vw);height:max(1px, 2px)}'),
                         'a{width:min(10px,5vw);height:max(1px,2px)}')

    def test_funciones_con_numeros_decimales(self):
        out = self.m('a{padding:clamp(24px, 4.50vw, 48.0px)}')
        self.assertEqual(out, 'a{padding:clamp(24px,4.50vw,48.0px)}')

    def test_strings_no_se_tocan(self):
        self.assertEqual(self.m('a::before{content:"a  b: c;"}'), 'a::before{content:"a  b: c;"}')
        self.assertEqual(self.m("a::before{content:'x   y ; 0.50'}"), "a::before{content:'x   y ; 0.50'}")

    def test_string_con_comillas_escapadas(self):
        css = r'a::before{content:"di \"hola  mundo\" ya"}'
        self.assertEqual(self.m(css), css)

    def test_url_entre_comillas(self):
        self.assertEqual(self.m('a{background:url("a  b.png")}'), 'a{background:url("a  b.png")}')

    def test_important(self):
        self.assertEqual(self.m('a{color:red ! important}'), 'a{color:red!important}')
        self.assertEqual(self.m('a{color:red   !important;margin:0}'), 'a{color:red!important;margin:0}')

    def test_comentarios_fuera(self):
        self.assertEqual(self.m('/* hola */ a{b:c} /* adiós\nmultilínea */'), 'a{b:c}')

    def test_ultimo_punto_y_coma(self):
        self.assertEqual(self.m('a{b:c;d:e;}'), 'a{b:c;d:e}')

    def test_numeros(self):
        self.assertEqual(self.m('a{margin:0px 0.5em 1.0px 1.50rem}'), 'a{margin:0 .5em 1px 1.5rem}')
        self.assertEqual(self.m('a{opacity:0.50;line-height:1.0}'), 'a{opacity:.5;line-height:1}')

    def test_numeros_que_no_deben_cambiar(self):
        css = 'a{top:100px;z-index:100;margin:10px;width:20.05px;height:1.05em;flex:0 0 100px}'
        self.assertEqual(self.m(css), css)

    def test_colores_hex(self):
        self.assertEqual(self.m('a{color:#FFFFFF}'), 'a{color:#FFF}')
        self.assertEqual(self.m('a{color:#aabbcc}'), 'a{color:#abc}')
        self.assertEqual(self.m('a{color:#abcdef}'), 'a{color:#abcdef}')

    def test_selectores_y_combinadores(self):
        self.assertEqual(self.m('a  >  b ~ c + d{x:y}'), 'a>b~c+d{x:y}')

    def test_media_query_sin_and(self):
        self.assertEqual(self.m('@media (min-width: 768px) { a { b: c } }'), '@media(min-width:768px){a{b:c}}')

    def test_pseudoclase_con_parentesis_sin_descendiente(self):
        # Lo que usa site.css hoy: el combinador hijo directo tras ")" es seguro.
        self.assertEqual(self.m('li:nth-child( 2n + 1 ) > a{x:y}'), 'li:nth-child(2n+1)>a{x:y}')

    def test_el_css_real_minimizado_conserva_las_reglas(self):
        """Mismas reglas antes y después: mismo número de llaves y de declaraciones."""
        css = (REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8')
        mini = build.minify_css(css)
        sin_comentarios = build.re.sub(r'/\*[\s\S]*?\*/', '', css)
        self.assertEqual(mini.count('{'), sin_comentarios.count('{'))
        self.assertEqual(mini.count('}'), sin_comentarios.count('}'))
        self.assertEqual(mini.count('{'), mini.count('}'))
        self.assertLess(len(mini), len(css))

    def test_el_css_real_sin_restos_de_los_marcadores_internos(self):
        mini = build.minify_css((REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8'))
        for resto in ('__STR_', '__MATH_', '\x00'):
            self.assertNotIn(resto, mini)


# --------------------------------------------------------------------------- 3. minify_html

class TestMinifyHtml(unittest.TestCase):
    def m(self, html):
        return build.minify_html(html)

    def test_atributos_con_espacios_dobles(self):
        self.assertEqual(self.m('<img alt="a  b" src="x">'), '<img alt="a  b" src="x">')
        self.assertEqual(self.m('<p title="z   w" data-x="a\n b">t</p>'), '<p title="z   w" data-x="a\n b">t</p>')

    def test_atributos_con_comillas_simples(self):
        self.assertEqual(self.m("<input value='a  b'>"), "<input value='a  b'>")

    def test_atributo_con_mayor_que(self):
        self.assertEqual(self.m('<p title="a > b">x</p>'), '<p title="a > b">x</p>')

    def test_pre_intacto(self):
        html = '<pre>a   b\n  c\n\n    d</pre>'
        self.assertEqual(self.m(html), html)

    def test_pre_con_etiquetas_dentro(self):
        html = '<pre class="x">  <code>uno   dos</code>\n  tres</pre>'
        self.assertEqual(self.m(html), html)

    def test_textarea_intacto(self):
        html = '<textarea name="t">  a   b \n  c </textarea>'
        self.assertEqual(self.m(html), html)

    def test_jsonld_valido_se_compacta_y_sigue_siendo_el_mismo_json(self):
        data = {'@context': 'https://schema.org', 'name': 'a  b', 'lista': [1, 2, {'x': 'ñ  é'}]}
        src = '<script type="application/ld+json">\n' + json.dumps(data, indent=4, ensure_ascii=False) + '\n</script>'
        out = self.m(src)
        inner = out[out.index('>') + 1:out.rindex('</script>')]
        self.assertEqual(json.loads(inner), data)
        self.assertNotIn('\n', inner)
        self.assertLess(len(out), len(src))

    def test_jsonld_roto_no_se_toca(self):
        src = '<script type="application/ld+json">{ roto:   sin cerrar </script>'
        self.assertEqual(self.m(src), src)

    def test_script_normal_intacto(self):
        src = '<script>var a = 1;   var b = 2;</script>'
        self.assertEqual(self.m(src), src)

    def test_style_intacto(self):
        src = '<style>a  {  color :  red  }</style>'
        self.assertEqual(self.m(src), src)

    def test_comentarios_fuera(self):
        self.assertEqual(self.m('<!-- c --><p>x</p>'), '<p>x</p>')
        self.assertEqual(self.m('<p>a<!-- c\nmultilínea -->b</p>'), '<p>ab</p>')

    def test_espacios_y_saltos_en_el_texto(self):
        self.assertEqual(self.m('<p>hola   mundo\n\n  adiós</p>'), '<p>hola mundo adiós</p>')

    def test_espacios_estructurales_entre_atributos(self):
        self.assertEqual(self.m('<a href="/x"   class="a"   >t</a>'), '<a href="/x" class="a">t</a>')

    def test_espacio_entre_elementos_en_linea_se_conserva(self):
        # Regresión: `<strong>x</strong> <small>y</small>` salía pegado («xy»). Pasaba en /precios/.
        html = '<p><strong>299 €</strong> <small>(a consultar)</small></p>'
        self.assertEqual(self.m(html), html)
        self.assertEqual(self.m('<span>a</span>\n   <span>b</span>'), '<span>a</span> <span>b</span>')
        self.assertEqual(self.m('<p>t <b>x</b> <img src="a"> <a href="/">y</a></p>'),
                         '<p>t <b>x</b> <img src="a"> <a href="/">y</a></p>')

    def test_espacio_entre_bloques_y_entre_bloque_y_linea_se_elimina(self):
        self.assertEqual(self.m('<li><a>1</a></li>\n<li><a>2</a></li>'), '<li><a>1</a></li><li><a>2</a></li>')
        self.assertEqual(self.m('<p>a</p> <span>b</span>'), '<p>a</p><span>b</span>')

    def test_precios_conserva_el_espacio_del_precio(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'salida'
            self.assertEqual(run_build(REPO, out, minify=True).returncode, 0)
            html = (out / 'precios' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('</strong> <small>', html)

    def test_espacio_entre_bloques_se_elimina(self):
        self.assertEqual(self.m('<div>\n  <p>a</p>\n  <p>b</p>\n</div>'), '<div><p>a</p><p>b</p></div>')

    def test_no_quedan_marcadores_internos(self):
        src = ('<script type="application/ld+json">{"a": 1}</script><pre>x</pre><p title="a  b">t</p>'
               '<textarea>q</textarea><style>a{}</style>')
        self.assertNotIn('\x00', self.m(src))

    def test_varios_bloques_protegidos_se_restauran_en_su_sitio(self):
        src = '<pre>1  1</pre><p>mid</p><pre>2  2</pre><textarea>3  3</textarea>'
        self.assertEqual(self.m(src), src)

    def test_pagina_real_conserva_el_texto_visible(self):
        """El texto de las páginas compiladas (sin tener en cuenta espacios) no cambia al minimizar."""
        from html.parser import HTMLParser

        class Texto(HTMLParser):
            def __init__(self):
                super().__init__()
                self.partes, self.skip = [], 0

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.skip += 1

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self.skip -= 1

            def handle_data(self, d):
                if not self.skip:
                    self.partes.append(d)

        def sin_espacios(html):
            t = Texto()
            t.feed(html)
            return ''.join(''.join(t.partes).split())

        with tempfile.TemporaryDirectory() as tmp:
            raw, mini = Path(tmp) / 'raw', Path(tmp) / 'mini'
            self.assertEqual(run_build(REPO, raw, minify=False).returncode, 0)
            self.assertEqual(run_build(REPO, mini, minify=True).returncode, 0)
            paginas = sorted(raw.rglob('*.html'))
            self.assertGreater(len(paginas), 5)
            for f in paginas:
                a = sin_espacios(f.read_text(encoding='utf-8'))
                b = sin_espacios((mini / f.relative_to(raw)).read_text(encoding='utf-8'))
                self.assertEqual(a, b, f'el texto de {f.relative_to(raw)} cambia al minimizar')


# --------------------------------------------------------------------------- 4. guías y blog

class TestColeccionesDirectas(unittest.TestCase):
    """load_collections sobre carpetas temporales: cada error debe decir qué pasa y dónde."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pages = Path(self._tmp.name)
        servicio = self.pages / 'servicios' / 'servicio-generico'
        servicio.mkdir(parents=True)
        (servicio / 'index.html').write_text('---\ntitle: S\ndescription: S\n---\n<main></main>', encoding='utf-8')

    def add(self, coll, slug, **over):
        d = self.pages / coll / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(pieza_html(coll, slug, **over), encoding='utf-8')

    def problemas(self):
        with self.assertRaises(build.CollectionError) as cm:
            build.load_collections(self.pages)
        return str(cm.exception)

    def test_sin_colecciones(self):
        self.assertEqual(build.load_collections(self.pages), {'guias': [], 'blog': []})

    def test_guia_y_articulo_validos(self):
        self.add('guias', 'mi-guia')
        self.add('blog', 'mi-articulo')
        piezas = build.load_collections(self.pages)
        self.assertEqual([p['rel'] for p in piezas['guias']], ['/guias/mi-guia/'])
        self.assertEqual([p['rel'] for p in piezas['blog']], ['/blog/mi-articulo/'])
        self.assertEqual(piezas['guias'][0]['topic'], 'Tema 1')

    def test_slug_con_tildes_o_mayusculas(self):
        self.add('guias', 'guía-útil')
        self.add('guias', 'Mayusculas')
        p = self.problemas()
        self.assertIn('guía-útil', p)
        self.assertIn('minúsculas, sin tildes', p)
        self.assertIn('Mayusculas', p)

    def test_topic_fuera_de_la_lista(self):
        self.add('guias', 'a', topic='Inventado')
        p = self.problemas()
        self.assertIn('topic "Inventado" no está en la taxonomía', p)
        self.assertIn('Tema 1', p, 'el mensaje debe listar los temas válidos')

    def test_related_con_mas_de_dos(self):
        for s in ('a', 'b', 'c', 'd'):
            self.add('guias', s)
        self.add('guias', 'e', related='/guias/a/, /guias/b/, /guias/c/')
        self.assertIn('related admite como máximo 2 enlaces y tiene 3', self.problemas())

    def test_related_a_pieza_inexistente_o_a_si_misma(self):
        self.add('guias', 'a', related='/guias/no-existe/, /guias/a/')
        p = self.problemas()
        self.assertIn('"/guias/no-existe/" no es una guía ni un artículo existente', p)
        self.assertIn('no puede apuntar a la propia pieza', p)

    def test_related_valido(self):
        self.add('guias', 'a', related='/blog/b/')
        self.add('blog', 'b', related='/guias/a/')
        build.load_collections(self.pages)

    def test_falta_un_campo_obligatorio(self):
        self.add('guias', 'a', summary=None, service=None)
        p = self.problemas()
        self.assertIn('falta "summary"', p)
        self.assertIn('falta "service"', p)

    def test_type_incorrecto_para_la_carpeta(self):
        self.add('guias', 'a', type='articulo')
        self.assertIn('type "articulo" no vale en guias/', self.problemas())

    def test_fechas_invalidas_o_en_orden_incorrecto(self):
        self.add('guias', 'a', published='10/01/2026')
        self.add('guias', 'b', published='2026-05-01', updated='2026-01-01')
        p = self.problemas()
        self.assertIn('no es una fecha ISO', p)
        self.assertIn('anterior a published', p)

    def test_service_que_no_existe(self):
        self.add('guias', 'a', service='/servicios/no-existe/')
        self.assertIn('service "/servicios/no-existe/" no apunta a una página existente', self.problemas())

    def test_indice_escrito_a_mano_y_ruta_mal_puesta(self):
        (self.pages / 'guias').mkdir()
        (self.pages / 'guias' / 'index.html').write_text('---\ntitle: x\ndescription: x\n---\n', encoding='utf-8')
        (self.pages / 'blog').mkdir()
        (self.pages / 'blog' / 'suelta.html').write_text('---\ntitle: x\ndescription: x\n---\n', encoding='utf-8')
        p = self.problemas()
        self.assertIn('el índice /guias/ se genera solo', p)
        self.assertIn('deben ser blog/<slug>/index.html', p)

    def test_type_de_coleccion_fuera_de_su_carpeta(self):
        d = self.pages / 'otra'
        d.mkdir()
        (d / 'index.html').write_text('---\ntitle: x\ndescription: x\ntype: guia\n---\n', encoding='utf-8')
        self.assertIn('solo se admite dentro de guias/ o blog/', self.problemas())

    def test_informa_de_todos_los_problemas_a_la_vez(self):
        self.add('guias', 'MAL', topic='x', published='no')
        self.assertGreaterEqual(self.problemas().count('\n') + 1, 3)

    def test_estados_del_blog(self):
        def arts(n):
            return [{'slug': str(i)} for i in range(n)]
        self.assertEqual(build.blog_state(arts(0)), 'none')
        self.assertEqual(build.blog_state(arts(1)), 'hidden')
        self.assertEqual(build.blog_state(arts(2)), 'hidden')
        self.assertEqual(build.blog_state(arts(3)), 'visible')
        self.assertFalse(build.blog_visible(arts(2)))
        self.assertTrue(build.blog_visible(arts(3)))


class TestColeccionesEnElBuild(ProyectoTemporal):
    """Compilación completa con piezas: aparición de índices, menú, sitemap y errores del build."""

    def test_sin_guias_no_hay_enlace_ni_indice(self):
        self.build_ok()
        self.assertFalse((self.out / 'guias').exists())
        self.assertFalse((self.out / 'blog').exists())
        self.assertNotIn('href="/guias/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_una_guia_real_aparece_en_menu_indice_sitemap_y_llms(self):
        add_pieza(self.project, 'guias', 'mi-primera-guia')
        self.build_ok()
        self.check_ok(strict=False)
        self.assertTrue((self.out / 'guias' / 'index.html').is_file())
        self.assertTrue((self.out / 'guias' / 'mi-primera-guia' / 'index.html').is_file())
        self.assertIn('href="/guias/"', (self.out / 'index.html').read_text(encoding='utf-8'),
                      'el menú o el pie deben enlazar a /guias/')
        sitemap = (self.out / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('/guias/</loc>', sitemap)
        self.assertIn('/guias/mi-primera-guia/</loc>', sitemap)
        self.assertIn('/guias/mi-primera-guia/', (self.out / 'llms.txt').read_text(encoding='utf-8'))

    def test_blog_con_dos_articulos_es_noindex_y_no_se_anuncia(self):
        add_pieza(self.project, 'blog', 'uno')
        add_pieza(self.project, 'blog', 'dos')
        self.build_ok()
        self.check_ok(strict=False)
        indice = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('noindex', indice)
        self.assertNotIn('/blog/</loc>', (self.out / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertNotIn('href="/blog/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_blog_con_tres_articulos_es_indexable_y_sale_en_el_menu(self):
        for s in ('uno', 'dos', 'tres'):
            add_pieza(self.project, 'blog', s)
        self.build_ok()
        self.check_ok(strict=False)
        indice = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('noindex', indice)
        self.assertIn('/blog/</loc>', (self.out / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertIn('href="/blog/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_indices_generados_con_contacto_resuelto(self):
        """Regresión: el f-string de _lead_strip_html dejaba `mailto:{contact_email}` sin sustituir."""
        add_pieza(self.project, 'guias', 'a')
        for s in ('uno', 'dos', 'tres'):
            add_pieza(self.project, 'blog', s)
        self.build_ok()
        for indice in ('guias', 'blog'):
            html = (self.out / indice / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('{contact_email}', html, indice)
            self.assertNotIn('{whatsapp_link}', html, indice)
            self.assertIn('mailto:', html)
            self.assertRegex(html, r'href="https://wa\.me/[^"]+"')

    @unittest.expectedFailure
    def test_guia_real_pasa_el_validador_estricto(self):
        # Fallo conocido: con una guía, el índice /guias/ tiene unas 120 palabras (mínimo 250) y nadie
        # enlaza a él desde un <main>, así que `build.sh` (estricto) falla en cuanto hay una guía.
        # Lo mismo con /blog/ (≈195 palabras y sin enlace contextual). Ver mejoras/05-pruebas-minimas.md.
        add_pieza(self.project, 'guias', 'mi-primera-guia')
        self.build_ok()
        self.check_ok(strict=True)

    def test_front_matter_incorrecto_detiene_el_build_con_mensaje_util(self):
        add_pieza(self.project, 'guias', 'guía-mala', topic='Inventado')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('front matter de Guías/Blog inválido', r.stderr)
        self.assertIn('guias/guía-mala/index.html', r.stderr, 'debe decir en qué archivo está el problema')
        self.assertIn('topic "Inventado"', r.stderr)
        self.assertNotIn('Traceback', r.stderr)


# --------------------------------------------------------------------------- 5. dominio y marcadores

class TestDominio(ProyectoTemporal):
    def test_por_defecto_usa_el_dominio_de_ejemplo(self):
        self.build_ok()
        todo = read_all(self.out)
        self.assertIn('https://TU-DOMINIO.com/', todo['index.html'])
        self.assertIn('https://TU-DOMINIO.com/sitemap.xml', todo['robots.txt'])

    def test_site_url_cambia_el_dominio_en_toda_la_salida(self):
        self.build_ok(site_url='https://ejemplo.es')
        todo = read_all(self.out)
        for ruta, texto in todo.items():
            self.assertNotIn('TU-DOMINIO', texto, f'{ruta} conserva el dominio por defecto')
        for ruta in ('index.html', 'precios/index.html', 'robots.txt', 'llms.txt', 'sitemap.xml'):
            self.assertIn('https://ejemplo.es', todo[ruta], f'{ruta} no usa el dominio nuevo')
        self.assertIn('<link rel="canonical" href="https://ejemplo.es/">', todo['index.html'].replace('"/>', '">'))
        self.assertIn('https://ejemplo.es/sitemap.xml', todo['robots.txt'])

    def test_con_dominio_nuevo_la_salida_pasa_el_validador(self):
        self.build_ok(site_url='https://ejemplo.es')
        self.check_ok(site_url='https://ejemplo.es')

    def test_dos_dominios_no_se_mezclan(self):
        self.build_ok(site_url='https://uno.es')
        self.assertFalse(any('dos.es' in t for t in read_all(self.out).values()))
        self.build_ok(site_url='https://dos.es')
        todo = read_all(self.out)
        self.assertFalse(any('uno.es' in t for t in todo.values()), 'el segundo build conserva restos del primero')
        self.assertTrue(any('dos.es' in t for t in todo.values()))

    def test_la_barra_final_se_quita(self):
        self.build_ok(site_url='https://ejemplo.es/')
        todo = read_all(self.out)
        self.assertNotIn('https://ejemplo.es//', ''.join(todo.values()))

    def test_dominio_invalido_aborta_con_mensaje_claro(self):
        for valor in ('http://ejemplo.es', 'ejemplo.es'):
            r = run_build(self.project, self.out, site_url=valor)
            self.assertNotEqual(r.returncode, 0, valor)
            self.assertIn('SITE_URL debe empezar por https://', r.stdout + r.stderr)
            self.assertNotIn('Traceback', r.stderr)

    def test_ninguna_pagina_fuente_lleva_el_dominio_escrito_a_mano(self):
        """Regresión de la fase 2: en src/ solo vale {{site_url}}."""
        for f in (REPO / 'src').rglob('*'):
            if f.is_file() and f.suffix in ('.html', '.json', '.txt', '.css'):
                self.assertNotIn('TU-DOMINIO', f.read_text(encoding='utf-8'), f.relative_to(REPO).as_posix())


class TestMarcadores(ProyectoTemporal):
    def test_marcador_suelto_en_una_pagina_detiene_el_build(self):
        pagina = self.project / 'src' / 'pages' / 'sobre-nosotros' / 'index.html'
        pagina.write_text(pagina.read_text(encoding='utf-8').replace('<h1', '<p>{{marcador_inventado}}</p>\n<h1', 1),
                          encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{{marcador_inventado}}', r.stderr + r.stdout)
        self.assertIn('textos.json', r.stderr + r.stdout)
        self.assertIn('sobre-nosotros', r.stderr + r.stdout, 'debe decir en qué página está')
        self.assertNotIn('Traceback', r.stderr)

    def test_marcador_resuelto_con_textos_json(self):
        pagina = self.project / 'src' / 'pages' / 'sobre-nosotros' / 'index.html'
        pagina.write_text(pagina.read_text(encoding='utf-8').replace('<h1', '<p>{{mi_marcador}}</p>\n<h1', 1),
                          encoding='utf-8')
        textos = self.project / 'src' / 'data' / 'textos.json'
        datos = json.loads(textos.read_text(encoding='utf-8'))
        datos['mi_marcador'] = 'Texto añadido desde textos.json'
        textos.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertIn('Texto añadido desde textos.json',
                      (self.out / 'sobre-nosotros' / 'index.html').read_text(encoding='utf-8'))

    def test_lo_calculado_de_entity_json_gana_a_textos_json(self):
        textos = self.project / 'src' / 'data' / 'textos.json'
        datos = json.loads(textos.read_text(encoding='utf-8'))
        datos['site_name'] = 'NOMBRE-DE-TEXTOS'
        textos.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertNotIn('NOMBRE-DE-TEXTOS', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_textos_json_roto_da_un_error_claro(self):
        (self.project / 'src' / 'data' / 'textos.json').write_text('{ esto no es json', encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('textos.json', r.stderr + r.stdout)
        self.assertNotIn('Traceback', r.stderr)

    def test_la_salida_no_contiene_marcadores(self):
        self.build_ok()
        for ruta, texto in read_all(self.out).items():
            self.assertNotIn('{{', texto, ruta)


# --------------------------------------------------------------------------- errores conocidos

class TestErroresConocidos(unittest.TestCase):
    """Fallos de minify_css encontrados al escribir estas pruebas.

    Están marcados como `expectedFailure`: documentan el problema sin romper la suite. Cuando se
    arregle uno, unittest avisará de «unexpected success» y habrá que quitar el decorador.
    Hoy la plantilla los evita (site.css los menciona en su cabecera), pero un cliente con CSS
    propio puede tropezar con ellos.
    """

    @unittest.expectedFailure
    def test_css_descendiente_tras_parentesis(self):
        # `a:not(.b) .c` (descendiente) se convierte en `a:not(.b).c` (mismo elemento): cambia el significado.
        self.assertEqual(build.minify_css('a:not(.b) .c{x:y}'), 'a:not(.b) .c{x:y}')

    @unittest.expectedFailure
    def test_css_var_dentro_de_calc(self):
        # Sale `calc(var( - - x)* 2)`: CSS inválido.
        self.assertEqual(build.minify_css('a{width:calc(var(--x) * 2)}'), 'a{width:calc(var(--x) * 2)}')

    @unittest.expectedFailure
    def test_css_numero_negativo_dentro_de_calc(self):
        # `calc(100% + -1px)` sale como `calc(100% + - 1px)`.
        self.assertEqual(build.minify_css('a{width:calc(100% + -1px)}'), 'a{width:calc(100% + -1px)}')

    @unittest.expectedFailure
    def test_css_cero_decimal_con_unidad(self):
        # `0.0px` sale como `.px`.
        self.assertEqual(build.minify_css('a{margin:0.0px}'), 'a{margin:0}')

    @unittest.expectedFailure
    def test_css_and_en_media_query(self):
        # `) and (` sale como `)and(`, que el navegador lee como una función `and()`.
        self.assertEqual(build.minify_css('@media (min-width:1px) and (max-width:2px){a{b:c}}'),
                         '@media(min-width:1px) and (max-width:2px){a{b:c}}')



if __name__ == '__main__':
    unittest.main()
