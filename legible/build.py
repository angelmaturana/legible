#!/usr/bin/env python3
import difflib
import html
import json
import os
import re
import shutil
import struct
import sys
sys.dont_write_bytecode = True  # importing check_site must not leave legible/__pycache__/
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import quote

from common import (BuildError, fail, get_git_info, load_site_config, read_text, report_lines,
                    resolve_site_url, write_text)
import check_site
from minify import minify_css, minify_html


# --------------------------------------------------------------------------- 1. configuration: languages, interface texts and the Site object

TEXT_STATIC_SUFFIXES = {'.txt', '.svg', '.xml', '.json', '.html', '.css', '.js', '.webmanifest'}

# language -> (html lang, og:locale, inLanguage); add a row here and an entry in UI below to support another language.
LANGUAGES = {'en': ('en', 'en_US', 'en-US'), 'es': ('es', 'es_ES', 'es-ES')}

# Interface texts (plan 4.4): the fixed words of the layout, the partials and the breadcrumb of the pages, in each
# language. Each key is published as the marker `{{ui_<key>}}` (plain text, escaped where it is used). A site
# rewords any of them with `ui` in src/data/site.json: {"ui": {"skip_to_content": "..."}}. The text of the PAGES is
# content, not interface: it is translated by editing the pages.
UI = {
    'en': {
        'skip_to_content': 'Skip to content',
        'open_menu': 'Open menu',
        'main_navigation': 'Main navigation',
        'home': 'Home',
        'home_aria': 'home',
        'breadcrumb_label': 'Breadcrumb',
        'footer_based_in': 'is based in',
        'footer_site': 'Site',
        'footer_legal': 'Legal',
        'rights_reserved': 'All rights reserved.',
        'whatsapp_open': 'Open WhatsApp chat',
        'whatsapp_contact': 'Contact us on WhatsApp',
        'contact_empty': 'Contact details are not available yet.',
    },
    'es': {
        'skip_to_content': 'Saltar al contenido',
        'open_menu': 'Abrir menú',
        'main_navigation': 'Navegación principal',
        'home': 'Inicio',
        'home_aria': 'inicio',
        'breadcrumb_label': 'Ruta de navegación',
        'footer_based_in': 'tiene su sede en',
        'footer_site': 'Sitio',
        'footer_legal': 'Legal',
        'rights_reserved': 'Todos los derechos reservados.',
        'whatsapp_open': 'Abrir el chat de WhatsApp',
        'whatsapp_contact': 'Escríbenos por WhatsApp',
        'contact_empty': 'Los datos de contacto aún no están disponibles.',
    },
}


def resolve_ui(language, config):
    """The interface texts of `language` with the `ui` object of site.json applied on top.

    `ui` is `{key: text}`. Everything is validated and reported at once, so a typo cannot silently leave the
    default text published: the key must exist in UI, the text must be a non-empty string and cannot contain
    `{{` (a text is never expanded twice). A `ui` that is absent or null changes nothing."""
    texts = dict(UI[language])
    overrides = config.get('ui')
    if overrides is None:
        return texts
    where = 'src/data/site.json › ui'
    if not isinstance(overrides, dict):
        raise BuildError(f'{where} must be an object {{"key": "text"}} (found {type(overrides).__name__})')
    problems = []
    for key, value in overrides.items():
        if key not in texts:
            near = difflib.get_close_matches(str(key), list(texts), n=1)
            hint = f' (did you mean "{near[0]}"?)' if near else ''
            problems.append(f'"{key}": no such key{hint}; the valid keys are: {", ".join(texts)}')
        elif not isinstance(value, str) or not value.strip():
            problems.append(f'"{key}": must be a non-empty text')
        elif '{{' in value:
            problems.append(f'"{key}": contains "{{{{"; write the text itself, not a marker')
        else:
            texts[key] = value
    if problems:
        raise BuildError(f'{where} has {len(problems)} problem{"" if len(problems) == 1 else "s"}:\n  - '
                         + '\n  - '.join(problems))
    return texts


@dataclass
class Site:
    """Everything the build reads about a project, loaded once by load_site(); nothing here is global."""
    root: Path
    config: dict
    site_url: str
    language: str
    lang: str
    og_locale: str
    in_language: str
    ui: dict
    entity: list
    business: dict
    nav_markers: dict = field(default_factory=dict)


def load_site(root, site_url_override=None):
    """Read `<root>/src/data/` and return the Site. Nothing is read or validated on import: every problem
    (site.json, SITE_URL, language, ui, entity.json) is a BuildError raised here, in that order."""
    root = Path(root)
    config = load_site_config(root)
    site_url = resolve_site_url(config, site_url_override)
    language = str(config.get('language', 'en')).strip()
    if language not in LANGUAGES:
        raise BuildError(f'unsupported language {language!r} in src/data/site.json; '
                         f'supported: {", ".join(sorted(LANGUAGES))}')
    lang, og_locale, in_language = LANGUAGES[language]
    ui = resolve_ui(language, config)
    try:
        entity = json.loads(read_text(root / 'src' / 'data' / 'entity.json'))
    except (OSError, ValueError) as exc:
        raise BuildError(f'could not read src/data/entity.json: {exc}')
    if not isinstance(entity, list):
        raise BuildError('src/data/entity.json must contain a JSON list [...]')
    return Site(root=root, config=config, site_url=site_url, language=language, lang=lang, og_locale=og_locale,
                in_language=in_language, ui=ui, entity=entity, business=_main_node(entity),
                nav_markers=render_nav_markers(config))


