#!/usr/bin/env python3
import os, re, json, html, shutil, sys, subprocess
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
# Dominio del sitio: se define aquí o con la variable de entorno SITE_URL
# (SITE_URL=https://midominio.es ./legible/build.sh). El resto del proyecto usa {{site_url}}.
SITE_URL = os.environ.get('SITE_URL', 'https://TU-DOMINIO.com').strip().rstrip('/')
if not SITE_URL.startswith('https://'):
    sys.exit(f'✗ SITE_URL debe empezar por https:// (valor actual: {SITE_URL!r})')
OUT_DEFAULT = REPO / 'dist'

def _replace_placeholders_in_json(obj, replacements):
    """Recursively replace {{placeholder}} in string values of a JSON object."""
    if isinstance(obj, dict):
        return {k: _replace_placeholders_in_json(v, replacements) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_placeholders_in_json(item, replacements) for item in obj]
    elif isinstance(obj, str):
        result = obj
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result
    else:
        return obj

def menu_hrefs(header_html):
    """Enlaces internos del <nav> principal (cualquier nivel), leídos del partial."""
    nav = re.search(r'<nav\b.*?</nav>', header_html, flags=re.DOTALL)
    return re.findall(r'<a\b[^>]*\bhref="(/[^"]*)"', nav.group(0)) if nav else []

def parse_front_matter(text):
    if not text.startswith('---'):
        return {}, text
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.DOTALL)
    if not m:
        return {}, text
    block, content = m.group(1), m.group(2)
    data = {}
    for line in block.splitlines():
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        data[key.strip()] = val.strip()
    return data, content

def read_text(path):
    return Path(path).read_text(encoding='utf-8')

def write_text(path, text):
    Path(path).write_text(text, encoding='utf-8')

def url_from_rel(rel):
    if rel == '/':
        return SITE_URL + '/'
    return SITE_URL + rel

def compute_active(rel, front, hrefs):
    if 'active' in front:
        return front['active'], ''
    if rel in hrefs:
        return rel, 'page'
    # Página sin entrada propia en el menú: resalta el ancestro más profundo
    parents = [h for h in hrefs if h != '/' and rel.startswith(h)]
    if parents:
        return max(parents, key=len), 'true'
    return '', ''

def apply_active(header_html, active_href, aria_value):
    if not active_href:
        return header_html
    marked = []  # solo se marca el primer enlace que coincide (el menú puede repetir href)
    def repl(m):
        attrs = m.group(1)
        hm = re.search(r'\bhref="([^"]*)"', attrs)
        if not hm or hm.group(1) != active_href or marked:
            return m.group(0)
        marked.append(True)
        cm = re.search(r'\bclass="([^"]*)"', attrs)
        if cm:
            if 'active' not in cm.group(1).split():
                attrs = attrs.replace(cm.group(0), f'class="{(cm.group(1) + " active").strip()}"', 1)
        else:
            attrs += ' class="active"'
        if 'aria-current=' not in attrs:
            attrs += f' aria-current="{aria_value}"'
        return f'<a{attrs}>'
    # Solo enlaces del <nav> principal (la clase puede ir antes o despues del href)
    def nav_repl(nm):
        return re.sub(r'<a((?:\s+[a-zA-Z-]+="[^"]*")+)>', repl, nm.group(0))
    return re.sub(r'<nav\b.*?</nav>', nav_repl, header_html, flags=re.DOTALL)

def render_geo(flag):
    if flag is True or str(flag).lower() == 'true':
        return '<meta name="geo.region" content="ES-MD">\n    <meta name="geo.placename" content="Valdemoro">'
    return ''

def render_canonical(rel, canonical_mode):
    if canonical_mode == 'none':
        return ''
    return f'<link rel="canonical" href="{url_from_rel(rel)}">'

def render_og_url(rel, canonical_mode):
    if canonical_mode == 'none':
        return ''
    return f'<meta property="og:url" content="{url_from_rel(rel)}">'

def render_jsonld(page_json, entity_nodes):
    if page_json is None:
        return ''
    graph = []
    seen = set()
    for node in entity_nodes:
        nid = node.get('@id')
        if nid:
            seen.add(nid)
        graph.append(node)
    page_graph = page_json.get('@graph', [])
    if not page_graph and page_json.get('@type'):
        page_graph = [page_json]
    for node in page_graph:
        nid = node.get('@id')
        if nid in seen:
            return ''
        graph.append(node)
    out = {'@context': 'https://schema.org', '@graph': graph}
    return '<script type="application/ld+json">\n' + json.dumps(out, ensure_ascii=False, indent=4) + '\n</script>'

def check_unrendered(html_text, path):
    m = re.search(r'\{\{([^}]+)\}\}', html_text)
    if m:
        sys.exit(f'✗ BUILD FAILED: el marcador {m.group(0)} (en la página {path}) no tiene valor. '
                 f'Añade "{m.group(1)}" a src/data/textos.json o escríbelo directamente en la página.')

