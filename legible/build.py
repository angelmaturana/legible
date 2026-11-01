#!/usr/bin/env python3
import difflib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
sys.dont_write_bytecode = True  # the late import of check_site must not leave legible/__pycache__/
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import quote

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / 'src' / 'data' / 'site.json'


def load_site_config():
    """Load the project configuration; site data does not live in the engine."""
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8')) if CONFIG_PATH.exists() else {}
    except (OSError, ValueError) as exc:
        raise SystemExit(f'✗ BUILD FAILED: could not read src/data/site.json: {exc}')
    if not isinstance(config, dict):
        raise SystemExit('✗ BUILD FAILED: src/data/site.json must contain a JSON object')
    return config


SITE_CONFIG = load_site_config()
# SITE_URL overrides the domain in CI/previews without editing source files.
SITE_URL = (os.environ.get('SITE_URL') or SITE_CONFIG.get('site_url', '')).strip().rstrip('/')
if not re.fullmatch(r'https://[^\s/]+(?::\d+)?(?:/[^\s]*)?', SITE_URL):
    sys.exit(f'✗ SITE_URL must start with https:// (current value: {SITE_URL!r}); check src/data/site.json')
OUT_DEFAULT = REPO / 'dist'

# language -> (html lang, og:locale, inLanguage); add a row to support another language. It only sets the
# language attributes of the pages: the engine texts stay as they are until the site overrides them.
LANGUAGES = {'en': ('en', 'en_US', 'en-US'), 'es': ('es', 'es_ES', 'es-ES')}
LANGUAGE = str(SITE_CONFIG.get('language', 'en')).strip()
if LANGUAGE not in LANGUAGES:
    sys.exit(f'✗ BUILD FAILED: unsupported language {LANGUAGE!r} in src/data/site.json; '
             f'supported: {", ".join(sorted(LANGUAGES))}')
LANG, OG_LOCALE, IN_LANGUAGE = LANGUAGES[LANGUAGE]
# Texts the engine generates (months, breadcrumb and menu labels, guides and blog indexes, closing strip,
# home resources, llms.txt labels). They are generic and in English; a site rewords any of them, in any
# language, with `generated_content.locale_overrides` in src/data/site.json (DOCUMENTATION.md section 2.1).
DEFAULT_TEXTS = {
    "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "long_date": "{month} {day}, {year}",
    "breadcrumb_home": "Home",
    "breadcrumb_label": "Breadcrumb",
    "nav_guides": "Guides",
    "nav_blog": "Blog",
    "card_read_guide": "Read the guide",
    "card_read_article": "Read the article",
    "lead_strip_action_label": "initial consultation",
    "lead_strip_eyebrow": "Next step",
    "lead_strip_headline": "Not sure where to start?",
    "lead_strip_lead_html": "Request your {action_link}: we will tell you what makes sense for your business.",
    "lead_strip_button": "Request a consultation",
    "lead_strip_contact": "or write to us at {email} or on {whatsapp}.",
    "lead_strip_contact_email_only": "or write to us at {email}.",
    "lead_strip_contact_whatsapp_only": "or write to us on {whatsapp}.",
    "home_resources_heading": "Resources for your business",
    "home_resources_guides_title": "Step-by-step guides",
    "home_resources_guides_text": "Explanations for solving a specific question about your business, with the date of their last review.",
    "home_resources_guides_link": "See the guides",
    "home_resources_blog_title": "Articles and news",
    "home_resources_blog_text": "Dated analysis of questions relevant to your business, with no promises.",
    "home_resources_blog_link": "See the articles",
    "guides_index_title": "Guides for your business",
    "guides_index_description": "Step-by-step guides to solve specific questions about your business. No tricks and no promises.",
    "guides_index_heading": "Guides to solve questions about your business",
    "guides_index_lead": "Step-by-step explanations for solving one specific question. You can apply them yourself; if you would rather we did it for you, each guide leads to the service that solves it.",
    "guides_index_intro": "Each guide explains what to do, in what order and what does not work. None of them promises guaranteed results: that depends on many factors. They carry the date of their last review so you know whether they are still current.",
    "guides_index_extra_heading": "How to get the most out of them",
    "blog_index_title": "Articles and news for your business",
    "blog_index_description": "Dated articles on topics relevant to your business: analysis and opinion, with no promises.",
    "blog_index_heading": "Articles and news",
    "blog_index_lead": "Dated articles in which we look at specific questions for your business. They are analysis and opinion; if you are looking for the steps to do something, {guides_txt}.",
    "blog_lead_guides_link": "see the <a href=\"{guides_url}\">guides</a>",
    "blog_lead_guides_text": "see the guides",
    "blog_index_intro": "Articles carry their date because what they say can go out of date. Trust the publication date, and keep in mind that tools and platforms change often. You will not find press releases or promises here. If something you read does not fit your case, write to us and we will take a look.",
    "blog_index_list_heading": "Latest articles",
    "blog_index_criteria_heading": "What you will find here",
    "llms_guides_description": "Step-by-step guides for your business, grouped by topic.",
    "llms_blog_description": "Dated articles on topics for your business.",
    "target_audience": "businesses in {areas}",
}


# `{name}` placeholders of a locale text (the engine fills them in); `{{marker}}` is not one of them.
_LOCALE_PLACEHOLDER = re.compile(r'(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})')


def _locale_placeholders(text):
    return sorted(set(_LOCALE_PLACEHOLDER.findall(text)))


def apply_locale_overrides(locale, config):
    """Return `locale` with `generated_content.locale_overrides` of site.json applied on top.

    The texts the engine generates (home resources, guides and blog indexes, closing strip, llms.txt) come
    from `DEFAULT_TEXTS` above and speak of "your business". A site changes them from src/ with
    `generated_content.locale_overrides`: an object `{locale key: new text}`. Everything is validated and
    reported at once, so a typo cannot silently leave the default text published:
      - the key must exist in `DEFAULT_TEXTS`;
      - the text must be non-empty and of the same kind as the default (`months` is a list of 12 texts);
      - it may use only the `{placeholders}` the default has (a subset is fine, `{{markers}}` are free).
    Per-section values (`generated_content.guides_index.title`, ...) still win over an override.
    `locale` is not modified."""
    generated = config.get('generated_content')
    overrides = generated.get('locale_overrides') if isinstance(generated, dict) else None
    if overrides is None:
        return locale
    where = 'src/data/site.json › generated_content › locale_overrides'
    if not isinstance(overrides, dict):
        raise SystemExit(f'✗ BUILD FAILED: {where} must be an object {{"locale_key": "text"}} '
                         f'(found {type(overrides).__name__})')
    problems = []
    clean = {}
    for key, value in overrides.items():
        default = locale.get(key)
        if key not in locale:
            near = difflib.get_close_matches(str(key), list(locale), n=1)
            hint = f' (did you mean "{near[0]}"?)' if near else ''
            problems.append(f'"{key}": no such key{hint}; the valid keys are those of DEFAULT_TEXTS in legible/build.py')
        elif isinstance(default, list):
            if (not isinstance(value, list) or len(value) != len(default)
                    or not all(isinstance(v, str) and v.strip() for v in value)):
                problems.append(f'"{key}": must be a list of {len(default)} non-empty texts')
            else:
                clean[key] = list(value)
        elif isinstance(default, str):
            if not isinstance(value, str):
                problems.append(f'"{key}": must be a text (found {type(value).__name__})')
                continue
            if not value.strip():
                problems.append(f'"{key}": must be a non-empty text')
                continue
            allowed = _locale_placeholders(default)
            extra = [name for name in _locale_placeholders(value) if name not in allowed]
            if extra:
                can = ', '.join('{' + a + '}' for a in allowed) or 'no {placeholders}'
                problems.append(f'"{key}": uses {", ".join("{" + e + "}" for e in extra)}, which this text '
                                f'does not receive (it can use: {can})')
                continue
            if key == 'long_date':
                try:
                    value.format(day=1, month='m', year=2000)
                except (KeyError, IndexError, ValueError) as exc:
                    problems.append(f'"{key}": not a valid date format ({exc}); use {{day}}, {{month}} and {{year}}')
                    continue
            clean[key] = value
        else:
            clean[key] = value
    if problems:
        raise SystemExit(f'✗ BUILD FAILED: {where} has {len(problems)} problem'
                         f'{"" if len(problems) == 1 else "s"}:\n  - ' + '\n  - '.join(problems))
    return {**locale, **clean}