def _main_node(entity):
    """The main entity node of entity.json: the one whose @id ends in /#business, whatever its @type
    (an Organization, a Restaurant, a Person...). With none, the build stops and names the @id."""
    for n in entity:
        if isinstance(n, dict) and str(n.get('@id', '')).endswith('/#business'):
            return n
    raise BuildError('src/data/entity.json: no main node. Add a node with "@id": "{{site_url}}/#business" '
                     '(its "@type" can be any Schema.org type): the business facts are read from it.')


# --------------------------------------------------------------------------- 2. markers: one table of {{markers}}, replaced in one pass

_MARKER = re.compile(r'\{\{[A-Za-z0-9_]+\}\}')


def _apply_markers(text, table):
    """Replace every known `{{marker}}` of `text` in ONE pass (plan 4.3, rule 1): a value is never expanded again.
    A marker the table does not know stays as it is; check_unrendered reports it."""
    return _MARKER.sub(lambda m: table.get(m.group(0), m.group(0)), text)


def _replace_placeholders_in_json(obj, replacements):
    """Recursively replace {{placeholder}} in string values of a JSON object."""
    if isinstance(obj, dict):
        return {k: _replace_placeholders_in_json(v, replacements) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_placeholders_in_json(item, replacements) for item in obj]
    elif isinstance(obj, str):
        return _apply_markers(obj, replacements)
    else:
        return obj

def _json_str(value):
    """Value ready to go INSIDE a JSON string (quotes, backslashes and newlines escaped)."""
    return json.dumps(str(value), ensure_ascii=False)[1:-1]

def _prune_empty(obj):
    """What would be published empty is dropped, bottom-up: blank strings, empty lists and objects, and an object
    left with only its `@type` (e.g. an address whose every field is blank). Returns None when nothing is left."""
    if isinstance(obj, dict):
        pruned = {k: v for k, v in ((k, _prune_empty(v)) for k, v in obj.items()) if v is not None}
        return pruned if set(pruned) - {'@type'} else None
    if isinstance(obj, list):
        return [v for v in map(_prune_empty, obj) if v is not None] or None
    if isinstance(obj, str):
        return obj if obj.strip() else None
    return obj

_LDJSON_BLOCK = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.DOTALL)

def replace_placeholders_in_content(content, html_replacements, json_replacements):
    """Replace markers in the HTML with HTML-escaped values and, inside JSON-LD blocks,
    with JSON-escaped values: a `"` or `&` in the business name breaks neither the JSON nor the attributes."""
    def apply(text, table):
        return _apply_markers(text, table)
    parts, pos = [], 0
    for m in _LDJSON_BLOCK.finditer(content):
        parts.append(apply(content[pos:m.start()], html_replacements))
        parts.append(m.group(1) + apply(m.group(2), json_replacements) + m.group(3))
        pos = m.end()
    parts.append(apply(content[pos:], html_replacements))
    return ''.join(parts)


# Names the engine uses for its own markers (plan 4.3): a text key of site.json cannot take one of them, nor start
# with `ui_` (the prefix of the interface texts).
RESERVED_MARKERS = frozenset((
    'lang og_locale in_language location whatsapp_link whatsapp_base phone_digits year og_image_width og_image_height '
    'page_title page_description page_url page_updated '
    'nav footer_nav legal_nav contact_methods footer_contact whatsapp_float llms_pages '
    'title description robots canonical og_url jsonld header content footer').split())


def _site_values(site):
    """The values derived from site.json that the pages receive (plan 4.3, "Derivados de sitio").

    Returns a namespace with `derived`, the table of derived markers, and `og_problem`, the warning about the
    og:image file (or None)."""
    config = site.config
    site_name = str(config.get('site_name', ''))
    contact_email = str(config.get('contact_email') or '').strip()  # optional: absent, null or empty = no email
    phone_value = str(config.get('phone_e164') or '').strip()
    whatsapp_message = str(config.get('whatsapp_message', ''))
    whatsapp_link = phone_value if phone_value.startswith('https://') else ''
    whatsapp_base = whatsapp_link  # link without text: pages with their own message append "?text=…"
    phone_digits = ''
    if phone_value and not phone_value.startswith('https://'):
        phone_digits = re.sub(r'\D', '', phone_value)
        if phone_digits:
            whatsapp_base = 'https://wa.me/' + phone_digits
            whatsapp_link = whatsapp_base
            if whatsapp_message:
                whatsapp_link += '?text=' + quote(whatsapp_message, safe='')
    city = str(config.get('city', '')).strip()
    region = str(config.get('region', '')).strip()
    location = ', '.join(part for part in (city, region) if part)  # only the parts that exist
    og_width, og_height, og_problem = read_png_size(site.root / 'src' / 'static' / 'images' / 'og-image.png')
    derived = {
        '{{site_name}}': site_name,
        '{{site_url}}': site.site_url,
        '{{lang}}': site.lang,
        '{{og_locale}}': site.og_locale,
        '{{in_language}}': site.in_language,
        '{{contact_email}}': contact_email,
        '{{whatsapp_link}}': whatsapp_link,
        '{{whatsapp_base}}': whatsapp_base,
        '{{phone_e164}}': phone_value,
        '{{phone_digits}}': phone_digits,
        '{{city}}': city,
        '{{region}}': region,
        '{{location}}': location,
        '{{og_image_width}}': str(og_width or ''),
        '{{og_image_height}}': str(og_height or ''),
    }
    return SimpleNamespace(derived=derived, og_problem=og_problem)