def compose_page(front, content, layout_text, header_text, footer_text, entity_nodes, page_rel, site_name='{{site_name}}', site_url='{{site_url}}', contact_email='{{contact_email}}', whatsapp_link='{{whatsapp_link}}', service_category_1='{{service_category_1}}', service_category_2='{{service_category_2}}', location='{{location}}', target_audience='{{target_audience}}', featured_action_name='{{featured_action_name}}', jsonld_replacements=None):
    # Reemplazar placeholders en title y description del front matter
    title_raw = front.get('title', '')
    description_raw = front.get('description', '')
    if jsonld_replacements:
        for placeholder, value in jsonld_replacements.items():
            title_raw = title_raw.replace(placeholder, value)
            description_raw = description_raw.replace(placeholder, value)
    title = html.escape(title_raw, quote=True)
    description = html.escape(description_raw, quote=True)
    robots = html.escape(front.get('robots', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'), quote=True)
    geo_flag = front.get('geo', 'true')
    canonical_mode = front.get('canonical', 'auto')
    active_href, aria_value = compute_active(page_rel, front, menu_hrefs(header_text))
    header_text = apply_active(header_text, active_href, aria_value)
    geo = render_geo(geo_flag)
    canonical = render_canonical(page_rel, canonical_mode)
    og_url = render_og_url(page_rel, canonical_mode)
    page_json = None
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
    if m:
        jsonld_str = m.group(1).strip()
        # Reemplazar placeholders en el JSON-LD de la página antes de parsear
        if jsonld_replacements:
            for placeholder, value in jsonld_replacements.items():
                jsonld_str = jsonld_str.replace(placeholder, value)
        try:
            page_json = json.loads(jsonld_str)
        except Exception as e:
            raise ValueError(f'JSON-LD parse error: {e}')
        content = content[:m.start()] + content[m.end():]
        content = content.strip()
    jsonld = render_jsonld(page_json, entity_nodes)
    page = layout_text
    page = page.replace('{{title}}', title)
    page = page.replace('{{description}}', description)
    page = page.replace('{{robots}}', robots)
    page = page.replace('{{geo}}', geo)
    page = page.replace('{{canonical}}', canonical)
    page = page.replace('{{og_url}}', og_url)
    page = page.replace('{{jsonld}}', jsonld)
    page = page.replace('{{header}}', header_text)
    page = page.replace('{{content}}', content)
    page = page.replace('{{footer}}', footer_text)
    page = page.replace('{{site_name}}', site_name)
    page = page.replace('{{site_url}}', site_url)
    page = page.replace('{{contact_email}}', contact_email)
    page = page.replace('{{whatsapp_link}}', whatsapp_link)
    page = page.replace('{{service_category_1}}', service_category_1)
    page = page.replace('{{service_category_2}}', service_category_2)
    page = page.replace('{{location}}', location)
    page = page.replace('{{target_audience}}', target_audience)
    page = page.replace('{{featured_action_name}}', featured_action_name)
    check_unrendered(page, page_rel)
    return page

def minify_css(css_text: str) -> str:
    css = css_text

    # 1) Comentarios
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)

    # 2) Proteger strings para que el resto de reglas no altere su contenido
    strings = []
    def protect_string(m):
        strings.append(m.group(0))
        return f'__STR_{len(strings)-1}__'
    css = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', protect_string, css)

    # 3) Espaciado básico
    css = re.sub(r'\s+', ' ', css)
    css = css.replace(' }', '}').replace(' {', '{').replace(': ', ':').replace(' ;', ';')
    css = re.sub(r';\s*}', '}', css)

    # 4) Proteger funciones matemáticas
    placeholders = {}
    def extract_math(match):
        idx = len(placeholders)
        key = f'__MATH_{idx}__'
        func = match.group(1)
        inner = match.group(2)
        inner = re.sub(r'\s+', ' ', inner)
        inner = re.sub(r'\s*([,()])\s*', r'\1', inner)
        inner = re.sub(r'\s*([+-])\s*', r' \1 ', inner)
        inner = re.sub(r'\s{2,}', ' ', inner).strip()
        placeholders[key] = f'{func}({inner})'
        return key
    pattern = r'\b(calc|min|max|clamp)\(([^()]*(?:\([^()]*\)[^()]*)*)\)'
    while re.search(pattern, css):
        css = re.sub(pattern, extract_math, css)

    # 5) 0 con unidad -> 0
    css = re.sub(
        r'(?<![\d.])0(?:px|em|rem|vh|vw|cm|mm|in|pt|pc|ex|ch|vmin|vmax)\b',
        '0', css, flags=re.IGNORECASE
    )

    # 6) Cero a la izquierda: 0.5 -> .5
    css = re.sub(r'(?<![\w.])0+\.(?=\d)', '.', css)

    # 7) Ceros a la derecha: 1.0 -> 1, 1.50 -> 1.5, .50 -> .5
    css = re.sub(r'(\d)\.0+(?=\D|$)', r'\1', css)
    css = re.sub(r'((?:\d+)?\.\d*?)0+(?=\D|$)', r'\1', css)
    css = re.sub(r'(?<![\w.])\.(?![\d\w])', '0', css)  # seguro: '.' huérfano -> 0

    # 8) Colores hex cortos: #AABBCC -> #ABC, #AABBCCDD -> #ABCD
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3(?![0-9a-fA-F])',
        r'#\1\2\3', css
    )
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3([0-9a-fA-F])\4(?![0-9a-fA-F])',
        r'#\1\2\3\4', css
    )

    # 9) !important compacto
    css = re.sub(r'\s*!\s*important\b', '!important', css)

    # 10) Espaciado alrededor de puntuación restante
    css = re.sub(r'\s*([{}:;,>~()\[\]])\s*', r'\1', css)
    css = re.sub(r'\s*\+\s*', '+', css)

    # 11) Restaurar funciones matemáticas
    for key, val in placeholders.items():
        css = css.replace(key, val)

    # 12) Restaurar strings
    for i, s in enumerate(strings):
        css = css.replace(f'__STR_{i}__', s)

    # 13) Limpieza final
    css = re.sub(r';;+', ';', css)
    css = css.strip()
    return css

# Elementos en línea: el espacio entre dos de ellos forma parte del texto visible.
INLINE_TAGS = frozenset('a abbr b bdi bdo br button cite code data del dfn em i img input ins kbd label mark q s '
                        'samp small span strong sub sup svg time u var wbr'.split())

VOID_INLINE_TAGS = frozenset(['br', 'img', 'input', 'wbr'])