LOCALE = apply_locale_overrides(DEFAULT_TEXTS, SITE_CONFIG)


def t(key, locale=None):
    """Engine text for `key` (with the site's overrides unless `locale` is given); a missing key stops the build."""
    data = LOCALE if locale is None else locale
    if key not in data:
        raise SystemExit(f'✗ BUILD FAILED: key "{key}" is missing in DEFAULT_TEXTS (legible/build.py)')
    return data[key]

# Markers whose value is a sample fallback (see sample_slots) and the ones actually found in published text.
_SAMPLE_WATCH = set()
_SAMPLE_HITS = set()

def _apply_markers(text, table, passes=5):
    """Replace markers until stable, so a text may reference another text defined earlier or later."""
    for _ in range(passes):
        before = text
        for placeholder, value in table.items():
            if placeholder in _SAMPLE_WATCH and placeholder in text:
                _SAMPLE_HITS.add(placeholder)
            text = text.replace(placeholder, value)
        if text == before:
            break
    return text

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
    """Drop keys whose value is an empty string (e.g. unconfigured priceRange): better omitted than published empty."""
    if isinstance(obj, dict):
        return {k: _prune_empty(v) for k, v in obj.items() if not (isinstance(v, str) and not v.strip())}
    if isinstance(obj, list):
        return [_prune_empty(v) for v in obj]
    return obj

_LDJSON_BLOCK = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.DOTALL)

def replace_placeholders_in_content(content, html_replacements, json_replacements):
    """Replace markers in the HTML with HTML-escaped values and, inside JSON-LD blocks,
    with JSON-escaped values: a `"` or `&` in the business name breaks neither the JSON nor the attributes."""
    apply = _apply_markers
    parts, pos = [], 0
    for m in _LDJSON_BLOCK.finditer(content):
        parts.append(apply(content[pos:m.start()], html_replacements))
        parts.append(m.group(1) + apply(m.group(2), json_replacements) + m.group(3))
        pos = m.end()
    parts.append(apply(content[pos:], html_replacements))
    return ''.join(parts)

def _is_unset(val):
    """True for a value entity.json has not filled in: missing/null, or still a {{...}} marker."""
    return val is None or (isinstance(val, str) and val.startswith('{{') and val.endswith('}}'))

def _get(node, *keys):
    """Walk nested dict keys without raising when a level is missing or explicitly null
    (e.g. entity.json has no "contactPoint", or "contactPoint": null; site.json has
    "generated_content": null). Returns None, which callers turn into a default
    (`_unwrap_placeholder`, `or {}` for optional settings)."""
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node

# Sample values for the numbered slots of entity.json (knowsAbout, areaServed, hasOfferCatalog). They are used
# only when entity.json gives no value for a slot, so a half-filled site still builds; the build then warns
# if the sample value is really published (sample_slots, sample_fallback_warnings).
SAMPLE_CATEGORIES = tuple(f'Service {n}' for n in range(1, 7))
SAMPLE_CITIES = tuple(f'City {n}' for n in range(1, 5))
SAMPLE_OFFERS = (('Service 1', '$99', '99'), ('Service 2', '$149', '149'), ('Service 3', '$49/mo', '49'),
                 ('Service 4', '$299/mo', '299'), ('Service 5', '$290', '290'))
SAMPLE_FREE_OFFER = 'Free Consultation'


def _marker(name):
    return '{{' + name + '}}'


def _entity_list(business, key, noun):
    """A list field of the business node; missing or null counts as empty, any other type stops the build."""
    value = business.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        sys.exit(f'✗ BUILD FAILED: src/data/entity.json: {noun} must be a list (found {type(value).__name__})')
    return value


def _why_unset(label, noun, count, index, raw, field=None):
    """Why the slot has no value, in words a person editing entity.json can act on."""
    if index >= count:
        return f'{label} has {count} {noun[0] if count == 1 else noun[1]}'
    what = f'{noun[0]} {index + 1}' + (f' {field}' if field else '')
    return f'{label} {what} is ' + ('empty' if raw is None else 'still a {{...}} marker')


def sample_slots(business):
    """Markers computed from the numbered slots of the business node in entity.json.

    Returns (values, fallbacks). `values` maps every slot marker to the text to publish. `fallbacks` maps the
    markers that had no value in entity.json (and so got a sample value) to (group, sample, why): the build
    warns about the ones that end up in published text. A free offer found in hasOfferCatalog also yields
    {{featured_action_name}}; without one that marker stays unresolved and the build fails as before."""
    values, fallbacks = {}, {}

    def slot(name, raw, sample, group, why):
        marker = _marker(name)
        if _is_unset(raw):
            values[marker] = sample
            fallbacks[marker] = (group, sample, why)
        else:
            values[marker] = raw

    knows = _entity_list(business, 'knowsAbout', 'knowsAbout')
    for i, sample in enumerate(SAMPLE_CATEGORIES):
        raw = knows[i] if i < len(knows) else None
        slot(f'service_category_{i + 1}', raw, sample, f'knowsAbout entry {i + 1}',
             _why_unset('knowsAbout', ('entry', 'entries'), len(knows), i, raw))

    areas = _entity_list(business, 'areaServed', 'areaServed')
    for i, sample in enumerate(SAMPLE_CITIES):
        raw = areas[i].get('name') if i < len(areas) and isinstance(areas[i], dict) else None
        slot(f'city_{i + 1}', raw, sample, f'areaServed entry {i + 1}',
             _why_unset('areaServed', ('entry', 'entries'), len(areas), i, raw))

    catalog = business.get('hasOfferCatalog')
    items = catalog.get('itemListElement') if isinstance(catalog, dict) else None
    if items is not None and not isinstance(items, list):
        sys.exit('✗ BUILD FAILED: src/data/entity.json: hasOfferCatalog › itemListElement must be a list')
    offers = [o if isinstance(o, dict) else {} for o in (items or [])]
    for i, (sample_name, sample_price, sample_number) in enumerate(SAMPLE_OFFERS):
        offer = offers[i] if i < len(offers) else {}
        price = offer.get('price')
        price = None if price is None else str(price)  # an offer with no price must not publish "None"
        n = i + 1
        for suffix, raw, sample, field in (('name', offer.get('name'), sample_name, 'name'),
                                           ('price', price, sample_price, 'price'),
                                           ('price_number', price, sample_number, 'price')):
            slot(f'service_{n}_{suffix}', raw, sample, f'offer {n}',
                 _why_unset('hasOfferCatalog', ('offer', 'offers'), len(offers), i, raw, field))
    for offer in offers:
        if offer.get('price') == '0' or offer.get('price') == 0:
            raw = offer.get('name')
            slot('featured_action_name', raw, SAMPLE_FREE_OFFER, 'free offer',
                 'the offer priced 0 has no name' if raw is None else 'the name of the offer priced 0 is still a {{...}} marker')
            break
    return values, fallbacks


def free_offer_warnings(business):
    """One (where, message) when `hasOfferCatalog` has more than one offer priced 0. Only the first becomes the
    featured action (sample_slots), and DOCUMENTATION.md section 5.3 rule 4 asks for exactly one, so the others
    would silently be ordinary offers with no price. Same contract as the sample-value warnings: a warning, or an
    error in strict mode. The criterion is the one of sample_slots (price '0' or 0), nothing broader."""
    catalog = business.get('hasOfferCatalog')
    items = catalog.get('itemListElement') if isinstance(catalog, dict) else None
    if not isinstance(items, list):
        return []
    free = [o for o in items if isinstance(o, dict) and (o.get('price') == '0' or o.get('price') == 0)]
    if len(free) < 2:
        return []
    names = ', '.join(f"'{o.get('name')}'" for o in free)
    return [('src/data/entity.json',
             f"hasOfferCatalog has {len(free)} offers priced 0 ({names}): only the first, '{free[0].get('name')}', "
             f"is the featured action ({{{{featured_action_name}}}}). Keep exactly one offer priced 0 "
             f"(DOCUMENTATION.md section 5.3, rule 4).")]