def _site_text_markers(config):
    """Every text (string) of site.json is a marker, `{{key}}`; lists and objects (nav, ...) are not (plan 4.3).
    A text with `{{` inside, or a key the engine reserves, stops the build and names the key."""
    markers = {}
    for key, value in config.items():
        if not isinstance(value, str):
            continue
        if key in RESERVED_MARKERS or key.startswith('ui_'):
            raise BuildError(f'src/data/site.json: the key "{key}" is reserved (the engine uses it as a marker, or it '
                             f'starts with "ui_"). Rename it.')
        if '{{' in value:
            raise BuildError(f'src/data/site.json: the value of "{key}" contains "{{{{". Values are plain text and '
                             f'are never expanded twice: write the text itself, not another marker.')
        markers['{{' + key + '}}'] = value
    return markers


def _marker_tables(site, derived):
    """Build the marker table (plan 4.3). Returns `(replacements, html_replacements)`: the first has the plain
    values (the texts of site.json under the derived values, which win), the second the same values escaped
    for HTML, plus the generated HTML (menus), which is already escaped."""
    ui_markers = {'{{ui_' + key + '}}': text for key, text in site.ui.items()}
    replacements = {**_site_text_markers(site.config), **ui_markers, **derived}
    html_replacements = {k: html.escape(str(v), quote=True) for k, v in replacements.items()}
    html_replacements.update(site.nav_markers)
    html_replacements.update(render_contact_markers(
        derived['{{contact_email}}'], derived['{{phone_digits}}'], derived['{{whatsapp_link}}'], site.ui))
    return replacements, html_replacements


def _shared_parts(layout, header, footer, entity, replacements, html_replacements):
    """Resolve the markers in the layout, the partials and the entity nodes, and fill the year marker. Returns `(layout, header, footer, entity_nodes)`."""
    layout = replace_placeholders_in_content(layout, html_replacements, replacements)
    header = replace_placeholders_in_content(header, html_replacements, replacements)
    footer = replace_placeholders_in_content(footer, html_replacements, replacements)
    entity_nodes = [_replace_placeholders_in_json(node, replacements) for node in entity]
    footer = footer.replace('{{year}}', str(datetime.now().year))
    return layout, header, footer, entity_nodes


# --------------------------------------------------------------------------- 3. navigation from site.json

def _nav_items(config, key, allow_children, allow_action):
    """Validate `config[key]` (a list of {label, url[, action][, children]}) and return it. Every problem is a
    BuildError that names the entry, e.g. `src/data/site.json › nav[1] › children[0]: ...`."""
    items = config.get(key, [])
    if items is None:
        items = []
    if not isinstance(items, list):
        raise BuildError(f'src/data/site.json › {key} must be a list (found {type(items).__name__})')
    seen = {}

    def check(entry, where, level):
        if not isinstance(entry, dict):
            raise BuildError(f'{where} must be an object {{"label": "...", "url": "/page/"}}')
        for field_name in ('label', 'url'):
            value = entry.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise BuildError(f'{where}: missing "{field_name}" (a non-empty text)')
        url = entry['url']
        if not (url.startswith('/') and url.endswith('/')) or url.startswith('//') or ' ' in url:
            raise BuildError(f'{where}: url {url!r} must be an internal address that starts and ends with "/" '
                             '(for example "/contact/")')
        if url in seen:
            raise BuildError(f'{where}: url {url!r} is repeated (already used by {seen[url]})')
        seen[url] = where
        if 'action' in entry:
            if not allow_action or level > 0:
                raise BuildError(f'{where}: "action" is only allowed on a top-level entry of nav')
            if not isinstance(entry['action'], bool):
                raise BuildError(f'{where}: "action" must be true or false (found {entry["action"]!r})')
        if 'children' in entry:
            if not allow_children or level > 0:
                raise BuildError(f'{where}: "children" is only allowed in one level of nav (no submenus inside a submenu)')
            if not isinstance(entry['children'], list):
                raise BuildError(f'{where}: "children" must be a list')
            for j, child in enumerate(entry['children']):
                check(child, f'{where} › children[{j}]', level + 1)

    for i, entry in enumerate(items):
        check(entry, f'src/data/site.json › {key}[{i}]', 0)
    return items


def _link(entry, cls=''):
    attrs = (f' class="{cls}"' if cls else '') + f' href="{html.escape(entry["url"], quote=True)}"'
    return f'<a{attrs}>{html.escape(entry["label"].strip(), quote=False)}</a>'