def minify_html(html_text: str) -> str:
    protected = []

    def is_ld_json(tag_text: str) -> bool:
        return bool(
            re.match(r'<script[^>]*>', tag_text, re.IGNORECASE)
            and re.search(r'type\s*=\s*["\']application/ld\+json["\']', tag_text, re.IGNORECASE)
        )

    def protect(pattern, flags=0, json_checker=None):
        def replacer(m):
            idx = len(protected)
            original = m.group(0)
            is_json = bool(json_checker and json_checker(original))
            protected.append((original, is_json))
            # \x00 no aparece en HTML normal: colisión prácticamente imposible
            return f'\x00P{idx}\x00'
        return re.sub(pattern, replacer, html_text, flags=flags)

    # 1) Proteger bloques sensibles (scripts, estilos, pre, textarea)
    html_text = protect(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE, is_ld_json)
    html_text = protect(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<pre[^>]*>.*?</pre>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<textarea[^>]*>.*?</textarea>', re.DOTALL | re.IGNORECASE)

    # 2) Comentarios
    html_text = re.sub(r'<!--[\s\S]*?-->', '', html_text)

    # 3) Proteger valores de atributos entre comillas ANTES de colapsar espacios
    #    Esto corrige el bug: alt="a  b", content="x   y", title="z  w" quedan intactos.
    attr_strings = []
    def protect_attr(m):
        attr_strings.append(m.group(0))
        return f'\x00A{len(attr_strings)-1}\x00'
    html_text = re.sub(r'="[^"]*"|=\'[^\']*\'', protect_attr, html_text)

    # 4) Colapsar espacios entre tags. Entre dos elementos en línea hermanos
    #    (<strong>a</strong> <small>b</small>) el espacio se ve en pantalla: se conserva uno solo
    #    (\x01 temporal). Entre bloques, o entre un contenedor y su contenido, se quita.
    html_text = re.sub(
        r'(<(/?)([a-zA-Z][\w-]*)[^<>]*>)\s+(?=<(/?)([a-zA-Z][\w-]*))',
        lambda m: m.group(1) + ('\x01' if (m.group(3).lower() in INLINE_TAGS and m.group(5).lower() in INLINE_TAGS
                                           and not m.group(4)
                                           and (m.group(2) or m.group(3).lower() in VOID_INLINE_TAGS)) else ''),
        html_text)
    html_text = re.sub(r'>\s+<', '><', html_text)
    html_text = html_text.replace('\x01', ' ')

    # 5) Colapsar espacios múltiples (ahora sí: solo espacios estructurales entre atributos)
    html_text = re.sub(r'\s{2,}', ' ', html_text)

    # 6) Limpiar espacios antes de > (sin tocar /> de autocierre)
    html_text = re.sub(r'\s+>', '>', html_text)

    html_text = html_text.strip()

    # 7) Restaurar valores de atributos
    for i, s in enumerate(attr_strings):
        html_text = html_text.replace(f'\x00A{i}\x00', s)

    # 8) Restaurar bloques protegidos (con minify de JSON-LD)
    for i, (original, is_json) in enumerate(protected):
        if is_json:
            match = re.match(r'<script[^>]*>(.*?)</script>', original, re.DOTALL | re.IGNORECASE)
            if match:
                inner = match.group(1)
                try:
                    parsed = json.loads(inner)
                    minified_inner = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                    gt_pos = original.find('>')
                    close_pos = original.rfind('</script>')
                    if gt_pos != -1 and close_pos != -1:
                        new_tag = original[:gt_pos + 1] + minified_inner + original[close_pos:]
                    else:
                        new_tag = original
                except Exception:
                    new_tag = original
            else:
                new_tag = original
            html_text = html_text.replace(f'\x00P{i}\x00', new_tag)
        else:
            html_text = html_text.replace(f'\x00P{i}\x00', original)

    return html_text

# --------------------------------------------------------------------------- colecciones (Guías y Blog)

COLLECTION_DIRS = {'guias': 'guia', 'blog': 'articulo'}
COLLECTION_TOPICS = ['Tema 1', 'Tema 2', 'Tema 3', 'Tema 4', 'Tema 5']
BLOG_MIN_VISIBLE = 3
MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
            'septiembre', 'octubre', 'noviembre', 'diciembre']
WHATSAPP_LINK = 'https://wa.me/TU-TELEFONO-E164?text=Hola%2C%20me%20interesa%20sus%20servicios.%20Mi%20negocio%20es%3A'

class CollectionError(Exception):
    """Front matter de colección incompleto o inválido (el build se detiene con el detalle completo)."""

def iso_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None

def fecha_larga(iso):
    d = iso_date(iso)
    return f'{d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def load_collections(pages_dir):
    """Lee y valida las piezas de src/pages/guias/*/ y src/pages/blog/*/.

    Devuelve {'guias': [...], 'blog': [...]}; cada pieza es un dict con rel, slug, path, front y los
    campos de colección ya normalizados. Lanza CollectionError con TODOS los problemas encontrados.
    """
    pages_dir = Path(pages_dir)
    problems = []
    pieces = {'guias': [], 'blog': []}
    for coll, expected_type in COLLECTION_DIRS.items():
        base = pages_dir / coll
        if not base.is_dir():
            continue
        for f in sorted(base.rglob('*.html')):
            rel_f = f.relative_to(pages_dir).as_posix()
            parts = f.relative_to(base).parts
            if len(parts) != 2 or parts[1] != 'index.html':
                if parts == ('index.html',):
                    problems.append(f'{rel_f}: el índice /{coll}/ se genera solo; borra este archivo.')
                else:
                    problems.append(f'{rel_f}: las piezas de {coll} deben ser {coll}/<slug>/index.html.')
                continue
            front, _ = parse_front_matter(read_text(f))
            where = f'{rel_f}'
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', parts[0]):
                problems.append(f'{where}: el slug "{parts[0]}" debe ir en minúsculas, sin tildes y con guiones.')
            for key in ('type', 'topic', 'published', 'updated', 'summary', 'service'):
                if not front.get(key):
                    problems.append(f'{where}: falta "{key}" en el front matter.')
            if front.get('type') and front['type'] != expected_type:
                problems.append(f'{where}: type "{front["type"]}" no vale en {coll}/ (se esperaba "{expected_type}").')
            if front.get('topic') and front['topic'] not in COLLECTION_TOPICS:
                problems.append(f'{where}: topic "{front["topic"]}" no está en la taxonomía ({" · ".join(COLLECTION_TOPICS)}).')
            pub, upd = iso_date(front.get('published')), iso_date(front.get('updated'))
            if front.get('published') and pub is None:
                problems.append(f'{where}: published "{front["published"]}" no es una fecha ISO (AAAA-MM-DD).')
            if front.get('updated') and upd is None:
                problems.append(f'{where}: updated "{front["updated"]}" no es una fecha ISO (AAAA-MM-DD).')
            if pub and upd and upd < pub:
                problems.append(f'{where}: updated ({front["updated"]}) es anterior a published ({front["published"]}).')
            svc = front.get('service')
            if svc:
                if not (svc.startswith('/') and svc.endswith('/')) or not (pages_dir / svc.strip('/') / 'index.html').is_file():
                    problems.append(f'{where}: service "{svc}" no apunta a una página existente.')
            if 'title' not in front or 'description' not in front:
                problems.append(f'{where}: falta title o description.')
            rel = f'/{coll}/{parts[0]}/'
            related = [r.strip() for r in front.get('related', '').split(',') if r.strip()]
            pieces[coll].append({
                'coll': coll, 'slug': parts[0], 'rel': rel, 'path': f, 'front': front,
                'title': front.get('title', ''), 'topic': front.get('topic', ''),
                'published': front.get('published', ''), 'updated': front.get('updated', ''),
                'summary': front.get('summary', ''), 'service': svc or '', 'related': related,
            })
    known = {p['rel'] for lst in pieces.values() for p in lst}
    for lst in pieces.values():
        for p in lst:
            where = p['path'].relative_to(pages_dir).as_posix()
            if len(p['related']) > 2:
                problems.append(f'{where}: related admite como máximo 2 enlaces y tiene {len(p["related"])}.')
            for r in p['related']:
                if r == p['rel']:
                    problems.append(f'{where}: related no puede apuntar a la propia pieza.')
                elif r not in known:
                    problems.append(f'{where}: related "{r}" no es una guía ni un artículo existente.')
    # `type` de colección fuera de su carpeta
    for f in sorted(pages_dir.rglob('*.html')):
        top = f.relative_to(pages_dir).parts[0]
        if top in COLLECTION_DIRS:
            continue
        front, _ = parse_front_matter(read_text(f))
        if front.get('type') in COLLECTION_DIRS.values():
            problems.append(f'{f.relative_to(pages_dir).as_posix()}: type "{front["type"]}" solo se admite dentro de guias/ o blog/.')
    if problems:
        raise CollectionError('\n'.join('  - ' + m for m in problems))
    return pieces