def _marker_sources(markers):
    """Project files under src/ that mention any of `markers`, as {marker: [relative paths]}."""
    found = {m: [] for m in markers}
    for path in sorted((REPO / 'src').rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.html', '.json', '.txt', '.xml'):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for m in markers:
            if m in text:
                found[m].append(path.relative_to(REPO).as_posix())
    return found


def sample_fallback_warnings(fallbacks, hits):
    """One (where, message) per slot whose sample value was really published: `hits` are the markers found in
    the text the build generated. A fallback nobody uses (a service the pages no longer mention) stays silent."""
    used = [m for m in fallbacks if m in hits]
    if not used:
        return []
    sources = _marker_sources(used)
    groups = {}
    for marker in used:
        groups.setdefault(fallbacks[marker][0], []).append(marker)
    warnings = []
    for group, markers in groups.items():
        why = fallbacks[markers[0]][2]
        values = ', '.join(f"{m} → '{fallbacks[m][1]}'" for m in markers)
        files = sorted({f for m in markers for f in sources[m]})
        where = ''
        if files:
            where = ' Used in: ' + ', '.join(files[:4]) + (f' and {len(files) - 4} more.' if len(files) > 4 else '.')
        one = len(markers) == 1
        warnings.append(('src/data/entity.json',
                         f'{why}, so {values} {"is" if one else "are"} published as '
                         f'{"a sample value" if one else "sample values"}.{where} '
                         f'Add the data to entity.json or stop using the marker.'))
    return warnings


def report_lines(items, width):
    """Lines of a boxed report: each message is wrapped to `width` columns (not truncated) so the whole error is readable."""
    out = []
    for where, msg in items:
        out.extend(textwrap.wrap(f'• {where} → {msg}', width=width, subsequent_indent='  ',
                                 break_long_words=True, break_on_hyphens=False) or [''])
    return out

def menu_hrefs(header_html):
    """Internal links of the main <nav> (any level), read from the partial."""
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

def render_geo(flag, placename='', region=''):
    """geo.* tags of the page. placename = city from entity.json; region = ISO 3166-2 code (texts.json: geo_region).
    Without data the tag is not emitted: better omitted than publishing an invented location."""
    if not (flag is True or str(flag).lower() == 'true'):
        return ''
    tags = []
    if region:
        tags.append(f'<meta name="geo.region" content="{html.escape(region, quote=True)}">')
    if placename:
        tags.append(f'<meta name="geo.placename" content="{html.escape(placename, quote=True)}">')
    return '\n    '.join(tags)

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
    page_json = _prune_empty(page_json)
    entity_nodes = [_prune_empty(n) for n in entity_nodes]
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
            raise ValueError(f'duplicate JSON-LD @id "{nid}": it is already defined in src/data/entity.json. '
                             f'Rename the @id of this page node.')
        graph.append(node)
    out = {'@context': 'https://schema.org', '@graph': graph}
    return '<script type="application/ld+json">\n' + json.dumps(out, ensure_ascii=False, indent=4) + '\n</script>'

def check_unrendered(html_text, path):
    m = re.search(r'\{\{([^}]+)\}\}', html_text)
    if m:
        sys.exit(f'✗ BUILD FAILED: marker {m.group(0)} (first found on page {path}) has no value. '
                 f'Add "{m.group(1)}" to src/data/texts.json or write it directly in the page. '
                 f'If it is a derived marker (DOCUMENTATION.md section 7.1), fix its source in '
                 f'src/data/entity.json or src/data/site.json instead.')

def compose_page(front, content, layout_text, header_text, footer_text, entity_nodes, page_rel, site_name='{{site_name}}', site_url='{{site_url}}', contact_email='{{contact_email}}', whatsapp_link='{{whatsapp_link}}', service_category_1='{{service_category_1}}', service_category_2='{{service_category_2}}', location='{{location}}', featured_action_name='{{featured_action_name}}', jsonld_replacements=None):
    # Replace placeholders in the front matter title and description
    title_raw = front.get('title', '')
    description_raw = front.get('description', '')
    if jsonld_replacements:
        title_raw = _apply_markers(title_raw, jsonld_replacements)
        description_raw = _apply_markers(description_raw, jsonld_replacements)
    title = html.escape(title_raw, quote=True)
    description = html.escape(description_raw, quote=True)
    robots = html.escape(front.get('robots', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'), quote=True)
    geo_flag = front.get('geo', str(SITE_CONFIG.get('geo_enabled', True)).lower())
    canonical_mode = front.get('canonical', 'auto')
    active_href, aria_value = compute_active(page_rel, front, menu_hrefs(header_text))
    header_text = apply_active(header_text, active_href, aria_value)
    replacements = jsonld_replacements or {}
    geo = render_geo(geo_flag, replacements.get('{{city}}', ''), replacements.get('{{geo_region}}', ''))
    canonical = render_canonical(page_rel, canonical_mode)
    og_url = render_og_url(page_rel, canonical_mode)
    page_json = None
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
    if m:
        jsonld_str = m.group(1).strip()
        # Replace placeholders in the page JSON-LD before parsing
        # {{page_title}} and {{page_description}}: the page's own title and description (already resolved above),
        # so the JSON-LD does not repeat them by hand.
        jsonld_table = {k: _json_str(v) for k, v in (jsonld_replacements or {}).items()}
        jsonld_table.update({'{{page_title}}': _json_str(title_raw), '{{page_description}}': _json_str(description_raw)})
        jsonld_str = _apply_markers(jsonld_str, jsonld_table)
        try:
            page_json = json.loads(jsonld_str)
        except ValueError as e:
            raise ValueError(f'JSON-LD parse error: {e}')
        content = content[:m.start()] + content[m.end():]
        content = content.strip()
    content = content.replace('{{page_title}}', html.escape(title_raw, quote=True))
    content = content.replace('{{page_description}}', html.escape(description_raw, quote=True))
    try:
        jsonld = render_jsonld(page_json, entity_nodes)
    except ValueError as e:
        sys.exit(f'✗ BUILD FAILED: page {page_rel}: {e}')  # same style as check_unrendered: names the page, no traceback
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
    page = page.replace('{{featured_action_name}}', featured_action_name)
    check_unrendered(page, page_rel)
    return page

# What minify_css must not touch: comments (dropped), strings, unquoted url() and unicode-range.
_CSS_PROTECT = re.compile(
    r'/\*[\s\S]*?\*/'
    r'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
    r'|\burl\([^)\'"]*\)'
    r'|(?<![\w-])[uU]\+[0-9A-Fa-f?]+(?:-[0-9A-Fa-f]+)?'
)
# Full CSS number (with sign and unit): so 0.0px, -0.50em or 1.0 are normalised in one pass.
_CSS_NUMBER = re.compile(r'(?<![\w.#])(-?)(\d*\.\d+|\d+\.?)([a-zA-Z%]*)')
# Length units that can be dropped after a 0. Excludes s, ms, deg, %, fr...: a unitless 0 is invalid there.
_CSS_ZERO_UNITS = frozenset('px em rem vh vw cm mm in pt pc ex ch vmin vmax'.split())

def _css_number(m):
    sign, num, unit = m.groups()
    ip, _, fp = num.partition('.')
    ip, fp = ip.lstrip('0'), fp.rstrip('0')
    if not ip and not fp:  # zero
        # In a custom property (--x: 0px) the unit may be needed inside a later calc().
        s = m.string
        ini = max(s.rfind(c, 0, m.start()) for c in '{};') + 1
        if unit.lower() in _CSS_ZERO_UNITS and not s[ini:m.start()].lstrip().startswith('--'):
            unit = ''
        return '0' + unit
    return sign + ip + ('.' + fp if fp else '') + unit

def minify_css(css_text: str) -> str:
    # 1) Protect strings, url() and unicode-range; drop comments (one pass: a "/*" inside a string is not a comment)
    protected = []
    def protect(m):
        if m.group(0).startswith('/*'):
            return ''
        protected.append(m.group(0))
        return f'__STR_{len(protected)-1}__'
    css = _CSS_PROTECT.sub(protect, css_text)

    # 2) Basic spacing
    css = re.sub(r'\s+', ' ', css)
    css = css.replace(' }', '}').replace(' {', '{').replace(': ', ':').replace(' ;', ';')
    css = re.sub(r';\s*}', '}', css)

    # 3) Math functions: inside calc()/min()/max()/clamp() only what is safe is compacted.
    #    "+" and "-" are left alone (CSS requires spaces around the operators, and "--x" or "-1px" are not operators).
    maths = []
    def extract_math(match):
        inner = re.sub(r'\s+', ' ', match.group(2))
        inner = re.sub(r'\s*,\s*', ',', inner)
        inner = re.sub(r'\(\s+', '(', inner)
        inner = re.sub(r'\s+\)', ')', inner).strip()
        maths.append(f'{match.group(1)}({inner})')
        return f'__MATH_{len(maths)-1}__'
    pattern = r'\b(calc|min|max|clamp)\(([^()]*(?:\([^()]*\)[^()]*)*)\)'
    while re.search(pattern, css):
        css = re.sub(pattern, extract_math, css)

    # 4) Numbers: 0px -> 0, 0.5 -> .5, 1.0 -> 1, 1.50 -> 1.5, 0.0px -> 0
    css = _CSS_NUMBER.sub(_css_number, css)

    # 5) Short hex colours: #AABBCC -> #ABC, #AABBCCDD -> #ABCD
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3(?![0-9a-fA-F])',
        r'#\1\2\3', css
    )
    css = re.sub(
        r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3([0-9a-fA-F])\4(?![0-9a-fA-F])',
        r'#\1\2\3\4', css
    )

    # 6) Compact !important
    css = re.sub(r'\s*!\s*important\b', '!important', css)

    # 7) Spacing around punctuation. A space after ")" or before ":" can be significant
    #    (descendant combinator in "a:not(.b) .c" or "a :hover"; "and" in "(a) and (b)"), so it is kept.
    css = re.sub(r'\s*([{};,>~])\s*', r'\1', css)
    css = re.sub(r'\(\s+', '(', css)
    css = re.sub(r'\s+\)', ')', css)
    css = re.sub(r'\[\s+', '[', css)
    css = re.sub(r'\s+\]', ']', css)
    css = re.sub(r'\s*\+\s*', '+', css)

    # 8) Restore math functions (they can be nested) and strings
    while '__MATH_' in css:
        css = re.sub(r'__MATH_(\d+)__', lambda m: maths[int(m.group(1))], css)
    css = re.sub(r'__STR_(\d+)__', lambda m: protected[int(m.group(1))], css)

    # 9) Final cleanup
    css = re.sub(r';;+', ';', css)
    return css.strip()

# Inline elements: the space between two of them is part of the visible text.
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
            # \x00 does not appear in normal HTML: a collision is practically impossible
            return f'\x00P{idx}\x00'
        return re.sub(pattern, replacer, html_text, flags=flags)

    # 1) Protect sensitive blocks (scripts, styles, pre, textarea)
    html_text = protect(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE, is_ld_json)
    html_text = protect(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<pre[^>]*>.*?</pre>', re.DOTALL | re.IGNORECASE)
    html_text = protect(r'<textarea[^>]*>.*?</textarea>', re.DOTALL | re.IGNORECASE)

    # 2) Comments
    html_text = re.sub(r'<!--[\s\S]*?-->', '', html_text)

    # 3) Protect quoted attribute values BEFORE collapsing whitespace
    #    This fixes the bug: alt="a  b", content="x   y", title="z  w" stay intact.
    attr_strings = []
    def protect_attr(m):
        attr_strings.append(m.group(0))
        return f'\x00A{len(attr_strings)-1}\x00'
    html_text = re.sub(r'="[^"]*"|=\'[^\']*\'', protect_attr, html_text)

    # 4) Collapse whitespace between tags. Between two sibling inline elements
    #    (<strong>a</strong> <small>b</small>) the space is visible on screen: a single one is kept
    #    (temporary \x01). Between blocks, or between a container and its content, it is removed.
    html_text = re.sub(
        r'(<(/?)([a-zA-Z][\w-]*)[^<>]*>)\s+(?=<(/?)([a-zA-Z][\w-]*))',
        lambda m: m.group(1) + ('\x01' if (m.group(3).lower() in INLINE_TAGS and m.group(5).lower() in INLINE_TAGS
                                           and not m.group(4)
                                           and (m.group(2) or m.group(3).lower() in VOID_INLINE_TAGS)) else ''),
        html_text)
    html_text = re.sub(r'>\s+<', '><', html_text)
    html_text = html_text.replace('\x01', ' ')

    # 5) Collapse repeated spaces (now safe: only structural spaces between attributes remain)
    html_text = re.sub(r'\s{2,}', ' ', html_text)

    # 6) Remove spaces before > (leaving self-closing /> alone)
    html_text = re.sub(r'\s+>', '>', html_text)

    html_text = html_text.strip()

    # 7) Restore attribute values
    for i, s in enumerate(attr_strings):
        html_text = html_text.replace(f'\x00A{i}\x00', s)

    # 8) Restore protected blocks (with JSON-LD minified)
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
                except ValueError:
                    new_tag = original  # Preserve the original block when JSON-LD cannot be parsed.
            else:
                new_tag = original
            html_text = html_text.replace(f'\x00P{i}\x00', new_tag)
        else:
            html_text = html_text.replace(f'\x00P{i}\x00', original)

    return html_text

# --------------------------------------------------------------------------- collections (Guides and Blog)

COLLECTION_DIRS = {'guides': 'guide', 'blog': 'article'}   # collection -> front matter `type`


def load_collection_paths():
    """URL path (= folder in src/pages/) of each collection; `site.json › collection_paths` overrides it."""
    paths = {'guides': 'guides', 'blog': 'blog'}
    custom = SITE_CONFIG.get('collection_paths', {})
    if not isinstance(custom, dict) or not set(custom) <= set(paths):
        raise SystemExit('✗ BUILD FAILED: collection_paths in src/data/site.json must be an object '
                         'with only the keys "guides" and "blog"')
    paths.update(custom)
    for coll, path in paths.items():
        if not isinstance(path, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', path):
            raise SystemExit(f'✗ BUILD FAILED: collection_paths "{coll}" must be a lowercase ASCII slug '
                             f'with hyphens (current value: {path!r})')
    if paths['guides'] == paths['blog']:
        raise SystemExit('✗ BUILD FAILED: collection_paths "guides" and "blog" must be different')
    return paths


COLLECTION_PATHS = load_collection_paths()
GUIDES_URL = f'/{COLLECTION_PATHS["guides"]}/'
BLOG_URL = f'/{COLLECTION_PATHS["blog"]}/'
COLLECTION_TOPICS = list(SITE_CONFIG.get('collection_topics', ['Topic 1', 'Topic 2', 'Topic 3', 'Topic 4', 'Topic 5']))
BLOG_MIN_VISIBLE = 3

class CollectionError(Exception):
    """Incomplete or invalid collection front matter (the build stops with the full detail)."""

def iso_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None

def format_long_date(iso, locale=None):
    d = iso_date(iso)
    return t('long_date', locale).format(day=d.day, month=t('months', locale)[d.month - 1], year=d.year)

def load_collections(pages_dir):
    """Read and validate the pieces in src/pages/<guides path>/*/ and src/pages/<blog path>/*/.

    Returns {'guides': [...], 'blog': [...]}; each piece is a dict with rel, slug, path, front and the
    already-normalised collection fields. Raises CollectionError with ALL the problems found.
    """
    pages_dir = Path(pages_dir)
    problems = []
    pieces = {'guides': [], 'blog': []}
    for coll, expected_type in COLLECTION_DIRS.items():
        path = COLLECTION_PATHS[coll]
        base = pages_dir / path
        if not base.is_dir():
            continue
        for f in sorted(base.rglob('*.html')):
            rel_f = f.relative_to(pages_dir).as_posix()
            parts = f.relative_to(base).parts
            if len(parts) != 2 or parts[1] != 'index.html':
                if parts == ('index.html',):
                    problems.append(f'{rel_f}: the /{path}/ index is generated; delete this file.')
                else:
                    problems.append(f'{rel_f}: {coll} pieces must be {path}/<slug>/index.html.')
                continue
            front, _ = parse_front_matter(read_text(f))
            where = f'{rel_f}'
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', parts[0]):
                problems.append(f'{where}: the slug "{parts[0]}" must be lowercase, without accents, and hyphenated.')
            for key in ('type', 'topic', 'published', 'updated', 'summary', 'service'):
                if not front.get(key):
                    problems.append(f'{where}: missing "{key}" in the front matter.')
            if front.get('type') and front['type'] != expected_type:
                problems.append(f'{where}: type "{front["type"]}" is not valid in {path}/ (expected "{expected_type}").')
            if front.get('topic') and front['topic'] not in COLLECTION_TOPICS:
                problems.append(f'{where}: topic "{front["topic"]}" is not in the taxonomy ({" · ".join(COLLECTION_TOPICS)}).')
            pub, upd = iso_date(front.get('published')), iso_date(front.get('updated'))
            if front.get('published') and pub is None:
                problems.append(f'{where}: published "{front["published"]}" is not an ISO date (YYYY-MM-DD).')
            if front.get('updated') and upd is None:
                problems.append(f'{where}: updated "{front["updated"]}" is not an ISO date (YYYY-MM-DD).')
            if pub and upd and upd < pub:
                problems.append(f'{where}: updated ({front["updated"]}) is earlier than published ({front["published"]}).')
            svc = front.get('service')
            if svc:
                if not (svc.startswith('/') and svc.endswith('/')) or not (pages_dir / svc.strip('/') / 'index.html').is_file():
                    problems.append(f'{where}: service "{svc}" does not point to an existing page.')
            if 'title' not in front or 'description' not in front:
                problems.append(f'{where}: missing title or description.')
            rel = f'/{path}/{parts[0]}/'
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
                problems.append(f'{where}: related allows at most 2 links and has {len(p["related"])}.')
            for r in p['related']:
                if r == p['rel']:
                    problems.append(f'{where}: related cannot point to the piece itself.')
                elif r not in known:
                    problems.append(f'{where}: related "{r}" is not an existing guide or article.')
    # collection `type` outside its folder
    for f in sorted(pages_dir.rglob('*.html')):
        top = f.relative_to(pages_dir).parts[0]
        if top in COLLECTION_PATHS.values():
            continue
        front, _ = parse_front_matter(read_text(f))
        if front.get('type') in COLLECTION_DIRS.values():
            problems.append(f'{f.relative_to(pages_dir).as_posix()}: type "{front["type"]}" is only allowed inside {COLLECTION_PATHS["guides"]}/ or {COLLECTION_PATHS["blog"]}/.')
    if problems:
        raise CollectionError('\n'.join('  - ' + m for m in problems))
    return pieces

def blog_state(articles):
    """'none' (0 articles: no blog index), 'hidden' (1-2: index noindex and not announced) or 'visible' (>= 3)."""
    n = len(articles)
    if n == 0:
        return 'none'
    return 'visible' if n >= BLOG_MIN_VISIBLE else 'hidden'

def blog_visible(articles):
    """True if the Blog is announced (menu, footer, sitemap, llms.txt) and indexable."""
    return blog_state(articles) == 'visible'

def _breadcrumb_html(label):
    home = ('<a href="/"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
            '<path d="M9 22V12h6v10"/></svg>' + html.escape(t('breadcrumb_home')) + '</a>')
    return (f'<nav class="breadcrumb" aria-label="{html.escape(t("breadcrumb_label"), quote=True)}"><ol><li>{home}</li>'
            f'<li><span>{html.escape(label)}</span></li></ol></nav>')

def _lead_strip_html(has_email=True, has_whatsapp=True):
    """CTA of the collection index, configurable per site with no business data in the engine.

    The contact line adapts to the contact data the site really has: email and WhatsApp, only one of
    them (locale keys `lead_strip_contact_email_only` / `lead_strip_contact_whatsapp_only`) or, with
    neither, no line at all, so no link with an empty href is ever generated.
    `generated_content.lead_strip.contact_html` replaces the whole line (it may use {{markers}}; an
    empty string removes it)."""
    cfg = _get(SITE_CONFIG, 'generated_content', 'lead_strip') or {}
    action_url = str(cfg.get('action_url', '/featured-action/'))
    action_label = str(cfg.get('action_label', t('lead_strip_action_label')))
    eyebrow = str(cfg.get('eyebrow', t('lead_strip_eyebrow')))
    headline = str(cfg.get('headline', t('lead_strip_headline')))
    lead_html = cfg.get('lead_html')
    if lead_html is None:
        action_link = f'<a href="{html.escape(action_url, quote=True)}">{html.escape(action_label)}</a>'
        lead_html = t('lead_strip_lead_html').replace('{action_link}', action_link)
    button = str(cfg.get('button', t('lead_strip_button')))
    contact = cfg.get('contact_html')
    if contact is None:
        key = {(True, True): 'lead_strip_contact', (True, False): 'lead_strip_contact_email_only',
               (False, True): 'lead_strip_contact_whatsapp_only'}.get((bool(has_email), bool(has_whatsapp)))
        email_link = '<a href="mailto:{{contact_email}}" class="link-accent">{{contact_email}}</a>'
        whatsapp_link = '<a href="{{whatsapp_link}}" target="_blank" rel="noopener noreferrer" class="link-accent">WhatsApp</a>'
        contact = t(key).replace('{email}', email_link).replace('{whatsapp}', whatsapp_link) if key else ''
    contact = str(contact)
    contact_line = (f'\n                <span class="text-muted-lg mt-15">{contact}</span>' if contact.strip() else '')
    return f'''<section class="lead-strip page-width">
            <div>
                <p class="eyebrow">{html.escape(eyebrow)}</p>
                <h2>{html.escape(headline)}</h2>
                <p class="lead mt-18">{lead_html}</p>
            </div>
            <div class="lead-strip-inner">
                <a class="button primary" href="{html.escape(action_url, quote=True)}">{html.escape(button)}</a>{contact_line}
            </div>
        </section>'''

def _index_jsonld(rel, title, description, label, last_mod, items):
    url = SITE_URL + rel
    graph = [
        {
            '@type': 'CollectionPage', '@id': url + '#webpage', 'url': url, 'name': title,
            'description': description, 'inLanguage': IN_LANGUAGE,
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
                {'@type': 'ListItem', 'position': 1, 'name': t('breadcrumb_home'), 'item': SITE_URL + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': label},
            ],
        },
    ]
    data = {'@context': 'https://schema.org', '@graph': graph}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=4) + '\n</script>'

def _card_html(p, link_text, with_date):
    link_text = html.escape(link_text, quote=True)  # it lands in text and in an aria-label; a locale override may carry `"` or `&`
    title = html.escape(p['title'].split(' | ')[0], quote=True)
    date = (f'<time class="post-meta" datetime="{p["published"]}">{format_long_date(p["published"])}</time>'
            if with_date else '')
    return f"""<article>
                    <span class="chip">{html.escape(p['topic'])}</span>
                    {date}
                    <h3>{title}</h3>
                    <p>{html.escape(p['summary'])}</p>
                    <a href="{p['rel']}" aria-label="{link_text}: {title}">{link_text}</a>
                </article>"""

def render_home_resources(collections):
    """Home section linking to the guides and blog indexes (only to what exists and is announced).

    It is the contextual link, from a <main>, that those indexes need so they are not orphaned.
    Returns '' if there are no guides and no visible blog."""
    cards = []
    if collections['guides']:
        cards.append((t('home_resources_guides_title'), t('home_resources_guides_text'),
                         GUIDES_URL, t('home_resources_guides_link')))
    if blog_visible(collections['blog']):
        cards.append((t('home_resources_blog_title'), t('home_resources_blog_text'),
                         BLOG_URL, t('home_resources_blog_link')))
    if not cards:
        return ''
    cards = '\n                '.join(
        f'<article>\n                    <h3>{card_title}</h3>\n                    <p>{text}</p>\n                    <a href="{href}">{link}</a>\n                </article>'
        for card_title, text, href, link in cards)
    return f"""<section class="section page-width" aria-labelledby="home-resources">
            <h2 id="home-resources">{t('home_resources_heading')}</h2>
            <div class="service-grid">
                {cards}
            </div>
        </section>"""

def render_guides_index(guides, lead_strip=None):
    """Build the guides index using editorial copy configured per site."""
    cfg = _get(SITE_CONFIG, 'generated_content', 'guides_index') or {}
    title = str(cfg.get('title', t('guides_index_title')))
    description = str(cfg.get('description', t('guides_index_description')))
    heading = str(cfg.get('heading', t('guides_index_heading')))
    lead = str(cfg.get('lead', t('guides_index_lead')))
    intro = str(cfg.get('intro', t('guides_index_intro')))
    extra_heading = str(cfg.get('extra_heading', t('guides_index_extra_heading')))
    extra_paragraphs = cfg.get('extra_paragraphs', [])
    last_mod = max(p['updated'] for p in guides)
    sections = []
    n = 0
    for topic in COLLECTION_TOPICS:
        group = sorted((p for p in guides if p['topic'] == topic), key=lambda p: (p['published'], p['slug']))
        if not group:
            continue
        n += 1
        cards = '\n                '.join(_card_html(p, t('card_read_guide'), False) for p in group)
        sections.append(f"""        <section class="section page-width" aria-labelledby="guides-topic-{n}">
            <h2 id="guides-topic-{n}">{html.escape(topic)}</h2>
            <div class="service-grid">
                {cards}
            </div>
        </section>""")
    ordered = [p for topic in COLLECTION_TOPICS for p in sorted((q for q in guides if q['topic'] == topic), key=lambda q: (q['published'], q['slug']))]
    extra_section = ''
    if extra_paragraphs:
        paragraphs = '\n            '.join(f'<p>{html.escape(str(paragraph))}</p>' for paragraph in extra_paragraphs)
        extra_section = f"""<section class="section page-width" aria-labelledby="guides-how">
            <h2 id="guides-how">{html.escape(extra_heading)}</h2>
            {paragraphs}
        </section>"""
    content = f"""{_index_jsonld(GUIDES_URL, title, description, t('nav_guides'), last_mod, ordered)}

<main id="main">
        <section class="inner-hero page-width">
            {_breadcrumb_html(t('nav_guides'))}
            <p class="eyebrow">{html.escape(t('nav_guides'))}</p>
            <h1>{html.escape(heading)}</h1>
            <p class="lead">{lead}</p>
            <p class="mt-18">{intro}</p>
            {cfg.get('intro_extra_html', '')}
        </section>

{chr(10).join(sections)}

        {extra_section}
        {lead_strip if lead_strip is not None else _lead_strip_html()}
    </main>"""
    front = {'title': title, 'description': description, 'canonical': 'auto', 'geo': 'true'}
    return front, content

def render_blog_index(articles, guides_exist, lead_strip=None):
    """Build the blog index using editorial copy configured per site."""
    cfg = _get(SITE_CONFIG, 'generated_content', 'blog_index') or {}
    title = str(cfg.get('title', t('blog_index_title')))
    description = str(cfg.get('description', t('blog_index_description')))
    heading = str(cfg.get('heading', t('blog_index_heading')))
    lead_template = str(cfg.get('lead', t('blog_index_lead')))
    intro = str(cfg.get('intro', t('blog_index_intro')))
    criteria_heading = str(cfg.get('criteria_heading', t('blog_index_criteria_heading')))
    criteria_paragraphs = cfg.get('criteria_paragraphs', [])
    ordered = sorted(articles, key=lambda p: (p['published'], p['updated'], p['slug']), reverse=True)
    last_mod = max(p['updated'] for p in articles)
    cards = '\n                '.join(_card_html(p, t('card_read_article'), True) for p in ordered)
    guides_txt = t('blog_lead_guides_link').replace('{guides_url}', GUIDES_URL) if guides_exist else t('blog_lead_guides_text')
    lead = lead_template.replace('{guides_txt}', guides_txt)
    criteria_section = ''
    if criteria_paragraphs:
        paragraphs = '\n            '.join(f'<p>{html.escape(str(paragraph))}</p>' for paragraph in criteria_paragraphs)
        criteria_section = f"""<section class="section page-width" aria-labelledby="blog-criteria">
            <h2 id="blog-criteria">{html.escape(criteria_heading)}</h2>
            {paragraphs}
        </section>"""
    content = f"""{_index_jsonld(BLOG_URL, title, description, t('nav_blog'), last_mod, ordered)}

<main id="main">
        <section class="inner-hero page-width">
            {_breadcrumb_html(t('nav_blog'))}
            <p class="eyebrow">{html.escape(t('nav_blog'))}</p>
            <h1>{html.escape(heading)}</h1>
            <p class="lead">{lead}</p>
            <p class="mt-18">{intro}</p>
        </section>

        <section class="section page-width" aria-labelledby="blog-list">
            <h2 id="blog-list">{html.escape(str(cfg.get('list_heading', t('blog_index_list_heading'))))}</h2>
            <div class="service-grid">
                {cards}
            </div>
        </section>

        {criteria_section}
        {lead_strip if lead_strip is not None else _lead_strip_html()}
    </main>"""
    front = {'title': title, 'description': description, 'canonical': 'auto', 'geo': 'true'}
    if blog_state(articles) != 'visible':
        front['robots'] = 'noindex, follow'
    return front, content


# --------------------------------------------------------------------------- generated sitemap and llms.txt

# Base sitemap order; new pages follow: the guides index + guides, the blog index + articles.
SITEMAP_BASE_ORDER = list(SITE_CONFIG.get('sitemap_base_order', ['/', '/services/', '/services/sample-service/', '/pricing/', '/about/', '/contact/', '/featured-action/']))

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

def build_sitemap(pages_data, collections, out):
    """Write out/sitemap.xml with the indexable pages (not 404, not noindex)."""
    entries = {}
    for rel, front, out_path in pages_data:
        robots = re.search(r'<meta name="robots" content="([^"]*)"', read_text(out_path))
        if rel == '/404.html' or (robots and 'noindex' in robots.group(1).lower()):
            continue
        lm = page_date_modified(out_path, front)
        if lm is None:
            raise ValueError(f'{rel}: no dateModified in the JSON-LD and no "updated" in the front matter; add "updated: YYYY-MM-DD".')
        upd = front.get('updated')
        if upd and upd != lm:
            raise ValueError(f'{rel}: front matter "updated: {upd}" differs from the JSON-LD dateModified ({lm}); '
                             f'use the same date in both.')
        entries[rel] = lm
    order = [r for r in SITEMAP_BASE_ORDER if r in entries]
    for coll in ('guides', 'blog'):
        idx = f'/{COLLECTION_PATHS[coll]}/'
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
    if coll == 'guides':
        return [p for t in COLLECTION_TOPICS for p in sorted((q for q in pieces if q['topic'] == t), key=lambda q: (q['published'], q['slug']))]
    return sorted(pieces, key=lambda p: (p['published'], p['updated'], p['slug']), reverse=True)

def _piece_name(p):
    return p['title'].split(' | ')[0]

def render_llms_guides(guides):
    if not guides:
        return ''
    lines = [f'## {t("nav_guides")}', '',
             f'- [{GUIDES_URL}]({SITE_URL}{GUIDES_URL}): {t("llms_guides_description")}']
    lines += [f'- [{_piece_name(p)}]({SITE_URL}{p["rel"]}): {p["summary"]}' for p in _ordered_pieces('guides', guides)]
    return '\n'.join(lines) + '\n\n'

def render_llms_blog(articles):
    if not blog_visible(articles):
        return ''
    lines = [f'## {t("nav_blog")}', '',
             f'- [{BLOG_URL}]({SITE_URL}{BLOG_URL}): {t("llms_blog_description")}']
    lines += [f'- [{_piece_name(p)}]({SITE_URL}{p["rel"]}) ({p["published"]}): {p["summary"]}' for p in _ordered_pieces('blog', articles)]
    return '\n'.join(lines) + '\n\n'

def render_llms_sitemap_extra(order):
    """Guide and blog URLs for the "Sitemap" section of llms.txt (the same ones that appear in sitemap.xml)."""
    return ''.join(f'- {SITE_URL}{rel}\n' for rel in order if rel.startswith((GUIDES_URL, BLOG_URL)))

def render_llms(text, collections, sitemap_order=(), replacements=None):
    text = text.replace('{{llms_sitemap_extra}}', render_llms_sitemap_extra(sitemap_order))
    text = text.replace('{{llms_guides}}', render_llms_guides(collections['guides']))
    text = text.replace('{{llms_blog}}', render_llms_blog(collections['blog']))
    if replacements:  # the generated blocks may carry {{markers}} (e.g. a locale override that names the business)
        text = _apply_markers(text, replacements)
    m = re.search(r'\{\{[^}]+\}\}', text)
    if m:
        raise ValueError(f'unresolved marker {m.group(0)} in llms.txt')
    return text

def print_report(success, errors, warnings, generated, total_bytes, out, minify,
                 git_branch, git_commit, build_time,
                 total_html_before, total_html_after, css_size_before, css_size_after):
    COL = 50
    LBL = 15
    W = 2 + LBL + 2 + COL  # interior width
    BANNER = str(SITE_CONFIG.get('build_banner', SITE_CONFIG.get('site_name', 'Legible') + ' • Static site generator'))

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
        centered('⚠  Warnings')
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

def get_git_info():
    git_branch = os.environ.get('RENDER_GIT_BRANCH')
    git_commit = os.environ.get('RENDER_GIT_COMMIT')
    if not git_branch:
        try:
            git_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=REPO, text=True, stderr=subprocess.DEVNULL).strip()
            if git_branch == 'HEAD':
                git_branch = None
        # Git metadata is optional; any Git failure must not abort the build.
        except Exception:
            pass
    if not git_branch:
        git_branch = 'unknown'
    if not git_commit:
        try:
            git_commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, text=True, stderr=subprocess.DEVNULL).strip()
        # Git metadata is optional; fall back to 'unknown' on any Git failure.
        except Exception:
            git_commit = 'unknown'
    else:
        git_commit = git_commit[:7]
    return git_branch, git_commit


def check_out_dir(out):
    """Abort if the output folder would put the project at risk (the build empties it entirely)."""
    out = Path(out).resolve()
    protected = [REPO / 'src', REPO / 'legible']
    at_risk = (
        out == REPO or out in REPO.parents
        or any(out == p or p in out.parents for p in protected)
        or any((out / p.name).exists() for p in protected)
    )
    if at_risk:
        print(f'✗ BUILD ABORTED: the output folder {out} is the project, src/, legible/ or contains one of them, '
              'and would be emptied. Use a folder of its own, such as dist/.', file=sys.stderr)
        raise SystemExit(1)

def _unwrap_placeholder(val, default):
    """If val is a {{...}} placeholder or missing (None), return default; otherwise return val.
    Contact data (email, telephone, address...) is optional: an absent field must fall back
    to site.json cleanly instead of leaking a Python None into the page."""
    return default if _is_unset(val) else val


def _prepare_output(out, minify):
    """Empty the output folder, copy src/static/ and write the (optionally minified) CSS.
    Returns the size of the CSS before and after minifying."""
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
    return css_size_before, css_size_after


def _main_node(entity):
    """The main entity node of entity.json: the one whose @id ends in /#business, whatever its @type
    (a Restaurant, a Dentist, a SoftwareApplication, a Person...). Older sites whose node has no such @id
    still work through the first ProfessionalService. With neither, the build stops and names the @id."""
    nodes = [n for n in entity if isinstance(n, dict)]
    for n in nodes:
        if str(n.get('@id', '')).endswith('/#business'):
            return n
    for n in nodes:
        if n.get('@type') == 'ProfessionalService':
            return n
    sys.exit('✗ BUILD FAILED: src/data/entity.json: no main node. Add a node with "@id": "{{site_url}}/#business" '
             '(its "@type" can be any Schema.org type): the business facts are read from it.')


def _site_values():
    """Read entity.json and site.json and compute the derived values (DOCUMENTATION.md section 3.2).

    Returns a namespace with the entity nodes, the business node, the values the pages receive, the sample
    fallbacks to watch, the guide/blog collections and `derived`, the table of derived markers."""
    entity = json.loads(read_text(REPO / 'src' / 'data' / 'entity.json'))
    # Read values from entity.json for global placeholders
    business = _main_node(entity)
    site_name = _unwrap_placeholder(business.get('name'), str(SITE_CONFIG.get('site_name', '')))
    contact_email = _unwrap_placeholder(business.get('email'), str(SITE_CONFIG.get('contact_email', '')))
    phone_value = _unwrap_placeholder(_get(business, 'contactPoint', 'telephone'), str(SITE_CONFIG.get('phone_e164', '')))
    whatsapp_message = str(SITE_CONFIG.get('whatsapp_message', ''))
    whatsapp_link = phone_value if phone_value.startswith('https://') else ''
    whatsapp_base = whatsapp_link  # link without text: pages with their own message append "?text=…"
    if phone_value and not phone_value.startswith('https://'):
        phone_digits = re.sub(r'\D', '', phone_value)
        if phone_digits:
            whatsapp_base = 'https://wa.me/' + phone_digits
            whatsapp_link = whatsapp_base
            if whatsapp_message:
                whatsapp_link += '?text=' + quote(whatsapp_message, safe='')
    # Extra values for the footer
    city = _unwrap_placeholder(_get(business, 'address', 'addressLocality'), str(SITE_CONFIG.get('city', '')))
    region = _unwrap_placeholder(_get(business, 'address', 'addressRegion'), str(SITE_CONFIG.get('region', '')))
    location = f"{city}, {region}"
    # Numbered slots (categories, cities, offers): entity.json value, else a sample value that the build
    # warns about if it is published (sample_slots). Watching starts before any marker is applied.
    slots, sample_fallbacks = sample_slots(business)
    _SAMPLE_WATCH.clear()
    _SAMPLE_HITS.clear()
    _SAMPLE_WATCH.update(sample_fallbacks)
    area_served = _entity_list(business, 'areaServed', 'areaServed')
    if not all(isinstance(c, dict) for c in area_served):
        sys.exit('✗ BUILD FAILED: src/data/entity.json: every areaServed entry must be an object such as '
                 '{"@type": "City", "name": "Your City"}')
    target_audience = (t('target_audience').format(areas=', '.join([c.get('name', '') for c in area_served[:3]]))
                       if area_served else '{{target_audience}}')
    featured_action_name = slots.get('{{featured_action_name}}', '{{featured_action_name}}')
    try:
        collections = load_collections(REPO / 'src' / 'pages')
    except CollectionError as e:
        print('✗ BUILD FAILED: invalid Guides/Blog front matter\n' + str(e), file=sys.stderr)
        raise SystemExit(1)

    derived = {
        '{{target_audience}}': target_audience,
        '{{site_name}}': site_name,
        '{{site_url}}': SITE_URL,
        '{{lang}}': LANG,
        '{{og_locale}}': OG_LOCALE,
        '{{in_language}}': IN_LANGUAGE,
        '{{contact_email}}': contact_email,
        '{{whatsapp_link}}': whatsapp_link,
        '{{whatsapp_base}}': whatsapp_base,
        '{{phone_e164}}': phone_value,
        '{{phone_digits}}': re.sub(r'\D', '', phone_value) if phone_value and not phone_value.startswith('https://') else '',
        '{{city}}': city,
        '{{region}}': region,
        '{{location}}': location,
        **slots,
        '{{price_range}}': _unwrap_placeholder(business.get('priceRange'), str(SITE_CONFIG.get('price_range', ''))),
        '{{featured_action_name}}': featured_action_name,
        '{{home_resources}}': render_home_resources(collections),
    }
    # URL-encoded variants (for use inside "?text="): "Service 1" -> "Service%201"
    for _k in ('featured_action_name', 'service_1_name'):
        derived['{{' + _k + '_url}}'] = quote(derived['{{' + _k + '}}'], safe='')
    return SimpleNamespace(
        entity=entity, business=business, site_name=site_name, contact_email=contact_email,
        whatsapp_link=whatsapp_link, location=location,
        service_category_1=slots['{{service_category_1}}'], service_category_2=slots['{{service_category_2}}'],
        featured_action_name=featured_action_name, sample_fallbacks=sample_fallbacks,
        collections=collections, derived=derived)


def _marker_tables(derived):
    """Build the marker table (DOCUMENTATION.md section 2.4, step 5). Returns `(replacements, html_replacements)`:
    the first has the plain values (texts.json under the derived values, which win), the second the same values
    escaped for HTML where they are computed."""
    # Business texts: src/data/texts.json (key without braces -> text). Whatever is computed from entity.json wins.
    texts_path = REPO / 'src' / 'data' / 'texts.json'
    try:
        texts = json.loads(read_text(texts_path)) if texts_path.exists() else {}
    except (OSError, ValueError) as e:
        sys.exit(f'✗ BUILD FAILED: could not read src/data/texts.json: {e}')
    if not isinstance(texts, dict):
        sys.exit('✗ BUILD FAILED: src/data/texts.json must contain a JSON object')
    config_text = SITE_CONFIG.get('text', {})
    if isinstance(config_text, dict):
        texts = {**config_text, **texts}
    replacements = {'{{' + k + '}}': str(v) for k, v in texts.items()}
    derived = dict(derived)
    if SITE_CONFIG.get('geo_region_code'):
        derived['{{geo_region}}'] = str(SITE_CONFIG['geo_region_code'])
    replacements.update(derived)
    # Values for HTML: what is computed from entity.json/site.json is plain text and is escaped (`&`, `"`, `<`);
    # texts in texts.json may carry HTML on purpose and {{home_resources}} is already-generated HTML.
    html_replacements = dict(replacements)
    for _k, _v in derived.items():
        if _k != '{{home_resources}}':
            html_replacements[_k] = html.escape(str(_v), quote=True)
    return replacements, html_replacements


def _shared_parts(layout, header, footer, entity, collections, replacements, html_replacements):
    """Resolve the markers in the layout, the partials and the entity nodes, and fill the navigation, footer-blog
    and year markers. Returns `(layout, header, footer, entity_nodes)`."""
    layout = replace_placeholders_in_content(layout, html_replacements, replacements)
    header = replace_placeholders_in_content(header, html_replacements, replacements)
    footer = replace_placeholders_in_content(footer, html_replacements, replacements)
    entity_nodes = [_replace_placeholders_in_json(node, replacements) for node in entity]
    # Conditional Blog markers (before menu_hrefs, so the active state works)
    nav_blog = f'<li><a href="{BLOG_URL}">{html.escape(t("nav_blog"))}</a></li>' if blog_visible(collections['blog']) else ''
    nav_guides = f'<li><a href="{GUIDES_URL}">{html.escape(t("nav_guides"))}</a></li>' if collections['guides'] else ''
    header = header.replace('{{nav_blog}}', nav_blog).replace('{{nav_guides}}', nav_guides)
    footer = footer.replace('{{footer_blog}}', nav_blog).replace('{{nav_guides}}', nav_guides)
    footer = footer.replace('{{year}}', str(datetime.now().year))
    return layout, header, footer, entity_nodes


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


def _write_pages(writer, errors):
    """Write every page of src/pages/. A page with no title or description is an error and is skipped."""
    pages_dir = REPO / 'src' / 'pages'
    for page_path in sorted(pages_dir.rglob('*.html')):
        front, content = parse_front_matter(read_text(page_path))
        if 'title' not in front or 'description' not in front:
            errors.append((str(page_path.relative_to(REPO)), 'missing title or description'))
            continue
        rel_parts = list(page_path.relative_to(pages_dir).parts)
        if rel_parts == ['404.html']:
            page_rel = '/404.html'
        else:
            if rel_parts[-1] == 'index.html':
                rel_parts.pop()  # only the final file name: a folder such as "my-index.html-guide" stays intact
            page_rel = '/' + '/'.join(rel_parts)
            if page_rel != '/':
                page_rel += '/'
        writer.emit(writer.out / page_path.relative_to(pages_dir), page_rel, front, content)


def _write_indexes(writer, site):
    """Write the generated collection indexes (they do not exist as files in src/pages)."""
    collections = site.collections
    # The closing strip of the indexes only offers the contact channels the site has (email, WhatsApp).
    lead_strip = _lead_strip_html(bool(str(site.contact_email).strip()), bool(site.whatsapp_link))
    generated_indexes = []
    if collections['guides']:
        generated_indexes.append((GUIDES_URL,) + render_guides_index(collections['guides'], lead_strip))
    if blog_state(collections['blog']) != 'none':
        generated_indexes.append((BLOG_URL,) + render_blog_index(collections['blog'], bool(collections['guides']), lead_strip))
    for page_rel, front, content in generated_indexes:
        writer.emit(writer.out / page_rel.strip('/') / 'index.html', page_rel, front, content)


def _write_site_files(out, collections, pages_data, replacements):
    """Write sitemap.xml and resolve the markers of robots.txt and llms.txt."""
    try:
        sitemap_order = build_sitemap(pages_data, collections, out)
        robots_path = out / 'robots.txt'
        if robots_path.exists():
            robots_text = read_text(robots_path)
            robots_text = _apply_markers(robots_text, replacements)
            write_text(robots_path, robots_text)
        llms_path = out / 'llms.txt'
        if llms_path.exists():
            llms_text = read_text(llms_path)
            # Replace global placeholders in llms.txt
            llms_text = _apply_markers(llms_text, replacements)
            llms_path.write_text(render_llms(llms_text, collections, sitemap_order, replacements), encoding='utf-8')
    except ValueError as e:
        print(f'✗ BUILD FAILED: {e}', file=sys.stderr)
        raise SystemExit(1)


def _final_checks(out, strict, no_validate, site, errors, warnings):
    """Add the build's own warnings and the validator's findings to `errors` and `warnings`."""
    # Sample values that ended up in published text: a warning, or an error in strict mode (build.sh with
    # CHECK_STRICT=TRUE), the same contract as the validator's warnings.
    (errors if strict else warnings).extend(sample_fallback_warnings(site.sample_fallbacks, _SAMPLE_HITS))
    (errors if strict else warnings).extend(free_offer_warnings(site.business))
    if not no_validate:
        # Intentional circular import: check_site imports shared settings/helpers from build;
        # import it only after output generation, when validation is requested.
        import check_site
        val_errors, val_warnings = check_site.run_checks(out, SITE_URL)
        errors.extend(val_errors)
        warnings.extend(val_warnings)


def build(out_dir=None, minify=None, no_validate=False, strict=False):
    git_branch, git_commit = get_git_info()
    build_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out = Path(out_dir or OUT_DEFAULT)
    css_size_before, css_size_after = _prepare_output(out, minify)

    layout = read_text(REPO / 'src' / 'layout.html')
    header = read_text(REPO / 'src' / 'partials' / 'header.html')
    footer = read_text(REPO / 'src' / 'partials' / 'footer.html')
    site = _site_values()
    replacements, html_replacements = _marker_tables(site.derived)
    layout, header, footer, entity_nodes = _shared_parts(
        layout, header, footer, site.entity, site.collections, replacements, html_replacements)

    shared = dict(layout_text=layout, header_text=header, footer_text=footer, entity_nodes=entity_nodes,
                  site_name=site.site_name, site_url=SITE_URL, contact_email=site.contact_email,
                  whatsapp_link=site.whatsapp_link, service_category_1=site.service_category_1,
                  service_category_2=site.service_category_2, location=site.location,
                  featured_action_name=site.featured_action_name, jsonld_replacements=replacements)
    writer = _PageWriter(out, minify, shared, html_replacements, {k: _json_str(v) for k, v in replacements.items()})
    errors = []
    warnings = []
    _write_pages(writer, errors)
    _write_indexes(writer, site)
    _write_site_files(out, site.collections, writer.pages_data, replacements)
    _final_checks(out, strict, no_validate, site, errors, warnings)
    success = len(errors) == 0
    print_report(
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
    )

    if not success:
        raise SystemExit(1)

if __name__ == '__main__':
    USAGE = 'usage: build.py [--out FOLDER] [--minify true|false] [--no-validate] [--strict]'
    out, minify, no_validate, strict = None, False, False, False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--no-validate':
            no_validate = True
        elif arg == '--strict':
            strict = True
        elif arg in ('--out', '--minify'):
            i += 1
            if i >= len(args):
                sys.exit(f'✗ missing value for {arg}\n{USAGE}')
            if arg == '--out':
                out = args[i]
            elif args[i].lower() in ('true', 'false'):
                minify = args[i].lower() == 'true'
            else:
                sys.exit(f'✗ --minify accepts true or false (got: {args[i]!r})\n{USAGE}')
        else:
            sys.exit(f'✗ unknown argument: {arg}\n{USAGE}')
        i += 1
    build(out_dir=out, minify=minify, no_validate=no_validate, strict=strict)