def render_nav_markers(config):
    """Validate `nav` and `legal_nav` of site.json and return the HTML of the markers `{{nav}}` (the whole <ul> of
    the main menu: the <nav aria-label> stays in the partial), `{{footer_nav}}` (the same pages, submenus
    flattened) and `{{legal_nav}}`."""
    nav = _nav_items(config, 'nav', allow_children=True, allow_action=True)
    legal = _nav_items(config, 'legal_nav', allow_children=False, allow_action=False)

    lines = ['<ul>']
    for entry in nav:
        children = entry.get('children') or []
        if children:
            lines.append(f'<li class="has-sub">{_link(entry)}<ul>'
                         + ''.join(f'<li>{_link(c)}</li>' for c in children) + '</ul></li>')
        else:
            lines.append(f'<li>{_link(entry, "nav-action" if entry.get("action") else "")}</li>')
    lines.append('</ul>')
    flat = [e for entry in nav for e in [entry] + (entry.get('children') or [])]
    return {
        '{{nav}}': '\n'.join(lines),
        '{{footer_nav}}': '<ul>' + ''.join(f'<li>{_link(e)}</li>' for e in flat) + '</ul>',
        '{{legal_nav}}': '<ul>' + ''.join(f'<li>{_link(e)}</li>' for e in legal) + '</ul>',
    }


# --------------------------------------------------------------------------- 4. contact channels and og:image size

_ICON_ATTRS = ('viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
               'stroke-linejoin="round" aria-hidden="true" focusable="false"')
_ICONS = {
    'email': '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    'phone': '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    'whatsapp': '<path d="M21 11.5a8.4 8.4 0 0 1-12.4 7.4L3 21l2.1-5.4A8.4 8.4 0 1 1 21 11.5z"/>',
}
_WHATSAPP_FLOAT_ICON = ('<svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true" focusable="false">'
                        '<path fill="currentColor" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>')


def render_contact_markers(email, phone_digits, whatsapp_link, ui):
    """The HTML of `{{contact_methods}}` (a list of buttons, one per channel that exists, or the `contact_empty` text),
    `{{footer_contact}}` (the footer's address block, empty when there is no channel) and `{{whatsapp_float}}`
    (the floating button, only with WhatsApp). A channel that is not configured is not written at all, so no
    link is ever empty. The phone number is the one of WhatsApp: with a number there is a `tel:` link too."""
    # (icon, href, text for the page buttons, text for the footer, opens in a new tab)
    channels = []
    if email:
        channels.append(('email', 'mailto:' + email, email, email, False))
    if phone_digits:
        channels.append(('phone', 'tel:+' + phone_digits, '+' + phone_digits, '+' + phone_digits, False))
    if whatsapp_link:
        channels.append(('whatsapp', whatsapp_link, ui['whatsapp_open'], ui['whatsapp_contact'], True))

    def attrs(href, new_tab):
        return f'href="{html.escape(href, quote=True)}"' + (' target="_blank" rel="noopener noreferrer"' if new_tab else '')

    def icon(kind, css):
        return f'<svg class="{css}" width="20" height="20" {_ICON_ATTRS}>{_ICONS[kind]}</svg>'

    if channels:
        items = ''.join(
            f'<li><a class="button primary" {attrs(href, new_tab)}>{icon(kind, "btn-icon")}{html.escape(page_text)}</a></li>'
            for kind, href, page_text, _footer_text, new_tab in channels)
        methods = f'<ul class="actions contact-methods">{items}</ul>'
        links = ''.join(
            f'<a {attrs(href, new_tab)} class="footer-contact-item">{icon(kind, "footer-icon")}'
            f'<span>{html.escape(footer_text)}</span></a>'
            for kind, href, _page_text, footer_text, new_tab in channels)
        footer = f'<address class="footer-contact">{links}</address>'
    else:
        methods = f'<p>{html.escape(ui["contact_empty"])}</p>'
        footer = ''
    float_button = ''
    if whatsapp_link:
        float_button = (f'<a {attrs(whatsapp_link, True)} class="whatsapp-float" '
                        f'aria-label="{html.escape(ui["whatsapp_open"], quote=True)}">{_WHATSAPP_FLOAT_ICON}</a>')
    return {'{{contact_methods}}': methods, '{{footer_contact}}': footer, '{{whatsapp_float}}': float_button}


def read_png_size(path):
    """`(width, height, problem)` from the header of a PNG file (stdlib `struct`, nothing else is read). When the
    file is missing or is not a PNG, the size is `None` and `problem` says what to do."""
    try:
        with open(path, 'rb') as handle:
            head = handle.read(24)
    except OSError:
        return None, None, 'the image does not exist: add a PNG of 1200×630 px'
    if len(head) < 24 or head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
        return None, None, ('the image is not a PNG (og:image:type is image/png), so its size cannot be published: '
                            'save it as a PNG of 1200×630 px')
    width, height = struct.unpack('>II', head[16:24])
    return width, height, None


# --------------------------------------------------------------------------- 5. page composition and writing

def menu_hrefs(header_html):
    """Internal links of the main <nav> (any level), read from the partial."""
    nav = re.search(r'<nav\b.*?</nav>', header_html, flags=re.DOTALL)
    return re.findall(r'<a\b[^>]*\bhref="(/[^"]*)"', nav.group(0)) if nav else []