def blog_state(articulos):
    """'none' (0 artículos: sin /blog/), 'hidden' (1-2: /blog/ noindex y sin anunciar) o 'visible' (>= 3)."""
    n = len(articulos)
    if n == 0:
        return 'none'
    return 'visible' if n >= BLOG_MIN_VISIBLE else 'hidden'

def blog_visible(articulos):
    """True si el Blog se anuncia (menú, pie, sitemap, llms.txt) y es indexable."""
    return blog_state(articulos) == 'visible'

def _breadcrumb_html(label):
    home = ('<a href="/"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
            '<path d="M9 22V12h6v10"/></svg>Inicio</a>')
    return (f'<nav class="breadcrumb" aria-label="Migas de pan"><ol><li>{home}</li>'
            f'<li><span>{html.escape(label)}</span></li></ol></nav>')

def _lead_strip_html():
    return f"""<section class="lead-strip page-width">
            <div>
                <p class="eyebrow">Siguiente paso</p>
                <h2>¿No sabes por dónde empezar?</h2>
                <p class="lead mt-18">Pide tu <a href="/accion-destacada/">consulta inicial</a>: te decimos qué tiene sentido para tu negocio.</p>
            </div>
            <div class="lead-strip-inner">
                <a class="button primary" href="/accion-destacada/">Solicitar consulta</a>
                <span class="text-muted-lg mt-15">o escríbenos a <a href="mailto:{{{{contact_email}}}}" class="link-accent">{{{{contact_email}}}}</a> o por <a href="{{{{whatsapp_link}}}}" target="_blank" rel="noopener noreferrer" class="link-accent">WhatsApp</a>.</span>
            </div>
        </section>"""

def _index_jsonld(rel, title, description, label, last_mod, items):
    url = SITE_URL + rel
    graph = [
        {
            '@type': 'CollectionPage', '@id': url + '#webpage', 'url': url, 'name': title,
            'description': description, 'inLanguage': 'es-ES',
            'isPartOf': {'@id': SITE_URL + '/#website'}, 'about': {'@id': SITE_URL + '/#business'},
            'dateModified': last_mod, 'breadcrumb': {'@id': url + '#breadcrumb'},
            'mainEntity': {
                '@type': 'ItemList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': i, 'url': SITE_URL + p['rel'], 'name': p['title'].split(' | ')[0]}
                    for i, p in enumerate(items, 1)
                ],
            },
        },
        {
            '@type': 'BreadcrumbList', '@id': url + '#breadcrumb',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': SITE_URL + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': label},
            ],
        },
    ]
    data = {'@context': 'https://schema.org', '@graph': graph}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=4) + '\n</script>'

def _card_html(p, link_text, with_date):
    title = html.escape(p['title'].split(' | ')[0], quote=True)
    date = (f'<time class="post-meta" datetime="{p["published"]}">{fecha_larga(p["published"])}</time>'
            if with_date else '')
    return f"""<article>
                    <span class="chip">{html.escape(p['topic'])}</span>
                    {date}
                    <h3>{title}</h3>
                    <p>{html.escape(p['summary'])}</p>
                    <a href="{p['rel']}" aria-label="{link_text}: {title}">{link_text}</a>
                </article>"""

def render_guias_index(guias):
    """(front, content) del índice /guias/: tarjetas agrupadas por tema (orden de COLLECTION_TOPICS)."""
    title = 'Guías para tu negocio'
    description = ('Guías paso a paso para resolver dudas concretas de tu negocio. Sin trucos ni promesas.')
    last_mod = max(p['updated'] for p in guias)
    sections = []
    n = 0
    for topic in COLLECTION_TOPICS:
        group = sorted((p for p in guias if p['topic'] == topic), key=lambda p: (p['published'], p['slug']))
        if not group:
            continue
        n += 1
        cards = '\n                '.join(_card_html(p, 'Leer la guía', False) for p in group)
        sections.append(f"""        <section class="section page-width" aria-labelledby="guias-tema-{n}">
            <h2 id="guias-tema-{n}">{html.escape(topic)}</h2>
            <div class="service-grid">
                {cards}
            </div>
        </section>""")
    ordered = [p for topic in COLLECTION_TOPICS for p in sorted((q for q in guias if q['topic'] == topic), key=lambda q: (q['published'], q['slug']))]
    content = f"""{_index_jsonld('/guias/', title, description, 'Guías', last_mod, ordered)}

<main id="main">
        <section class="inner-hero page-width">
            {_breadcrumb_html('Guías')}
            <p class="eyebrow">Guías</p>
            <h1>Guías para resolver dudas de tu negocio</h1>
            <p class="lead">Explicaciones paso a paso para resolver una duda concreta. Puedes aplicarlas tú mismo; si prefieres que lo hagamos nosotros, cada guía te lleva al servicio que lo resuelve.</p>
            <p class="mt-18">Cada guía cuenta qué hacer, en qué orden y qué no funciona. Ninguna promete resultados garantizados: eso depende de muchos factores. Llevan la fecha de su última revisión para que sepas si siguen vigentes.</p>
        </section>

{chr(10).join(sections)}

        {_lead_strip_html()}
    </main>"""
    front = {'title': title, 'description': description, 'canonical': 'auto', 'geo': 'true'}
    return front, content