def parse_front_matter(text):
    if not text.startswith('---'):
        return {}, text
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', text, re.DOTALL)
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

def url_from_rel(site_url, rel):
    if rel == '/':
        return site_url + '/'
    return site_url + rel

def compute_active(rel, front, hrefs):
    if 'active' in front:
        return front['active'], ''
    if rel in hrefs:
        return rel, 'page'
    # Page without its own menu entry: highlight the deepest ancestor
    parents = [h for h in hrefs if h != '/' and rel.startswith(h)]
    if parents:
        return max(parents, key=len), 'true'
    return '', ''

def apply_active(header_html, active_href, aria_value):
    if not active_href:
        return header_html
    marked = []  # only the first matching link is marked (the menu may repeat an href)
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
    # Main <nav> links only (the class may come before or after the href)
    def nav_repl(nm):
        return re.sub(r'<a((?:\s+[a-zA-Z-]+="[^"]*")+)>', repl, nm.group(0))
    return re.sub(r'<nav\b.*?</nav>', nav_repl, header_html, flags=re.DOTALL)

def render_canonical(site_url, rel, canonical_mode):
    if canonical_mode == 'none':
        return ''
    return f'<link rel="canonical" href="{url_from_rel(site_url, rel)}">'

def render_og_url(site_url, rel, canonical_mode):
    if canonical_mode == 'none':
        return ''
    return f'<meta property="og:url" content="{url_from_rel(site_url, rel)}">'

def render_jsonld(page_json, entity_nodes, page_rel):
    if page_json is None:
        return ''
    graph = []
    seen = set()
    page_json = _prune_empty(page_json) or {}
    entity_nodes = [n for n in map(_prune_empty, entity_nodes) if n is not None]
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
            raise BuildError(f'page {page_rel}: duplicate JSON-LD @id "{nid}": it is already defined in '
                             f'src/data/entity.json. Rename the @id of this page node.')
        graph.append(node)
    out = {'@context': 'https://schema.org', '@graph': graph}
    return '<script type="application/ld+json">\n' + json.dumps(out, ensure_ascii=False, indent=4) + '\n</script>'

def check_unrendered(html_text, path):
    m = re.search(r'\{\{([^}]+)\}\}', html_text)
    if m:
        raise BuildError(f'marker {m.group(0)} (first found on page {path}) has no value. '
                 f'Add "{m.group(1)}" to src/data/site.json or write it directly in the page. '
                 f'If it is a derived marker (see "Markers" in DOCUMENTATION.md), fix its source in '
                 f'src/data/entity.json or src/data/site.json instead.')