def render_blog_index(articulos, guias_exist):
    """(front, content) del índice /blog/: cronológico inverso. Con 1-2 artículos sale noindex, follow."""
    title = 'Artículos y novedades'
    description = ('Artículos con fecha sobre temas relevantes para tu negocio: análisis y opinión, sin promesas.')
    ordered = sorted(articulos, key=lambda p: (p['published'], p['updated'], p['slug']), reverse=True)
    last_mod = max(p['updated'] for p in articulos)
    cards = '\n                '.join(_card_html(p, 'Leer el artículo', True) for p in ordered)
    guias_txt = ('mira las <a href="/guias/">guías</a>' if guias_exist else 'mira las guías')
    content = f"""{_index_jsonld('/blog/', title, description, 'Blog', last_mod, ordered)}

<main id="main">
        <section class="inner-hero page-width">
            {_breadcrumb_html('Blog')}
            <p class="eyebrow">Blog</p>
            <h1>Artículos y novedades</h1>
            <p class="lead">Artículos con fecha en los que analizamos cuestiones concretas para tu negocio. Son análisis y opinión con criterio; si lo que buscas son los pasos para hacer algo, {guias_txt}.</p>
            <p class="mt-18">Los artículos llevan su fecha porque lo que cuentan puede quedarse viejo. Fíate de la de publicación, y ten en cuenta que las herramientas y plataformas cambian a menudo. Aquí no vas a encontrar notas de prensa ni promesas. Si algo de lo que leas no encaja con tu caso, escríbenos y lo miramos.</p>
        </section>

        <section class="section page-width" aria-labelledby="blog-lista">
            <h2 id="blog-lista">Últimos artículos</h2>
            <div class="service-grid">
                {cards}
            </div>
        </section>

        {_lead_strip_html()}
    </main>"""
    front = {'title': title, 'description': description, 'canonical': 'auto', 'geo': 'true'}
    if blog_state(articulos) != 'visible':
        front['robots'] = 'noindex, follow'
    return front, content


# --------------------------------------------------------------------------- sitemap y llms.txt generados

# Orden histórico del sitemap (F3). Las páginas nuevas se añaden después: /guias/ + guías, /blog/ + artículos.
SITEMAP_BASE_ORDER = [
    '/', '/servicios/', '/servicios/servicio-generico/', '/precios/', '/sobre-nosotros/',
    '/contacto/', '/accion-destacada/',
]

def page_date_modified(out_path, front):
    """lastmod de una página: dateModified del JSON-LD compilado (el más reciente de sus nodos) o `updated`."""
    text = read_text(out_path)
    dates = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        for node in data.get('@graph') or [data]:
            if isinstance(node, dict) and iso_date(node.get('dateModified')):
                dates.append(node['dateModified'])
    if dates:
        return max(dates)
    if iso_date(front.get('updated')):
        return front['updated']
    return None

def build_sitemap(pages_data, collections, out):
    """Escribe out/sitemap.xml con las páginas indexables (no 404, no noindex)."""
    entries = {}
    for rel, front, out_path in pages_data:
        robots = re.search(r'<meta name="robots" content="([^"]*)"', read_text(out_path))
        if rel == '/404.html' or (robots and 'noindex' in robots.group(1).lower()):
            continue
        lm = page_date_modified(out_path, front)
        if lm is None:
            raise ValueError(f'{rel}: sin dateModified en el JSON-LD ni "updated" en el front matter; añade "updated: AAAA-MM-DD".')
        entries[rel] = lm
    order = [r for r in SITEMAP_BASE_ORDER if r in entries]
    for coll in ('guias', 'blog'):
        idx = f'/{coll}/'
        if idx in entries:
            order.append(idx)
        order.extend(p['rel'] for p in _ordered_pieces(coll, collections[coll]) if p['rel'] in entries)
    order.extend(sorted(r for r in entries if r not in order))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in order:
        lines += ['    <url>', f'        <loc>{SITE_URL}{rel}</loc>', f'        <lastmod>{entries[rel]}</lastmod>', '    </url>']
    lines.append('</urlset>')
    (Path(out) / 'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return order

def _ordered_pieces(coll, pieces):
    if coll == 'guias':
        return [p for t in COLLECTION_TOPICS for p in sorted((q for q in pieces if q['topic'] == t), key=lambda q: (q['published'], q['slug']))]
    return sorted(pieces, key=lambda p: (p['published'], p['updated'], p['slug']), reverse=True)

def _piece_name(p):
    return p['title'].split(' | ')[0]

def render_llms_guias(guias):
    if not guias:
        return ''
    lines = ['## Guías', '',
             f'- [/guias/]({SITE_URL}/guias/): Guías paso a paso para tu negocio, agrupadas por tema.']
    lines += [f'- [{_piece_name(p)}]({SITE_URL}{p["rel"]}): {p["summary"]}' for p in _ordered_pieces('guias', guias)]
    return '\n'.join(lines) + '\n\n'

def render_llms_blog(articulos):
    if not blog_visible(articulos):
        return ''
    lines = ['## Blog', '',
             f'- [/blog/]({SITE_URL}/blog/): Artículos con fecha sobre temas de tu negocio.']
    lines += [f'- [{_piece_name(p)}]({SITE_URL}{p["rel"]}) ({p["published"]}): {p["summary"]}' for p in _ordered_pieces('blog', articulos)]
    return '\n'.join(lines) + '\n\n'

def render_llms_sitemap_extra(order):
    """URLs de guías y blog en la sección «Sitemap» de llms.txt (las mismas que salen en sitemap.xml)."""
    return ''.join(f'- {SITE_URL}{rel}\n' for rel in order if rel.startswith(('/guias/', '/blog/')))

def render_llms(text, collections, sitemap_order=()):
    text = text.replace('{{llms_sitemap_extra}}', render_llms_sitemap_extra(sitemap_order))
    text = text.replace('{{llms_guias}}', render_llms_guias(collections['guias']))
    text = text.replace('{{llms_blog}}', render_llms_blog(collections['blog']))
    m = re.search(r'\{\{[^}]+\}\}', text)
    if m:
        raise ValueError(f'marcador sin resolver {m.group(0)} en llms.txt')
    return text

def print_report(success, errors, warnings, generated, total_bytes, out, minify,
                 git_branch, git_commit, build_time,
                 total_html_before, total_html_after, css_size_before, css_size_after):
    COL = 50
    LBL = 15
    W = 2 + LBL + 2 + COL  # interior width
    BANNER = 'legible  •  Generador de webs estáticas'

    def hr(): print('╠' + '═' * W + '╣')
    def row(label, value): print(f'║  {label:<{LBL}}: {str(value):<{COL}}║')
    def centered(text): print(f'║{text.center(W)}║')
    def empty(): print(f'║{" " * W}║')

    print('╔' + '═' * W + '╗')
    empty()
    centered(BANNER)
    empty()
    hr()

    if success:
        centered('✓  BUILD SUCCESS')
    else:
        centered('✗  BUILD FAILED')
    hr()

    centered('BUILD REPORT')
    hr()

    status = '✓  SUCCESS' if success else '✗  FAILED'
    row('Status', status)
    row('Branch', git_branch)
    row('Commit', git_commit)
    row('Build Time', build_time)
    row('Pages Generated', str(generated))
    row('Total Size', f'{total_bytes:,} bytes')
    row('Output Dir', str(out))
    row('Minify', str(minify))

    if success:
        hr()
        centered('SIZE BREAKDOWN')
        hr()
        html_saved = total_html_before - total_html_after
        html_pct = f'{(html_saved/total_html_before*100):.1f}%' if total_html_before else '0%'
        row('HTML Before', f'{total_html_before:,} bytes')
        row('HTML After', f'{total_html_after:,} bytes')
        row('HTML Saved', f'{html_saved:,} bytes ({html_pct})')
        css_saved = css_size_before - css_size_after
        css_pct = f'{(css_saved/css_size_before*100):.1f}%' if css_size_before else '0%'
        row('CSS Before', f'{css_size_before:,} bytes')
        row('CSS After', f'{css_size_after:,} bytes')
        row('CSS Saved', f'{css_saved:,} bytes ({css_pct})')
        total_before = total_html_before + css_size_before
        total_after = total_html_after + css_size_after
        total_saved = total_before - total_after
        total_pct = f'{(total_saved/total_before*100):.1f}%' if total_before else '0%'
        row('TOTAL Before', f'{total_before:,} bytes')
        row('TOTAL After', f'{total_after:,} bytes')
        row('TOTAL Saved', f'{total_saved:,} bytes ({total_pct})')

    hr()

    if warnings:
        centered('⚠  Warnings')
        for p, msg in warnings:
            line = f'• {p} → {msg}'[:60]
            print(f'║  {line:<{W-2}}║')
    elif success:
        centered('✓  No warnings')
    else:
        centered('✗  Errors')
        for p, msg in errors:
            line = f'• {p} → {msg}'[:60]
            print(f'║  {line:<{W-2}}║')

    empty()
    if success:
        centered('Site ready for deployment')
    else:
        centered('Build aborted — fix errors above')
    empty()
    print('╚' + '═' * W + '╝')

def get_git_info():
    git_branch = os.environ.get('RENDER_GIT_BRANCH')
    git_commit = os.environ.get('RENDER_GIT_COMMIT')
    if not git_branch:
        try:
            git_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=REPO, text=True, stderr=subprocess.DEVNULL).strip()
            if git_branch == 'HEAD':
                git_branch = None
        except Exception:
            pass
    if not git_branch:
        git_branch = 'unknown'
    if not git_commit:
        try:
            git_commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            git_commit = 'unknown'
    else:
        git_commit = git_commit[:7]
    return git_branch, git_commit


def check_out_dir(out):
    """Aborta si la carpeta de salida pondría en riesgo el proyecto (el build la vacía entera)."""
    out = Path(out).resolve()
    protegidas = [REPO / 'src', REPO / 'legible']
    en_riesgo = (
        out == REPO or out in REPO.parents
        or any(out == p or p in out.parents for p in protegidas)
        or any((out / p.name).exists() for p in protegidas)
    )
    if en_riesgo:
        print(f'✗ BUILD ABORTADO: la carpeta de salida {out} es el proyecto, src/, legible/ o contiene alguno de ellos, '
              'y se vaciaría. Usa una carpeta propia, como dist/.', file=sys.stderr)
        raise SystemExit(1)