def compose_page(front, content, layout_text, header_text, footer_text, entity_nodes, page_rel, site_url,
                 jsonld_replacements):
    """Compose one page: its front matter, content and JSON-LD inside the layout. The layout, the partials and the
    content arrive with the site's markers already resolved; here the page's own markers are filled, in ONE pass
    over the layout (a value is never expanded again), and any marker left over is a build error."""
    title_raw = _apply_markers(front.get('title', ''), jsonld_replacements)
    description_raw = _apply_markers(front.get('description', ''), jsonld_replacements)
    robots = front.get('robots', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1')
    canonical_mode = front.get('canonical', 'auto')
    header_text = apply_active(header_text, *compute_active(page_rel, front, menu_hrefs(header_text)))
    # {{page_url}} and {{page_updated}}: the page's own URL and `updated` date, so a page never types them.
    page_values = {'{{page_title}}': title_raw, '{{page_description}}': description_raw,
                   '{{page_url}}': url_from_rel(site_url, page_rel)}
    updated = front.get('updated', '').strip()
    if updated:
        page_values['{{page_updated}}'] = updated
    elif '{{page_updated}}' in content:
        raise BuildError(f'page {page_rel}: uses {{{{page_updated}}}} but its front matter has no "updated: YYYY-MM-DD". '
                         f'Add the date to the front matter.')
    page_json = None
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
    if m:
        json_table = {k: _json_str(v) for k, v in {**jsonld_replacements, **page_values}.items()}
        try:
            page_json = json.loads(_apply_markers(m.group(1).strip(), json_table))
        except ValueError as e:
            raise BuildError(f'page {page_rel}: the JSON-LD block is not valid JSON ({e}). '
                             f'Fix the block in the page, or the value a marker inserts into it.')
        content = (content[:m.start()] + content[m.end():]).strip()
    content = _apply_markers(content, {k: html.escape(v, quote=True) for k, v in page_values.items()})
    table = {
        '{{title}}': html.escape(title_raw, quote=True), '{{description}}': html.escape(description_raw, quote=True),
        '{{robots}}': html.escape(robots, quote=True),
        '{{canonical}}': render_canonical(site_url, page_rel, canonical_mode),
        '{{og_url}}': render_og_url(site_url, page_rel, canonical_mode),
        '{{jsonld}}': render_jsonld(page_json, entity_nodes, page_rel),
        '{{header}}': header_text, '{{content}}': content, '{{footer}}': footer_text,
    }
    page = _apply_markers(layout_text, table)
    check_unrendered(page, page_rel)
    return page


class _PageWriter:
    """Compose, minify and write one page, and keep the running totals the report needs.

    `shared` holds the arguments every page passes to compose_page (layout, header, footer, entity nodes and
    the resolved values), so a page only adds its own front matter, content and URL."""

    def __init__(self, out, minify, shared, html_replacements, json_replacements):
        self.out = out
        self.minify = minify
        self.shared = shared
        self.html_replacements = html_replacements
        self.json_replacements = json_replacements
        self.generated = 0
        self.total_bytes = 0
        self.html_before = 0
        self.html_after = 0
        self.pages_data = []

    def emit(self, out_path, page_rel, front, content):
        # A page that prints the contact email while there is none would publish an empty sentence ("write to ."):
        # that is an error. No general "empty marker" rule: `{{location}}`, for one, may be empty on purpose.
        if '{{contact_email}}' in content and not self.html_replacements.get('{{contact_email}}'):
            raise BuildError(f'page {page_rel}: uses {{{{contact_email}}}} but "contact_email" in src/data/site.json is empty. '
                             f'Write the email in site.json, or take the marker out of the page.')
        # Global markers: HTML body as HTML, JSON-LD with JSON escaping
        content = replace_placeholders_in_content(content, self.html_replacements, self.json_replacements)
        composed = compose_page(front, content, page_rel=page_rel, **self.shared)
        self.html_before += len(composed.encode('utf-8'))
        if self.minify:
            composed = minify_html(composed)
        self.html_after += len(composed.encode('utf-8'))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_text(out_path, composed)
        self.generated += 1
        self.total_bytes += out_path.stat().st_size
        self.pages_data.append((page_rel, front, str(out_path)))


def _write_pages(writer, errors, root):
    """Write every page of src/pages/. A page with no title or description is an error and is skipped."""
    pages_dir = root / 'src' / 'pages'
    for page_path in sorted(pages_dir.rglob('*.html')):
        front, content = parse_front_matter(read_text(page_path))
        if 'title' not in front or 'description' not in front:
            errors.append((str(page_path.relative_to(root)), 'missing title or description'))
            continue
        rel_parts = list(page_path.relative_to(pages_dir).parts)
        if rel_parts == ['404.html']:
            page_rel = '/404.html'
        else:
            if rel_parts[-1] == 'index.html':
                rel_parts.pop()  # only the final file name: a folder such as "my-index.html-x" stays intact
            page_rel = '/' + '/'.join(rel_parts)
            if page_rel != '/':
                page_rel += '/'
        writer.emit(writer.out / page_path.relative_to(pages_dir), page_rel, front, content)


# --------------------------------------------------------------------------- 6. sitemap, robots.txt and llms.txt

def iso_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def page_date_modified(out_path, front):
    """lastmod of a page: dateModified from the compiled JSON-LD (the most recent of its nodes) or `updated`."""
    text = read_text(out_path)
    dates = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in data.get('@graph') or [data]:
            if isinstance(node, dict) and iso_date(node.get('dateModified')):
                dates.append(node['dateModified'])
    if dates:
        return max(dates)
    if iso_date(front.get('updated')):
        return front['updated']
    return None

def build_sitemap(pages_data, out, site_url):
    """Write out/sitemap.xml with the indexable pages (not 404, not noindex): the home page first, then the rest
    sorted by URL. The order of the menu does not matter here (it only rules llms.txt)."""
    entries = {}
    for rel, front, out_path in pages_data:
        robots = re.search(r'<meta name="robots" content="([^"]*)"', read_text(out_path))
        if rel == '/404.html' or (robots and 'noindex' in robots.group(1).lower()):
            continue
        lm = page_date_modified(out_path, front)
        if lm is None:
            raise BuildError(f'page {rel}: no dateModified in the JSON-LD and no "updated" in the front matter. '
                             f'Add "updated: YYYY-MM-DD" to the front matter.')
        upd = front.get('updated')
        if upd and upd != lm:
            raise BuildError(f'page {rel}: front matter "updated: {upd}" differs from the JSON-LD dateModified ({lm}). '
                             f'Use the same date in both, or write {{{{page_updated}}}} in the JSON-LD.')
        entries[rel] = lm
    order = sorted(entries, key=lambda rel: (rel != '/', rel))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in order:
        lines += ['    <url>', f'        <loc>{site_url}{rel}</loc>', f'        <lastmod>{entries[rel]}</lastmod>', '    </url>']
    lines.append('</urlset>')
    write_text(Path(out) / 'sitemap.xml', '\n'.join(lines) + '\n')
    return order

def _page_summary(rel, html_text):
    """Title and description of a built page, read from its `<title>` and `<meta name="description">` (markers already
    resolved), as one line of plain text each. Brackets become parentheses so they cannot break a Markdown link."""
    found = []
    for pattern, what in ((r'<title>(.*?)</title>', '<title>'), (r'<meta name="description" content="([^"]*)"', 'meta description')):
        m = re.search(pattern, html_text, re.S)
        text = ' '.join(html.unescape(m.group(1)).split()) if m else ''
        if not text:
            raise BuildError(f'page {rel}: no {what}. llms.txt lists every indexable page with its title and '
                             f'description: add "title" and "description" to its front matter.')
        found.append(text.translate(str.maketrans('[]', '()')))
    return tuple(found)


def render_llms_pages(pages, nav_urls, site_url):
    """The `{{llms_pages}}` list of llms.txt: `- [Title](URL): description`, the pages that are in the menu first (in
    the order of `nav`) and then the rest by URL. `pages` maps the route of each indexable page to its
    `(title, description)`; a menu address with no indexable page is skipped."""
    first = [url for url in dict.fromkeys(nav_urls) if url in pages]
    rest = sorted((url for url in pages if url not in first), key=lambda url: (url != '/', url))
    return '\n'.join(f'- [{pages[url][0]}]({site_url}{url}): {pages[url][1]}' for url in first + rest)


def render_llms(text, replacements=None):
    if replacements:
        text = _apply_markers(text, replacements)
    m = re.search(r'\{\{[^}]+\}\}', text)
    if m:
        raise BuildError(f'marker {m.group(0)} in src/static/llms.txt has no value. Add "{m.group(0)[2:-2]}" to '
                         f'src/data/site.json or remove it from the file.')
    return text


def _write_site_files(out, pages_data, replacements, site):
    """Write sitemap.xml and resolve the markers of robots.txt and llms.txt."""
    indexable = build_sitemap(pages_data, out, site.site_url)
    paths = {rel: out_path for rel, _front, out_path in pages_data}
    nav = site.config.get('nav') or []
    nav_urls = [e['url'] for entry in nav for e in [entry] + (entry.get('children') or [])]
    replacements = {**replacements, '{{llms_pages}}': render_llms_pages(
        {rel: _page_summary(rel, read_text(paths[rel])) for rel in indexable}, nav_urls, site.site_url)}
    robots_path = out / 'robots.txt'
    if robots_path.exists():
        write_text(robots_path, _apply_markers(read_text(robots_path), replacements))
    llms_path = out / 'llms.txt'
    if llms_path.exists():
        write_text(llms_path, render_llms(read_text(llms_path), replacements))


# --------------------------------------------------------------------------- 7. report and output folder

REPORT_BANNER = 'Legible • Static site generator'


def print_report(banner, success, errors, warnings, generated, total_bytes, out, minify,
                 git_branch, git_commit, build_time,
                 total_html_before, total_html_after, css_size_before, css_size_after, strict=False):
    COL = 50
    LBL = 15
    W = 2 + LBL + 2 + COL  # interior width
    BANNER = banner

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

    if errors:
        centered('✗  Errors')
        for line in report_lines(errors, W - 2):
            print(f'║  {line:<{W-2}}║')
    if warnings:
        centered('⚠  Warnings (treated as errors)' if strict else '⚠  Warnings')
        for line in report_lines(warnings, W - 2):
            print(f'║  {line:<{W-2}}║')
    elif success:
        centered('✓  No warnings')

    empty()
    if success:
        centered('Site ready for deployment')
    else:
        centered('Build aborted — fix errors above')
    empty()
    print('╚' + '═' * W + '╝')

def check_out_dir(out, root):
    """Abort if the output folder would put the project at risk (the build empties it entirely)."""
    out = Path(out).resolve()
    root = Path(root).resolve()
    protected = [root / 'src', root / 'legible']
    at_risk = (
        out == root or out in root.parents
        or any(out == p or p in out.parents for p in protected)
        or any((out / p.name).exists() for p in protected)
    )
    if at_risk:
        raise BuildError(f'the output folder {out} is the project, src/, legible/ or contains one of them, '
                         'and would be emptied. Use a folder of its own, such as dist/.', label='BUILD ABORTED')


def _read_required(root, rel_path):
    """Read a required project file or raise a clean BuildError."""
    try:
        return read_text(Path(root) / rel_path)
    except OSError as exc:
        raise BuildError(f'could not read {rel_path}: {exc}')


def _prepare_output(root, out, minify):
    """Empty the output folder, copy src/static/ and write the (optionally minified) CSS.
    Returns the size of the CSS before and after minifying."""
    check_out_dir(out, root)
    if out.exists():
        for p in out.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    static_src = root / 'src' / 'static'
    for p in static_src.rglob('*'):
        if p.is_file():
            target = out / p.relative_to(static_src)
            target.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix.lower() in TEXT_STATIC_SUFFIXES:
                write_text(target, read_text(p))  # text files leave with LF even if the source has CRLF
            else:
                target.write_bytes(p.read_bytes())
    css_dst = out / 'css' / 'site.css'
    css_dst.parent.mkdir(parents=True, exist_ok=True)
    css_text = _read_required(root, 'src/css/site.css')
    css_size_before = len(css_text.encode('utf-8'))
    if minify:
        css_text = minify_css(css_text)
    css_size_after = len(css_text.encode('utf-8'))
    write_text(css_dst, css_text)
    return css_size_before, css_size_after


# --------------------------------------------------------------------------- 8. build() and the command line

def _final_checks(out, no_validate, site, errors, warnings):
    """Add the validator's findings to `errors` and `warnings`."""
    if not no_validate:
        val_errors, val_warnings = check_site.run_checks(out, site.site_url)
        errors.extend(val_errors)
        warnings.extend(val_warnings)


def build(root, out_dir=None, minify=None, no_validate=False, strict=False, site_url_override=None):
    """Build the project in `root` into `out_dir` (default `<root>/dist`). Returns True when it succeeded.
    The validator runs on the result unless `no_validate`; with `strict` a warning (the build's or the
    validator's) fails the build, like `check_site.py --strict`."""
    root = Path(root)
    site = load_site(root, site_url_override)
    git_branch, git_commit = get_git_info(root)
    build_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out = Path(out_dir or root / 'dist')
    css_size_before, css_size_after = _prepare_output(root, out, minify)

    layout = _read_required(root, 'src/layout.html')
    header = _read_required(root, 'src/partials/header.html')
    footer = _read_required(root, 'src/partials/footer.html')
    errors = []
    warnings = []
    values = _site_values(site)
    if values.og_problem:
        warnings.append(('src/static/images/og-image.png', values.og_problem))
    replacements, html_replacements = _marker_tables(site, values.derived)
    layout, header, footer, entity_nodes = _shared_parts(
        layout, header, footer, site.entity, replacements, html_replacements)

    shared = dict(layout_text=layout, header_text=header, footer_text=footer, entity_nodes=entity_nodes,
                  site_url=site.site_url, jsonld_replacements=replacements)
    writer = _PageWriter(out, minify, shared, html_replacements, {k: _json_str(v) for k, v in replacements.items()})
    _write_pages(writer, errors, root)
    _write_site_files(out, writer.pages_data, replacements, site)
    _final_checks(out, no_validate, site, errors, warnings)
    success = len(errors) == 0 and not (strict and warnings)
    print_report(
        banner=REPORT_BANNER,
        success=success,
        errors=errors,
        warnings=warnings,
        generated=writer.generated,
        total_bytes=writer.total_bytes,
        out=out,
        minify=minify,
        git_branch=git_branch,
        git_commit=git_commit,
        build_time=build_time,
        total_html_before=writer.html_before,
        total_html_after=writer.html_after,
        css_size_before=css_size_before,
        css_size_after=css_size_after,
        strict=strict,
    )

    return success


USAGE = 'usage: build.py [--all] [--out FOLDER] [--minify true|false] [--no-validate] [--strict]'


def _env_enabled(environ, name):
    """CSS_MINIFY and CHECK_STRICT are on unless they say FALSE (any case)."""
    return environ.get(name, 'TRUE').strip().upper() != 'FALSE'


def parse_args(args, environ=None):
    """Command line -> keyword arguments of build() plus `all`. Raises BuildError (with the usage line) on a
    bad option. `--all` is the whole pipeline: it minifies unless CSS_MINIFY=FALSE and is strict unless
    CHECK_STRICT=FALSE (an explicit --minify or --strict wins over the variable) and always validates."""
    options = dict(out_dir=None, minify=None, no_validate=False, strict=None, all=False)
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--all':
            options['all'] = True
        elif arg == '--no-validate':
            options['no_validate'] = True
        elif arg == '--strict':
            options['strict'] = True
        elif arg in ('--out', '--minify'):
            i += 1
            if i >= len(args):
                raise BuildError(f'missing value for {arg}\n{USAGE}', label='')
            if arg == '--out':
                options['out_dir'] = args[i]
            elif args[i].lower() in ('true', 'false'):
                options['minify'] = args[i].lower() == 'true'
            else:
                raise BuildError(f'--minify accepts true or false (got: {args[i]!r})\n{USAGE}', label='')
        else:
            raise BuildError(f'unknown argument: {arg}\n{USAGE}', label='')
        i += 1
    if options['all']:
        if options['no_validate']:
            raise BuildError(f'--all always validates: drop --no-validate\n{USAGE}', label='')
        environ = os.environ if environ is None else environ
        if options['minify'] is None:
            options['minify'] = _env_enabled(environ, 'CSS_MINIFY')
        if options['strict'] is None:
            options['strict'] = _env_enabled(environ, 'CHECK_STRICT')
    options['minify'] = bool(options['minify'])
    options['strict'] = bool(options['strict'])
    return options


def _prelaunch_notice(root, out):
    """After `--all`: say, without failing, that example data is left (the list: check_site.py --prelaunch)."""
    found = check_site.prelaunch_findings(root, out)
    if found:
        print(f'WARNING: not ready to publish: {len(found)} thing(s) still say "example". '
              'List and what to do: python3 legible/check_site.py --prelaunch', file=sys.stderr)


def run(root, argv, environ=None):
    """The command line of build.py for the project in `root`. Returns the exit code: 0 ok, 1 on a build error,
    a failed validation or (with --strict) a warning. `environ` defaults to os.environ."""
    try:
        options = parse_args(argv, environ)
        run_all = options.pop('all')
        ok = build(root, **options)
        if ok and run_all:
            _prelaunch_notice(root, Path(options['out_dir'] or Path(root) / 'dist'))
        return 0 if ok else 1
    except BuildError as exc:
        return fail(exc)


def main(argv=None):
    """Entry point. The only place that knows where the project is."""
    root = Path(__file__).resolve().parent.parent
    return run(root, sys.argv[1:] if argv is None else argv)


if __name__ == '__main__':
    sys.exit(main())