def build(out_dir=None, minify=None, no_validate=False):
    git_branch, git_commit = get_git_info()
    build_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out = Path(out_dir or OUT_DEFAULT)
    check_out_dir(out)
    if out.exists():
        for p in out.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    static_src = REPO / 'src' / 'static'
    for p in static_src.rglob('*'):
        if p.is_file():
            target = out / p.relative_to(static_src)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
    css_src = REPO / 'src' / 'css' / 'site.css'
    css_dst = out / 'css' / 'site.css'
    css_dst.parent.mkdir(parents=True, exist_ok=True)
    css_text = css_src.read_text(encoding='utf-8')
    css_size_before = len(css_text.encode('utf-8'))
    if minify:
        css_text = minify_css(css_text)
    css_size_after = len(css_text.encode('utf-8'))
    css_dst.write_text(css_text, encoding='utf-8')

    def _unwrap_placeholder(val, default):
        """Si val es un placeholder {{...}}, devuelve default; si no, devuelve val."""
        if isinstance(val, str) and val.startswith('{{') and val.endswith('}}'):
            return default
        return val

    layout = read_text(REPO / 'src' / 'layout.html')
    header = read_text(REPO / 'src' / 'partials' / 'header.html')
    footer = read_text(REPO / 'src' / 'partials' / 'footer.html')
    entity = json.loads(read_text(REPO / 'src' / 'data' / 'entity.json'))
    # Extraer valores de entity.json para placeholders globales
    business = next((n for n in entity if n.get('@type') == 'ProfessionalService'), {})
    site_name = _unwrap_placeholder(business.get('name'), 'Tu Negocio')
    site_url = SITE_URL
    contact_email = _unwrap_placeholder(business.get('email'), 'contacto@tu-negocio.com')
    whatsapp_link = _unwrap_placeholder(business.get('contactPoint', {}).get('telephone'), '+34600000000')
    if whatsapp_link.startswith('+'):
        whatsapp_link = 'https://wa.me/' + whatsapp_link[1:] + '?text=Hola%2C%20me%20interesa%20sus%20servicios.%20Mi%20negocio%20es%3A'
    elif not whatsapp_link.startswith('http'):
        whatsapp_link = 'https://wa.me/' + whatsapp_link + '?text=Hola%2C%20me%20interesa%20sus%20servicios.%20Mi%20negocio%20es%3A'
    # Valores adicionales para footer
    address = business.get('address', {})
    city = _unwrap_placeholder(address.get('addressLocality'), 'Tu Ciudad')
    region = _unwrap_placeholder(address.get('addressRegion'), 'Tu Provincia')
    location = f"{city}, {region}"
    knows_about = business.get('knowsAbout', [])
    service_category_1 = _unwrap_placeholder(knows_about[0] if len(knows_about) > 0 else '{{service_category_1}}', 'Servicio 1')
    service_category_2 = _unwrap_placeholder(knows_about[1] if len(knows_about) > 1 else '{{service_category_2}}', 'Servicio 2')
    area_served = business.get('areaServed', [])
    target_audience = 'negocios de ' + ', '.join([c.get('name', '') for c in area_served[:3]]) if area_served else '{{target_audience}}'
    # Extraer nombres de ciudades de areaServed para placeholders city_1, city_2, etc.
    city_1 = _unwrap_placeholder(area_served[0].get('name') if len(area_served) > 0 else '{{city_1}}', 'Ciudad 1')
    city_2 = _unwrap_placeholder(area_served[1].get('name') if len(area_served) > 1 else '{{city_2}}', 'Ciudad 2')
    city_3 = _unwrap_placeholder(area_served[2].get('name') if len(area_served) > 2 else '{{city_3}}', 'Ciudad 3')
    city_4 = _unwrap_placeholder(area_served[3].get('name') if len(area_served) > 3 else '{{city_4}}', 'Ciudad 4')
    # Extraer featured_action_name de las ofertas (la que tiene price 0)
    featured_action_name = '{{featured_action_name}}'
    offers = business.get('hasOfferCatalog', {}).get('itemListElement', [])
    for offer in offers:
        if offer.get('price') == '0' or offer.get('price') == 0:
            featured_action_name = _unwrap_placeholder(offer.get('name'), 'Acción Destacada')
            break
    try:
        collections = load_collections(REPO / 'src' / 'pages')
    except CollectionError as e:
        print('✗ BUILD FAILED: front matter de Guías/Blog inválido\n' + str(e), file=sys.stderr)
        raise SystemExit(1)

    # Procesar entity nodes para reemplazar placeholders
    derived = {
        '{{site_name}}': site_name,
        '{{site_url}}': site_url,
        '{{contact_email}}': contact_email,
        '{{whatsapp_link}}': whatsapp_link,
        '{{phone_e164}}': _unwrap_placeholder(business.get('contactPoint', {}).get('telephone'), '+34600000000'),
        '{{city}}': city,
        '{{region}}': region,
        '{{location}}': location,
        '{{city_1}}': city_1,
        '{{city_2}}': city_2,
        '{{city_3}}': city_3,
        '{{city_4}}': city_4,
        '{{service_category_1}}': service_category_1,
        '{{service_category_2}}': service_category_2,
        '{{service_category_3}}': _unwrap_placeholder(knows_about[2] if len(knows_about) > 2 else '{{service_category_3}}', 'Servicio 3'),
        '{{service_category_4}}': _unwrap_placeholder(knows_about[3] if len(knows_about) > 3 else '{{service_category_4}}', 'Servicio 4'),
        '{{service_category_5}}': _unwrap_placeholder(knows_about[4] if len(knows_about) > 4 else '{{service_category_5}}', 'Servicio 5'),
        '{{service_category_6}}': _unwrap_placeholder(knows_about[5] if len(knows_about) > 5 else '{{service_category_6}}', 'Servicio 6'),
        '{{price_range}}': _unwrap_placeholder(business.get('priceRange'), '0 € - 999 €/mes'),
        '{{featured_action_name}}': featured_action_name,
        '{{service_1_name}}': _unwrap_placeholder(offers[0].get('name') if len(offers) > 0 else '{{service_1_name}}', 'Servicio 1'),
        '{{service_1_price}}': _unwrap_placeholder(str(offers[0].get('price')) if len(offers) > 0 else '{{service_1_price}}', '99 €'),
        '{{service_1_price_number}}': _unwrap_placeholder(str(offers[0].get('price')) if len(offers) > 0 else '{{service_1_price_number}}', '99'),
        '{{service_2_name}}': _unwrap_placeholder(offers[1].get('name') if len(offers) > 1 else '{{service_2_name}}', 'Servicio 2'),
        '{{service_2_price}}': _unwrap_placeholder(str(offers[1].get('price')) if len(offers) > 1 else '{{service_2_price}}', '149 €'),
        '{{service_2_price_number}}': _unwrap_placeholder(str(offers[1].get('price')) if len(offers) > 1 else '{{service_2_price_number}}', '149'),
        '{{service_3_name}}': _unwrap_placeholder(offers[2].get('name') if len(offers) > 2 else '{{service_3_name}}', 'Servicio 3'),
        '{{service_3_price}}': _unwrap_placeholder(str(offers[2].get('price')) if len(offers) > 2 else '{{service_3_price}}', '49 €/mes'),
        '{{service_3_price_number}}': _unwrap_placeholder(str(offers[2].get('price')) if len(offers) > 2 else '{{service_3_price_number}}', '49'),
        '{{service_4_name}}': _unwrap_placeholder(offers[3].get('name') if len(offers) > 3 else '{{service_4_name}}', 'Servicio 4'),
        '{{service_4_price}}': _unwrap_placeholder(str(offers[3].get('price')) if len(offers) > 3 else '{{service_4_price}}', '299 €/mes'),
        '{{service_4_price_number}}': _unwrap_placeholder(str(offers[3].get('price')) if len(offers) > 3 else '{{service_4_price_number}}', '299'),
        '{{service_5_name}}': _unwrap_placeholder(offers[4].get('name') if len(offers) > 4 else '{{service_5_name}}', 'Servicio 5'),
        '{{service_5_price}}': _unwrap_placeholder(str(offers[4].get('price')) if len(offers) > 4 else '{{service_5_price}}', '290 €'),
        '{{service_5_price_number}}': _unwrap_placeholder(str(offers[4].get('price')) if len(offers) > 4 else '{{service_5_price_number}}', '290'),
    }
    # Textos del negocio: src/data/textos.json (clave sin llaves -> texto). Lo calculado de entity.json gana.
    try:
        textos = json.loads(read_text(REPO / 'src' / 'data' / 'textos.json'))
    except (OSError, ValueError) as e:
        sys.exit(f'✗ BUILD FAILED: no se pudo leer src/data/textos.json: {e}')
    replacements = {'{{' + k + '}}': v for k, v in textos.items()}
    replacements.update(derived)
    entity_nodes =[_replace_placeholders_in_json(node, replacements) for node in entity]

    # Marcadores condicionales del Blog (antes de menu_hrefs, para que el estado activo funcione)
    nav_blog = '<li><a href="/blog/">Blog</a></li>' if blog_visible(collections['blog']) else ''
    nav_guias = '<li><a href="/guias/">Guías</a></li>' if collections['guias'] else ''
    header = header.replace('{{nav_blog}}', nav_blog).replace('{{nav_guias}}', nav_guias)
    footer = footer.replace('{{footer_blog}}', nav_blog).replace('{{nav_guias}}', nav_guias)
    footer = footer.replace('{{year}}', str(datetime.now().year))
    pages = []
    for p in sorted((REPO / 'src' / 'pages').rglob('*.html')):
        pages.append(p)
    generated = 0
    errors = []
    warnings = []
    total_bytes = 0
    total_html_before = 0
    total_html_after = 0
    pages_data = []
    for page_path in pages:
        text = read_text(page_path)
        front, content = parse_front_matter(text)
        if 'title' not in front or 'description' not in front:
            errors.append((str(page_path.relative_to(REPO)), 'missing title or description'))
            continue
        # Reemplazar placeholders globales en el contenido de la página (HTML body)
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        page_rel = '/' + str(page_path.relative_to(REPO / 'src' / 'pages')).replace('index.html', '').replace('\\', '/').strip('/')
        if page_rel != '/':
            page_rel += '/'
        if str(page_path.relative_to(REPO / 'src' / 'pages')) == '404.html':
            page_rel = '/404.html'
        composed = compose_page(front, content, layout, header, footer, entity_nodes, page_rel, site_name, site_url, contact_email, whatsapp_link, service_category_1, service_category_2, location, target_audience, featured_action_name, jsonld_replacements=replacements)
        html_before = len(composed.encode('utf-8'))
        if minify:
            composed = minify_html(composed)
        html_after = len(composed.encode('utf-8'))
        total_html_before += html_before
        total_html_after += html_after
        out_path = out / page_path.relative_to(REPO / 'src' / 'pages')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_text(out_path, composed)
        generated += 1
        total_bytes += out_path.stat().st_size
        pages_data.append((page_rel, front, str(out_path)))
    # Índices generados de las colecciones (no existen como archivos en src/pages)
    generated_indexes = []
    if collections['guias']:
        generated_indexes.append(('/guias/',) + render_guias_index(collections['guias']))
    if blog_state(collections['blog']) != 'none':
        generated_indexes.append(('/blog/',) + render_blog_index(collections['blog'], bool(collections['guias'])))
    for page_rel, front, content in generated_indexes:
        # Reemplazar placeholders globales en el contenido generado
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        composed = compose_page(front, content, layout, header, footer, entity_nodes, page_rel, site_name, site_url, contact_email, whatsapp_link, service_category_1, service_category_2, location, target_audience, featured_action_name, jsonld_replacements=replacements)
        html_before = len(composed.encode('utf-8'))
        if minify:
            composed = minify_html(composed)
        html_after = len(composed.encode('utf-8'))
        total_html_before += html_before
        total_html_after += html_after
        out_path = out / page_rel.strip('/') / 'index.html'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_text(out_path, composed)
        generated += 1
        total_bytes += out_path.stat().st_size
        pages_data.append((page_rel, front, str(out_path)))
    try:
        sitemap_order = build_sitemap(pages_data, collections, out)
        robots_path = out / 'robots.txt'
        if robots_path.exists():
            robots_text = read_text(robots_path)
            for placeholder, value in replacements.items():
                robots_text = robots_text.replace(placeholder, value)
            write_text(robots_path, robots_text)
        llms_path = out / 'llms.txt'
        if llms_path.exists():
            llms_text = read_text(llms_path)
            # Reemplazar placeholders globales en llms.txt
            for placeholder, value in replacements.items():
                llms_text = llms_text.replace(placeholder, value)
            llms_path.write_text(render_llms(llms_text, collections, sitemap_order), encoding='utf-8')
    except ValueError as e:
        print(f'✗ BUILD FAILED: {e}', file=sys.stderr)
        raise SystemExit(1)
    if not no_validate:
        import check_site  # import tardío: check_site importa SITE_URL y get_git_info de este módulo
        val_errors, val_warnings = check_site.run_checks(out, SITE_URL)
        errors.extend(val_errors)
        warnings.extend(val_warnings)
    success = len(errors) == 0
    print_report(
        success=success,
        errors=errors,
        warnings=warnings,
        generated=generated,
        total_bytes=total_bytes,
        out=out,
        minify=minify,
        git_branch=git_branch,
        git_commit=git_commit,
        build_time=build_time,
        total_html_before=total_html_before,
        total_html_after=total_html_after,
        css_size_before=css_size_before,
        css_size_after=css_size_after,
    )

    if not success:
        raise SystemExit(1)

if __name__ == '__main__':
    out = None
    minify = None
    no_validate = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--out':
            i += 1
            out = args[i]
        elif args[i] == '--minify':
            i += 1
            minify = args[i].lower() != 'false'
        elif args[i] == '--no-validate':
            no_validate = True
        i += 1
    build(out_dir=out, minify=minify, no_validate=no_validate)