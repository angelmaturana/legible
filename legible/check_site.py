#!/usr/bin/env python3
"""SEO/integrity validator for the compiled output (dist/).

Usage:
    python3 legible/check_site.py                 # checks dist/
    python3 legible/check_site.py --dir .dev-dist # another folder
    python3 legible/check_site.py --strict        # warnings also fail
    python3 legible/check_site.py --prelaunch     # is it ready to publish? (no example data left)

Also run by legible/build.py at the end of every build.
Exit code: 0 = OK, 1 = errors (or warnings with --strict).
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import partial
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


sys.dont_write_bytecode = True  # importing this module must not leave legible/__pycache__/
from common import BuildError, fail, get_git_info, load_site_config, read_text, report_lines, resolve_site_url

REPO = Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / 'dist'

# Thresholds (adjustable)
TITLE_MAX = 60
TITLE_MIN = 20
DESC_MIN = 70
DESC_MAX = 160
ALT_MAX = 125
MIN_WORDS_INDEXABLE = 250
MIN_CONTEXTUAL_INLINKS = 1  # inbound links from the <main> of other pages

OG_IMAGE_MIN_WIDTH = 1200
OG_IMAGE_RATIO = 1200 / 630  # the 1.91:1 that social networks crop to
OG_IMAGE_RATIO_TOLERANCE = 0.05

REQUIRED_FILES = ['index.html', '404.html', 'sitemap.xml', 'robots.txt']
RECOMMENDED_FILES = ['llms.txt']
VOID = {'meta', 'link', 'img', 'br', 'hr', 'input', 'source', 'base', 'col', 'area', 'wbr', 'embed', 'track', 'param'}

# Valid twitter:card values (the 4 official ones)
TWITTER_CARDS = {'summary', 'summary_large_image', 'app', 'player'}


# --------------------------------------------------------------------------- parsing

class PageParser(HTMLParser):
    """Extract from a page everything the rules need."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ''
        self.metas = {}            # name|property -> content
        self.canonical = None
        self.links = []            # (href, in_main, kind)
        self.a_meta = []           # dicts: href, target, rel, in_main
        self.resources = []        # (url, kind) for link/script/img/source
        self.ids = set()
        self.h = []                # (level, text)
        self.imgs = []
        self.ld_raw = []
        self._ld_cache = None      # (blocks, parsed) of `load_ld`
        self.aria_current = 0
        self.main_text = []
        self.all_text = []
        self.faq = []              # (question, answer) visible in <details>
        self._stack = []
        self._in_title = False
        self._in_script = None
        self._in_style = False
        self._cur_h = None
        self._in_main = 0
        self._details = []         # stack of dicts {'q': str, 'a': [..], 'in_summary': bool}

    # -- JSON-LD, parsed once
    def load_ld(self):
        """Parse every JSON-LD block ONCE: [(data, None) | (None, error), ...]. Cached; redone only if `ld_raw` changes."""
        blocks = tuple(self.ld_raw)
        if self._ld_cache is None or self._ld_cache[0] != blocks:
            self._ld_cache = (blocks, [_parse_ld(raw) for raw in blocks])
        return self._ld_cache[1]

    @property
    def ld_docs(self):
        return self.load_ld()

    # -- start tags: common attributes, then one method per tag (see _START)
    _START = {'title': '_start_title', 'meta': '_start_meta', 'link': '_start_link', 'script': '_start_script',
              'style': '_start_style', 'main': '_start_main', 'a': '_start_a', 'img': '_start_img',
              'source': '_start_source', 'details': '_start_details', 'summary': '_start_summary'}
    # -- end tags (headings are handled before the table)
    _END = {'title': '_end_title', 'script': '_end_script', 'style': '_end_style', 'main': '_end_main',
            'summary': '_end_summary', 'details': '_end_details'}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        if 'id' in a:
            self.ids.add(a['id'])
        if 'aria-current' in a:
            self.aria_current += 1
        if re.fullmatch(r'h[1-6]', tag):
            self._cur_h = [int(tag[1]), '']
        elif tag in self._START:
            getattr(self, self._START[tag])(a)
        if tag not in VOID:
            self._stack.append(tag)

    def _start_title(self, a):
        self._in_title = True

    def _start_meta(self, a):
        key = a.get('name') or a.get('property')
        if key:
            self.metas[key] = a.get('content', '')

    def _start_link(self, a):
        rel = (a.get('rel') or '').lower()
        if rel == 'canonical':
            self.canonical = a.get('href')
        if a.get('href'):
            self.resources.append((a['href'], 'link:' + rel))

    def _start_script(self, a):
        if a.get('type') == 'application/ld+json':
            self._in_script = 'ld'
            self.ld_raw.append('')
        else:
            self._in_script = 'js'
        if a.get('src'):
            self.resources.append((a['src'], 'script'))

    def _start_style(self, a):
        self._in_style = True

    def _start_main(self, a):
        self._in_main += 1

    def _start_a(self, a):
        if a.get('href') is not None:
            self.links.append((a['href'], self._in_main > 0, 'a'))
            self.a_meta.append({
                'href': a['href'],
                'target': a.get('target'),
                'rel': a.get('rel') or '',
                'in_main': self._in_main > 0,
            })

    def _start_img(self, a):
        self.imgs.append(a)
        self._start_source(a)

    def _start_source(self, a):
        if a.get('src'):
            self.resources.append((a['src'], 'img'))
        for part in (a.get('srcset') or '').split(','):
            u = part.strip().split(' ')[0]
            if u:
                self.resources.append((u, 'img'))

    def _start_details(self, a):
        self._details.append({'q': '', 'a': [], 'in_summary': False})

    def _start_summary(self, a):
        if self._details:
            self._details[-1]['in_summary'] = True

    def handle_endtag(self, tag):
        if re.fullmatch(r'h[1-6]', tag):
            self._end_heading()
        elif tag in self._END:
            getattr(self, self._END[tag])()
        if tag in self._stack:
            # closes up to the tag (tolerant of badly nested HTML)
            while self._stack and self._stack.pop() != tag:
                pass

    def _end_title(self):
        self._in_title = False

    def _end_script(self):
        self._in_script = None

    def _end_style(self):
        self._in_style = False

    def _end_main(self):
        self._in_main = max(0, self._in_main - 1)

    def _end_heading(self):
        if self._cur_h:
            self._cur_h[1] = re.sub(r'\s+', ' ', self._cur_h[1]).strip()
            self.h.append(tuple(self._cur_h))
            self._cur_h = None

    def _end_summary(self):
        if self._details:
            self._details[-1]['in_summary'] = False

    def _end_details(self):
        if self._details:
            d = self._details.pop()
            self.faq.append((re.sub(r'\s+', ' ', d['q']).strip(),
                             re.sub(r'\s+', ' ', ' '.join(d['a'])).strip()))

    def handle_data(self, data):
        if self._in_script == 'ld':
            self.ld_raw[-1] += data
            return
        if self._in_script or self._in_style:
            return
        if self._in_title:
            self.title += data
        if self._cur_h is not None:
            self._cur_h[1] += data
        if self._details:
            d = self._details[-1]
            if d['in_summary']:
                d['q'] += data
            else:
                d['a'].append(data)
        self.all_text.append(data)
        if self._in_main:
            self.main_text.append(data)


_TAG_OPEN = re.compile(r'<([A-Za-z][A-Za-z0-9-]*)')
_INNER_TAG = re.compile(r'<[A-Za-z/!?]')


def _comment_end(text: str, start: int):
    """None when `start` is outside an HTML comment; else the index after its closing `-->` (-1 if it never closes)."""
    comment = text.rfind('<!--', 0, start)
    if comment == -1 or text.find('-->', comment, start) != -1:
        return None
    end = text.find('-->', start)
    return -1 if end == -1 else end + 3


def _tag_end(text: str, m) -> int:
    """Index of the `>` that closes the start tag matched by `m`, read respecting quotes; len(text) if it never closes."""
    n, i, quote = len(text), m.end(), None
    while i < n:
        c = text[i]
        if quote:
            if c == quote:
                quote = None
        elif c in '"\'':
            quote = c
        elif c == '>':
            break
        if i > m.end() and c == '<' and _INNER_TAG.match(text, i):
            return n
        i += 1
    return i


def find_broken_markup(text: str):
    """Describe the first broken tag of a page's raw HTML, or return None.

    A missing quote or `>` makes the parser swallow the rest of the page, and the validator then reports symptoms
    ("0 <h1>", "no JSON-LD", "anchor #main not found", "0 words") that never name the cause. Two kinds of fault
    are looked for: a start tag whose attribute quote is not closed (read respecting quotes, it reaches the end
    of the file or runs into another tag) and a `<script>` or `<style>` with no closing tag. Comments and the
    bodies of scripts and styles are skipped. Line numbers refer to the file as built (a minified file has one)."""
    pos = 0
    while True:
        m = _TAG_OPEN.search(text, pos)
        if not m:
            return None
        skip = _comment_end(text, m.start())
        if skip == -1:
            return None
        if skip is not None:
            pos = skip
            continue
        name, i = m.group(1).lower(), _tag_end(text, m)
        line = text.count('\n', 0, m.start()) + 1
        snippet = re.sub(r'\s+', ' ', text[m.start():m.start() + 60]).strip()
        if i >= len(text):
            return (f'broken markup at line {line}: the tag <{name}> never closes (an attribute quote or the ">" '
                    f'is missing): {snippet}')
        if name in ('script', 'style'):
            close = re.compile(r'</' + name + r'\s*>', re.I).search(text, i)
            if not close:
                return f'broken markup at line {line}: <{name}> has no closing </{name}>'
            pos = close.end()
        else:
            pos = i + 1


def _parse_ld(raw):
    """One JSON-LD block -> (data, None), or (None, error) when it is not valid JSON."""
    try:
        return json.loads(raw), None
    except ValueError as e:
        return None, e


def parse_page(path: Path) -> PageParser:
    p = PageParser()
    p.feed(path.read_text(encoding='utf-8'))
    p.close()
    p.load_ld()
    return p


def _get(node, *keys):
    """Walk nested dict keys; None when a level is missing or explicitly null ."""
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


# --------------------------------------------------------------------------- utilities

def page_url(rel_file: str, site_url: str) -> str:
    """index.html -> /, x/index.html -> /x/, 404.html -> /404.html"""
    if rel_file.endswith('index.html'):
        rel = '/' + rel_file[:-len('index.html')]
    else:
        rel = '/' + rel_file
    return site_url + rel


def is_indexable(parser: PageParser) -> bool:
    return 'noindex' not in parser.metas.get('robots', '').lower()


def resolve_internal(url: str, out: Path, site_url: str):
    """Return (file_path | None, fragment, error | None) for an internal URL."""
    if url.startswith(site_url):
        url = url[len(site_url):] or '/'
    parts = urlsplit(url)
    path, frag = parts.path, parts.fragment
    if not path:
        return None, frag, None  # same-page anchor only
    rel = path.lstrip('/')
    if path.endswith('/'):
        target = out / rel / 'index.html'
    else:
        target = out / rel
        if target.is_dir():
            return None, frag, f'missing trailing slash in {path}'
    return target, frag, None


# --------------------------------------------------------------------------- per-page rules

SAMPLE_DOMAINS = ('example.com', 'example.org', 'example.net')


def _is_sample_url(url, own_host):
    try:
        parts = urlsplit(str(url).strip())
        host = (parts.hostname or '').lower()
    except ValueError:
        return False
    if parts.scheme not in ('http', 'https') or not host or host == own_host:
        return False
    return any(host == d or host.endswith('.' + d) for d in SAMPLE_DOMAINS)


def sample_domain_urls(p: PageParser, site_url: str):
    """URLs of the page that point to example.com, example.org or example.net (or a subdomain): in links,
    resources, canonical, og:url, og:image and the `url` and `@id` of the JSON-LD. Never the visible text, never
    `mailto:` or `tel:` (not http), and never the site's own domain."""
    own = (urlsplit(site_url).hostname or '').lower()
    candidates = [h for h, _, _ in p.links] + [u for u, _ in p.resources]
    candidates += [p.canonical or '', p.metas.get('og:url', ''), p.metas.get('og:image', '')]
    for data, error in p.ld_docs:
        if error is not None:
            continue
        for node in walk_nodes(data):
            candidates += [v for k, v in node.items() if k in ('url', '@id') and isinstance(v, str)]
    found = []
    for url in candidates:
        if _is_sample_url(url, own) and url not in found:
            found.append(url)
    return found


# --------------------------------------------------------------------------- context and collector

class Findings:
    """Collects the findings of a run as (file, message) pairs. Wraps existing lists when it is given them."""

    def __init__(self, errors=None, warnings=None):
        self.errors = [] if errors is None else errors
        self.warnings = [] if warnings is None else warnings

    def error(self, file, msg):
        self.errors.append((file, msg))

    def warn(self, file, msg):
        self.warnings.append((file, msg))

    def as_tuple(self):
        return self.errors, self.warnings


@dataclass
class PageCtx:
    """Everything one page rule needs; `E`/`W` record a finding for this page."""
    rel_file: str
    p: PageParser
    out: Path
    site_url: str
    url: str
    title: str
    desc: str
    indexable: bool
    is404: bool
    findings: Findings

    def E(self, msg):
        self.findings.error(self.rel_file, msg)

    def W(self, msg):
        self.findings.warn(self.rel_file, msg)


# --------------------------------------------------------------------------- page rules
# One function per topic. The order of PAGE_RULES is the order of the messages.

def _head_lang_viewport(ctx):
    E, W, p = ctx.E, ctx.W, ctx.p
    if not p.lang:
        E('<html> without lang attribute')
    elif not re.fullmatch(r'[a-z]{2,3}(-[A-Za-z0-9]{2,8})*', p.lang):
        W(f'unusual lang value: {p.lang!r}')
    if 'viewport' not in p.metas:
        E('missing <meta name="viewport">')
    else:
        vp = p.metas['viewport'].lower().replace(' ', '')
        if 'width=device-width' not in vp:
            W('viewport without width=device-width')


def _head_title(ctx):
    E, W, title = ctx.E, ctx.W, ctx.title
    if not title:
        E('missing <title>')
    elif ctx.indexable:
        if len(title) > TITLE_MAX:
            W(f'title of {len(title)} characters (> {TITLE_MAX})')
        if len(title) < TITLE_MIN:
            W(f'title too short ({len(title)} characters)')


def _head_description(ctx):
    E, W, desc = ctx.E, ctx.W, ctx.desc
    if not desc:
        E('missing meta description')
    elif ctx.indexable:
        if len(desc) > DESC_MAX:
            W(f'description of {len(desc)} characters (> {DESC_MAX})')
        if len(desc) < DESC_MIN:
            W(f'description too short ({len(desc)} characters)')


def rules_head(ctx):
    _head_lang_viewport(ctx)
    _head_title(ctx)
    _head_description(ctx)
    if 'robots' not in ctx.p.metas:
        ctx.E('missing <meta name="robots">')


def rules_canonical(ctx):
    E, p, url = ctx.E, ctx.p, ctx.url
    if ctx.is404:
        if p.canonical or 'og:url' in p.metas:
            E('the 404 page must not have canonical or og:url')
    elif ctx.indexable:
        if not p.canonical:
            E('indexable page without canonical')
        elif p.canonical != url:
            E(f'canonical {p.canonical} does not match the expected URL {url}')
    if p.canonical and not p.canonical.startswith('https://'):
        E(f'canonical without HTTPS: {p.canonical}')
    if p.canonical and p.metas.get('og:url') and p.metas['og:url'] != p.canonical:
        E('og:url differs from canonical')


def _social_tags(ctx):
    W, p = ctx.W, ctx.p
    common_og = (
        'og:title', 'og:description', 'og:image', 'og:type', 'og:site_name', 'og:locale',
        'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image',
    )
    for key in common_og:
        if key not in p.metas:
            W(f'missing {key}')
    if not ctx.is404 and 'og:url' not in p.metas:
        W('missing og:url')
    if p.metas.get('og:title') and norm(p.metas['og:title']) != ctx.title:
        W('og:title differs from <title>')
    if 'og:locale' in p.metas and not re.fullmatch(r'[a-z]{2,3}_[A-Z]{2}', p.metas['og:locale']):
        W(f'unusual og:locale format: {p.metas["og:locale"]}')
    if 'twitter:card' in p.metas and p.metas['twitter:card'] not in TWITTER_CARDS:
        W(f'unrecognised twitter:card: {p.metas["twitter:card"]}')


def _og_image_size(ctx):
    W, p = ctx.W, ctx.p
    if ctx.rel_file == 'index.html' and 'og:image:width' in p.metas:  # the layout is shared: reported once
        try:
            og_w, og_h = int(p.metas['og:image:width']), int(p.metas.get('og:image:height', ''))
        except ValueError:
            og_w = og_h = 0
        if og_w <= 0 or og_h <= 0:
            W('og:image:width and og:image:height are not numbers: the engine could not read the size of '
              'og-image.png (see the build warning)')
        elif og_w < OG_IMAGE_MIN_WIDTH or abs(og_w / og_h - OG_IMAGE_RATIO) > OG_IMAGE_RATIO_TOLERANCE:
            W(f'og:image is {og_w}x{og_h}: use at least {OG_IMAGE_MIN_WIDTH} px wide and a 1.91:1 ratio (1200x630)')


def _og_image_exists(ctx):
    og_img = ctx.p.metas.get('og:image', '')
    if og_img.startswith(ctx.site_url):
        t, _, _ = resolve_internal(og_img, ctx.out, ctx.site_url)
        if t is not None and not t.exists():
            ctx.E(f'og:image does not exist in the output: {og_img}')


def rules_social(ctx):
    E, W, p = ctx.E, ctx.W, ctx.p
    _social_tags(ctx)
    og_img = p.metas.get('og:image', '')
    if og_img and not og_img.startswith('https://'):
        E(f'og:image without HTTPS: {og_img}')
    if og_img and 'og:image:alt' not in p.metas:
        W('og:image without og:image:alt')
    _og_image_size(ctx)
    og_url = p.metas.get('og:url', '')
    if og_url and not og_url.startswith('https://'):
        E(f'og:url without HTTPS: {og_url}')
    _og_image_exists(ctx)


def rules_headings(ctx):
    E, W, p = ctx.E, ctx.W, ctx.p
    h1s = [t for lvl, t in p.h if lvl == 1]
    if len(h1s) != 1:
        E(f'expected 1 <h1>, found {len(h1s)}')
    if p.h and p.h[0][0] != 1:
        W(f'the first heading is h{p.h[0][0]} ("{p.h[0][1][:40]}"), expected h1')
    prev = 0
    for lvl, t in p.h:
        if prev and lvl > prev + 1:
            W(f'heading level skipped h{prev} → h{lvl} ("{t[:40]}")')
        prev = lvl
    for lvl, t in p.h:
        if not t:
            E(f'empty h{lvl} heading')


def rules_images(ctx):
    E, W = ctx.E, ctx.W
    for img in ctx.p.imgs:
        src = img.get('src', '?')
        if not img.get('src') and not img.get('srcset'):
            W('<img> without src or srcset')
        if 'alt' not in img:
            E(f'<img> without alt: {src}')
        elif len(img['alt']) > ALT_MAX:
            W(f'alt of {len(img["alt"])} characters (> {ALT_MAX}): {src}')
        if not img.get('width') or not img.get('height'):
            W(f'<img> without width/height (CLS risk): {src}')


def rules_link_safety(ctx):
    # links with target="_blank" must carry rel="noopener"/"noreferrer"
    for meta in ctx.p.a_meta:
        if meta['target'] == '_blank':
            rel = (meta['rel'] or '').lower()
            if 'noopener' not in rel and 'noreferrer' not in rel:
                ctx.W(f'<a target="_blank"> without rel="noopener"/"noreferrer": {meta["href"][:60]}')


def rules_sample_domains(ctx):
    # URLs on a sample domain (a copied example that was never replaced)
    sample_urls = sample_domain_urls(ctx.p, ctx.site_url)
    if sample_urls:
        more = f' and {len(sample_urls) - 3} more' if len(sample_urls) > 3 else ''
        ctx.W('URL on a sample domain (example.com, example.org or example.net): ' + ', '.join(sample_urls[:3]) + more +
              '; use the real address or remove the link')


def rules_aria(ctx):
    if ctx.p.aria_current > 1:
        ctx.E(f'{ctx.p.aria_current} elements with aria-current')


def rules_leftovers(ctx):
    # template leftovers / markers
    p = ctx.p
    text = ' '.join(p.all_text)
    if '{{' in text or '{{' in str(p.canonical or '') or '{{' in ctx.title:
        ctx.E('unrendered {{...}} marker')
    if re.search(r'\bTODO\b|\[CONFIRM', text):
        ctx.W('contains TODO or [CONFIRM')


def rules_content(ctx):
    if ctx.indexable and not ctx.is404:
        words = len(norm(' '.join(ctx.p.main_text)).split())
        if words < MIN_WORDS_INDEXABLE:
            ctx.W(f'thin content: {words} words in <main> (< {MIN_WORDS_INDEXABLE})')


def walk_nodes(obj):
    """Iterate over all nested dicts of a JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_nodes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_nodes(v)


_JSON_KINDS = {type(None): 'null', list: 'a list', str: 'text', bool: 'a boolean', int: 'a number', float: 'a number',
               dict: 'an object'}


def _json_kind(value):
    return _JSON_KINDS.get(type(value), type(value).__name__)


def _as_text(value):
    """`value` when it is text, else None: JSON-LD fields that must be text may come as numbers, lists or objects."""
    return value if isinstance(value, str) else None


def _ld_nodes(data, problems=None):
    """The nodes (dicts) of one JSON-LD document: `@graph` items, or the document itself. What is not an object
    (a root that is a list or null, a `@graph` item that is text...) is dropped and described in `problems`."""
    if not isinstance(data, dict):
        if problems is not None:
            problems.append(f'the root is {_json_kind(data)}, expected an object')
        return []
    graph = data.get('@graph') or [data]
    if not isinstance(graph, list):
        graph = [graph]
    nodes = [n for n in graph if isinstance(n, dict)]
    if problems is not None:
        problems += [f'@graph item is not an object: {json.dumps(n)[:40]}' for n in graph if not isinstance(n, dict)]
    return nodes


def _faq_questions(node, problems=None):
    """The questions (dicts) of a FAQPage: `mainEntity` must be a list of objects; what is not is described in `problems`."""
    entity = node.get('mainEntity')
    if not entity:
        return []
    if not isinstance(entity, list):
        if problems is not None:
            problems.append(f'FAQPage.mainEntity is {_json_kind(entity)}, expected a list')
        return []
    if problems is not None:
        problems += [f'FAQPage.mainEntity item is not an object: {json.dumps(q)[:40]}' for q in entity if not isinstance(q, dict)]
    return [q for q in entity if isinstance(q, dict)]


PAGE_TYPES = ('WebPage', 'CollectionPage', 'AboutPage', 'ContactPage')
SCHEMA_CONTEXTS = ('https://schema.org', 'https://schema.org/', 'http://schema.org', 'http://schema.org/')


def _bad_id(ctx, value):
    ctx.E(f'JSON-LD with an unexpected shape: @id is not text: {json.dumps(value)[:40]}')


def _ld_register_ids(ctx, nodes, defined):
    """Record the `@id` of each node in `defined`; a repeated one is an error, one that is not text a shape error."""
    for n in nodes:
        nid = n.get('@id')
        if not nid:
            continue
        if _as_text(nid) is None:
            _bad_id(ctx, nid)
            continue
        if nid in defined:
            ctx.E(f'duplicate @id on the page: {nid}')
        defined[nid] = n


def _ld_ref_ids(ctx, nodes):
    """The `@id` of every reference (a dict that contains only `@id`); one that is not text is a shape error."""
    refs = []
    for sub in walk_nodes(nodes):
        if set(sub.keys()) == {'@id'}:
            if _as_text(sub['@id']) is None:
                _bad_id(ctx, sub['@id'])
            else:
                refs.append(sub['@id'])
    return refs


def _ld_collect(ctx):
    """Read every JSON-LD block: syntax, @context, shape and duplicate ids.
    Returns (defined @ids, @id references, all nodes)."""
    defined, refs, graph_nodes = {}, [], []
    for data, error in ctx.p.ld_docs:
        if error is not None:
            ctx.E(f'invalid JSON-LD: {error}')
            continue
        if isinstance(data, dict) and data.get('@context') not in SCHEMA_CONTEXTS:
            ctx.E('JSON-LD without schema.org @context')
        problems = []
        nodes = _ld_nodes(data, problems)
        for detail in problems:
            ctx.E(f'JSON-LD with an unexpected shape: {detail}')
        graph_nodes.extend(nodes)
        _ld_register_ids(ctx, nodes, defined)
        refs.extend(_ld_ref_ids(ctx, nodes))
    return defined, refs, graph_nodes


def _ld_references(ctx, defined, refs):
    for r in refs:
        if r not in defined:
            ctx.E(f'undefined @id reference on the page: {r}')


def _ld_required_nodes(ctx, graph_nodes):
    """An indexable page needs the main node and a WebSite node."""
    # @type is a text or a list of texts (["Restaurant", "LocalBusiness"]): normalise before comparing
    types = set()
    for n in graph_nodes:
        t = n.get('@type')
        types.update(x for x in (t if isinstance(t, list) else [t]) if isinstance(x, str))
    main_id = (ctx.site_url + '/#business') if ctx.site_url is not None else None
    if not any(isinstance(n.get('@id'), str) and
               (n['@id'] == main_id if main_id else n['@id'].endswith('/#business')) for n in graph_nodes):
        ctx.E(f'missing main node (@id {main_id or "<site_url>/#business"}) in the JSON-LD')
    if 'WebSite' not in types:
        ctx.E('missing WebSite node in the JSON-LD')


def _ld_page_node(ctx, n, t):
    """WebPage and its subtypes: url, name and dateModified must agree with the page."""
    if n.get('url') != ctx.url:
        ctx.E(f'{t}.url ({n.get("url")}) differs from the page URL ({ctx.url})')
    name = n.get('name')
    if name and _as_text(name) is None:
        ctx.W(f'name is not text: {name}')
    elif name and norm(name) != ctx.title:
        ctx.W(f'{t}.name differs from <title>')
    dm = n.get('dateModified')
    if dm and _as_text(dm) is None:
        ctx.W(f'dateModified is not text: {dm}')
    elif dm and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', dm):
        ctx.W(f'dateModified in non-ISO format: {dm}')


def _ld_question(ctx, q):
    """One Question of a FAQPage: @type, text name and an Answer with text."""
    if q.get('@type') != 'Question':
        ctx.W(f'FAQPage.mainEntity with @type {q.get("@type")!r}, expected "Question"')
    name = q.get('name')
    if name is not None and _as_text(name) is None:
        ctx.W(f'FAQPage Question name is not text: {name}')
    ans = q.get('acceptedAnswer')
    ans = ans if isinstance(ans, dict) else {}
    if ans.get('@type') != 'Answer':
        ctx.W(f'FAQPage Question "{norm(_as_text(name) or "")[:40]}" without acceptedAnswer @type="Answer"')
    text = ans.get('text')
    if text is not None and _as_text(text) is None:
        ctx.W(f'FAQPage Answer text is not text: {text}')


def _ld_faq(ctx, n):
    """FAQPage: mainEntity must be a list of Question with an Answer."""
    if not n.get('mainEntity'):
        ctx.E('FAQPage without mainEntity')
        return
    faq_problems = []
    for q in _faq_questions(n, faq_problems):
        _ld_question(ctx, q)
    for detail in faq_problems:
        ctx.E(f'JSON-LD with an unexpected shape: {detail}')


def _ld_check_type(ctx, t):
    """`@type` is text or a list of texts (["Restaurant", "LocalBusiness"]); anything else is odd. Absent is fine."""
    if t is None or isinstance(t, str):
        return
    if not (isinstance(t, list) and all(isinstance(x, str) for x in t)):
        ctx.W(f'JSON-LD @type is not text or a list of texts: {json.dumps(t)[:40]}')


def _ld_structure(ctx):
    """The JSON-LD of the page: presence, ids, required nodes, page nodes and FAQ."""
    if not ctx.p.ld_raw:
        if ctx.indexable and not ctx.is404:
            ctx.E('indexable page without JSON-LD')
        return
    defined, refs, graph_nodes = _ld_collect(ctx)
    _ld_references(ctx, defined, refs)
    if ctx.indexable:
        _ld_required_nodes(ctx, graph_nodes)
    for n in graph_nodes:
        t = n.get('@type')
        _ld_check_type(ctx, t)
        if t in PAGE_TYPES:
            _ld_page_node(ctx, n, t)
        if t == 'FAQPage':
            _ld_faq(ctx, n)


def _faq_texts(q):
    """(question, answer) of a Question as normalised texts; None when one of them is present but not text
    (`_ld_question` already warns about it)."""
    name, text = q.get('name'), _get(q, 'acceptedAnswer', 'text')
    if any(v is not None and _as_text(v) is None for v in (name, text)):
        return None
    return norm(name or ''), norm(text or '')


def _ld_faq_visible(ctx):
    """JSON-LD FAQs must match the visible questions."""
    schema_faq = []
    for data, error in ctx.p.ld_docs:
        if error is not None:
            continue
        for n in _ld_nodes(data):
            if n.get('@type') == 'FAQPage':
                schema_faq += [t for t in map(_faq_texts, _faq_questions(n)) if t is not None]
    visible = dict(ctx.p.faq)
    for q, a in schema_faq:
        if q not in visible:
            ctx.E(f'JSON-LD FAQ not visible on the page: "{q[:60]}"')
        elif visible[q] != a:
            ctx.E(f'FAQ answer differs between JSON-LD and visible text: "{q[:60]}"')


def rules_jsonld(ctx):
    _ld_structure(ctx)
    _ld_faq_visible(ctx)


def _faq_matches_schema(rel_file, p, errors, warnings):
    """FAQ check outside `check_page` (same argument order as the page checks)."""
    ctx = PageCtx(rel_file=rel_file, p=p, out=None, site_url=None, url='', title='', desc='',
                  indexable=False, is404=False, findings=Findings(errors, warnings))
    _ld_faq_visible(ctx)


def check_faq_matches_schema(rel_file, p, warnings, errors):
    """Public entry point; keeps the original argument order (warnings, errors)."""
    _faq_matches_schema(rel_file, p, errors, warnings)


PAGE_RULES = (
    rules_head, rules_canonical, rules_social, rules_headings, rules_images,
    rules_link_safety, rules_sample_domains, rules_aria, rules_leftovers, rules_content, rules_jsonld,
)


def check_page(rel_file, p: PageParser, out: Path, site_url: str, errors, warnings):
    ctx = PageCtx(
        rel_file=rel_file, p=p, out=out, site_url=site_url,
        url=page_url(rel_file, site_url), title=norm(p.title),
        desc=norm(p.metas.get('description', '')), indexable=is_indexable(p),
        is404=rel_file == '404.html', findings=Findings(errors, warnings),
    )
    for rule in PAGE_RULES:
        rule(ctx)


# --------------------------------------------------------------------------- site rules

_MAILTO_RE = re.compile(r'mailto:[^@\s]+@[^@\s]+\.[^@\s?]+(\?.*)?')
_TEL_RE = re.compile(r'tel:\+?[\d\s().-]{6,}')


def _classify_href(href: str, site_url: str) -> str:
    """Label an href: empty, mailto, tel, own_http, external, protocol_relative, fragment, relative or internal."""
    if not href:
        return 'empty'
    if href.startswith('mailto:'):
        return 'mailto'
    if href.startswith('tel:'):
        return 'tel'
    own_http = 'http://' + site_url.split('://', 1)[1]
    if href.startswith(own_http) and href[len(own_http):len(own_http) + 1] in ('', '/', '?', '#'):
        return 'own_http'
    if href.startswith(('http://', 'https://')) and not href.startswith(site_url):
        return 'external'
    if href.startswith('//'):
        return 'protocol_relative'
    if href.startswith('#'):
        return 'fragment'
    if not (href.startswith('/') or href.startswith(site_url)):
        return 'relative'
    return 'internal'


def _check_mailto(href, E):
    if not _MAILTO_RE.fullmatch(href):
        E(f'malformed mailto: {href[:60]}')


def _check_tel(href, E):
    if not _TEL_RE.fullmatch(href):
        E(f'malformed tel: {href}')


def _check_external(href, W):
    if href.startswith('http://'):
        W(f'external link without HTTPS: {href[:60]}')


def _check_fragment(href, p, E):
    frag = href[1:]
    if frag and frag not in p.ids:
        E(f'anchor not found on the same page: {href}')


def _check_internal(href, pages, out: Path, site_url: str, E):
    """Check an internal link (file and anchor). Returns the target's key in `pages` when it exists, else None."""
    target, frag, err = resolve_internal(href, out, site_url)
    if err:
        E(err)
        return None
    if target is None or not target.exists():
        E(f'broken internal link: {href}')
        return None
    key = target.relative_to(out).as_posix()
    if frag:
        tp = pages.get(key)
        if tp is not None and frag not in tp.ids:
            E(f'anchor not found: {href}')
    return key


def _check_href(href, p, pages, out: Path, site_url: str, E, W):
    """Check one link by kind. Returns the target page key for a valid internal link, else None."""
    kind = _classify_href(href, site_url)
    if kind == 'empty':
        E('link with empty href')
    elif kind == 'mailto':
        _check_mailto(href, E)
    elif kind == 'tel':
        _check_tel(href, E)
    elif kind == 'own_http':
        E(f'internal link with http instead of https: {href}')
    elif kind == 'external':
        _check_external(href, W)
    elif kind == 'fragment':
        _check_fragment(href, p, E)
    elif kind == 'relative':
        W(f'relative link (an absolute path is better): {href[:60]}')
    elif kind == 'internal':
        return _check_internal(href, pages, out, site_url, E)
    return None


def _check_resources(p, out: Path, site_url: str, E):
    """Internal resources (stylesheets, icons, ...) must exist in the output."""
    for url, kind in p.resources:
        if url.startswith(('data:', 'http://', 'https://')) and not url.startswith(site_url):
            continue
        target, _, err = resolve_internal(url, out, site_url)
        if err:
            continue
        if target is not None and not target.exists():
            E(f'missing resource ({kind}): {url}')


def _orphans(pages, inlinks, warnings):
    """Indexable pages without inbound contextual links."""
    for rel_file, p in pages.items():
        if rel_file in ('404.html', 'index.html') or not is_indexable(p):
            continue
        if len(inlinks[rel_file]) < MIN_CONTEXTUAL_INLINKS:
            warnings.append((rel_file, 'no inbound contextual links from other pages (menu/footer only)'))


def check_links(pages, out: Path, site_url: str, errors, warnings):
    """Internal links and resources: file and anchor existence."""
    findings = Findings(errors, warnings)
    inlinks = {rel: set() for rel in pages}
    for rel_file, p in pages.items():
        E, W = partial(findings.error, rel_file), partial(findings.warn, rel_file)
        for href, in_main, _kind in p.links:
            key = _check_href(href.strip(), p, pages, out, site_url, E, W)
            if key in inlinks and key != rel_file and in_main:
                inlinks[key].add(rel_file)
        _check_resources(p, out, site_url, E)
    _orphans(pages, inlinks, warnings)


def check_duplicates(pages, errors):
    seen_t, seen_d = {}, {}
    for rel_file, p in sorted(pages.items()):
        if not is_indexable(p) or rel_file == '404.html':
            continue
        t, d = norm(p.title), norm(p.metas.get('description', ''))
        if t in seen_t:
            errors.append((rel_file, f'title duplicated with {seen_t[t]}'))
        seen_t[t] = rel_file
        if d in seen_d:
            errors.append((rel_file, f'description duplicated with {seen_d[d]}'))
        seen_d[d] = rel_file


def _read_sitemap(sm: Path, errors):
    """Parse sitemap.xml; returns its root element, or None (with an error recorded) when it is invalid."""
    try:
        return ET.fromstring(sm.read_text(encoding='utf-8'))
    except ET.ParseError as e:
        errors.append(('sitemap.xml', f'invalid XML: {e}'))
        return None


def _check_sitemap_entry(loc, lm, out: Path, site_url: str, errors, warnings):
    if not loc.startswith(site_url + '/'):
        errors.append(('sitemap.xml', f'URL outside the domain: {loc}'))
        return
    target, _, err = resolve_internal(loc, out, site_url)
    if err or target is None or not target.exists():
        errors.append(('sitemap.xml', f'sitemap URL without a generated page: {loc}'))
    if lm and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', lm):
        warnings.append(('sitemap.xml', f'lastmod in non-ISO format: {loc} → {lm}'))


def _check_sitemap_entries(root, out: Path, site_url: str, errors, warnings):
    """Per-URL checks. Returns ({loc: True}, {loc: lastmod}) for the coverage checks."""
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    in_sitemap, lastmods = {}, {}
    for u in root.findall('s:url', ns):
        loc = (u.findtext('s:loc', default='', namespaces=ns) or '').strip()
        lm = (u.findtext('s:lastmod', default='', namespaces=ns) or '').strip()
        if loc in in_sitemap:
            errors.append(('sitemap.xml', f'duplicate URL: {loc}'))
        in_sitemap[loc] = True
        lastmods[loc] = lm
        _check_sitemap_entry(loc, lm, out, site_url, errors, warnings)
    return in_sitemap, lastmods


def _check_sitemap_coverage(pages, in_sitemap, site_url: str, errors):
    """Indexable pages must be listed and nothing else. Returns {url: parser} of the indexable pages."""
    indexable = {page_url(rel, site_url): p for rel, p in pages.items()
                 if is_indexable(p) and rel != '404.html'}
    for u in sorted(set(indexable) - set(in_sitemap)):
        errors.append(('sitemap.xml', f'indexable page missing from the sitemap: {u}'))
    for u in sorted(set(in_sitemap) - set(indexable)):
        if u.startswith(site_url + '/'):
            errors.append(('sitemap.xml', f'the sitemap includes a noindex or non-existent page: {u}'))
    return indexable


def _check_lastmod_vs_jsonld(indexable, lastmods, warnings):
    """lastmod <-> JSON-LD dateModified consistency."""
    for u, p in indexable.items():
        for data, error in p.ld_docs:
            if error is not None:
                continue
            for n in _ld_nodes(data):
                dm = _as_text(n.get('dateModified'))
                if dm and lastmods.get(u) and dm != lastmods[u]:
                    warnings.append(('sitemap.xml', f'lastmod {lastmods[u]} ≠ dateModified {dm} in {u}'))


def check_sitemap(pages, out: Path, site_url: str, errors, warnings):
    sm = out / 'sitemap.xml'
    if not sm.exists():
        return
    root = _read_sitemap(sm, errors)
    if root is None:
        return
    in_sitemap, lastmods = _check_sitemap_entries(root, out, site_url, errors, warnings)
    indexable = _check_sitemap_coverage(pages, in_sitemap, site_url, errors)
    _check_lastmod_vs_jsonld(indexable, lastmods, warnings)


def check_robots(out: Path, site_url: str, errors, warnings):
    rb = out / 'robots.txt'
    if not rb.exists():
        return
    text = rb.read_text(encoding='utf-8')
    if not re.search(r'^\s*Sitemap:\s*' + re.escape(site_url) + r'/sitemap\.xml\s*$', text, re.M | re.I):
        warnings.append(('robots.txt', f'does not declare "Sitemap: {site_url}/sitemap.xml"'))
    current_all = False
    for line in text.splitlines():
        line = line.split('#')[0].strip()
        if re.match(r'user-agent:\s*\*$', line, re.I):
            current_all = True
        elif re.match(r'user-agent:', line, re.I):
            current_all = False
        elif current_all and re.fullmatch(r'disallow:\s*/', line, re.I):
            errors.append(('robots.txt', 'Disallow: / for all crawlers (blocks the whole site)'))


# --------------------------------------------------------------------------- API

def _check_required_files(out, errors, warnings):
    for req in REQUIRED_FILES:
        if not (out / req).exists():
            errors.append((req, 'required file missing'))
    for rec in RECOMMENDED_FILES:
        if not (out / rec).exists():
            warnings.append((rec, 'recommended file missing'))


def _load_pages(out, files, errors):
    """Parse every page: `{relative path: PageParser}`. A page that cannot be read goes to `errors`."""
    pages = {}
    for f in files:
        rel = str(f.relative_to(out)).replace('\\', '/')
        try:
            pages[rel] = parse_page(f)
        except (OSError, UnicodeError, ValueError) as e:
            errors.append((rel, f'could not read/parse: {e}'))
    return pages


def _check_one_page(rel, p, out, site_url, errors, warnings):
    page_errors = []
    check_page(rel, p, out, site_url, page_errors, warnings)
    if page_errors:
        # Only a page that already fails gets the cause (the other messages stay): this never changes which
        # sites build, and a tag that merely looks odd but breaks nothing is not reported.
        try:
            cause = find_broken_markup((out / rel).read_text(encoding='utf-8'))
        except (OSError, UnicodeError):
            cause = None
        if cause:
            errors.append((rel, cause))
    errors.extend(page_errors)


def run_checks(out_dir, site_url=None):
    """Return (errors, warnings): lists of (file, message) tuples. Without `site_url`, the one of the project."""
    if site_url is None:
        site_url = resolve_site_url(load_site_config(REPO))
    out = Path(out_dir)
    errors, warnings = [], []
    if not out.is_dir():
        return [(str(out), 'the output folder does not exist: build first')], []
    files = sorted(out.rglob('*.html'))
    if not files:
        return [(str(out), 'no .html page found: the build is empty')], []
    _check_required_files(out, errors, warnings)
    pages = _load_pages(out, files, errors)
    for rel, p in pages.items():
        _check_one_page(rel, p, out, site_url, errors, warnings)
    check_duplicates(pages, errors)
    check_links(pages, out, site_url, errors, warnings)
    check_sitemap(pages, out, site_url, errors, warnings)
    check_robots(out, site_url, errors, warnings)
    return errors, warnings


# --------------------------------------------------------------------------- --prelaunch (plan 4.6)

# `site.json` key -> the example value of the template. `--prelaunch` fails while a key still has it. A test checks
# that this table matches the site.json that ships with the project.
SAMPLE_VALUES = {
    'site_url': 'https://YOUR-DOMAIN.com',
    'site_name': 'Your Business',
    'site_description': 'One sentence about what the site is and who it is for.',
    'contact_email': 'hello@example.com',
    'phone_e164': '+15550100',
    'city': 'Your City',
    'region': 'Your Region',
    'country_code': 'XX',
    'legal_name': 'Your legal name',
    'legal_tax_id': 'Your registration number',
    'legal_address': 'Your registered address',
    'legal_jurisdiction': 'Your jurisdiction',
}
SAMPLE_STRINGS = ('YOUR-DOMAIN', 'Your Business')  # unmistakable: they can only come from the template
_NOT_VISIBLE = re.compile(r'<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>', re.DOTALL | re.IGNORECASE)
_PENDING_TEXT = re.compile(r'\bTODO\b|\[CONFIRM')


def _prelaunch_site_json(root, url_given):
    found = []
    config = load_site_config(root)
    for key, sample in SAMPLE_VALUES.items():
        if key == 'site_url' and url_given:
            continue
        if config.get(key) == sample:
            found.append(('src/data/site.json', f'"{key}" still has the example value "{sample}"',
                          f'write the real value of "{key}"'))
    return found


def _prelaunch_pages(root):
    found = []
    for page in sorted((root / 'src' / 'pages').rglob('*.html')):
        if '<!-- SAMPLE COPY' in read_text(page):
            found.append((str(page.relative_to(root)), 'it still has the <!-- SAMPLE COPY --> comment',
                          'replace the sample text with the real one and delete the comment'))
    return found


def _prelaunch_output(out):
    found = []
    where = {}  # what was found in the output -> the files that have it (one finding each, not one per file)
    for path in sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in ('.html', '.txt', '.xml')):
        text = read_text(path)
        rel = str(path.relative_to(out))
        for sample in SAMPLE_STRINGS:
            if sample in text:
                where.setdefault(('the output contains "%s"' % sample,
                                  'fix it in src/ (data or page) and rebuild'), []).append(rel)
        if path.suffix == '.html':
            visible = re.sub(r'<[^>]+>', ' ', _NOT_VISIBLE.sub(' ', text))
            for match in sorted(set(_PENDING_TEXT.findall(visible))):
                where.setdefault(('the visible text contains "%s"' % match,
                                  'finish the text and rebuild'), []).append(rel)
    for (finding, action), files in where.items():
        more = f' and {len(files) - 3} more' if len(files) > 3 else ''
        found.append((str(out.name) + '/', f'{finding} (in {", ".join(files[:3])}{more})', action))
    return found


def prelaunch_findings(root, out, site_url_override=None):
    """What still says "example" in the project `root` and its built folder `out`: a list of
    `(file, finding, action)`. Empty = ready to publish. Never changes anything. A site whose address comes
    from `--site-url` or the SITE_URL variable (as on a host that sets it) does not need `site_url` in site.json."""
    root, out = Path(root), Path(out)
    url_given = bool(site_url_override or os.environ.get('SITE_URL'))
    found = _prelaunch_site_json(root, url_given) + _prelaunch_pages(root)
    if not out.is_dir():
        found.append((str(out), 'the built folder does not exist, so the output was not checked',
                      'run ./legible/build.sh first'))
        return found
    return found + _prelaunch_output(out)


def print_prelaunch_report(findings):
    if not findings:
        print('✓ Ready to publish: no example data left.')
        return
    print(f'✗ Not ready to publish: {len(findings)} thing(s) still say "example":\n')
    for file, finding, action in findings:
        print(f'  • {file}: {finding}\n      → {action}')
    print('\nThe base itself is fine (`check_site.py --strict` passes): this list is what to do before going live.')


class _Box:
    """The frame of the console report: `W` is the interior width."""
    COL = 50
    LBL = 15
    W = 2 + LBL + 2 + COL

    def top(self): print('╔' + '═' * self.W + '╗')
    def bottom(self): print('╚' + '═' * self.W + '╝')
    def hr(self): print('╠' + '═' * self.W + '╣')
    def row(self, label, value): print(f'║  {label:<{self.LBL}}: {str(value):<{self.COL}}║')
    def centered(self, text): print(f'║{text.center(self.W)}║')
    def empty(self): print(f'║{" " * self.W}║')

    def lines(self, items):
        for line in report_lines(items, self.W - 2):
            print(f'║  {line:<{self.W - 2}}║')


def _report_issues(box, success, errors, warnings, strict):
    box.hr()
    if success:
        box.centered('✓  No issues')
        return
    if errors:
        box.centered('✗  Errors')
        box.lines(errors)
    if warnings:
        box.centered('⚠  Warnings (treated as errors)' if strict else '⚠  Warnings')
        box.lines(warnings)


def print_check_report(success, errors, warnings, n_pages, check_time, git_branch, git_commit, out_dir, strict):
    box = _Box()
    box.top()
    box.empty()
    box.centered('Legible • Site validator')
    box.empty()
    box.hr()
    box.centered('✓  CHECK PASSED' if success else '✗  CHECK FAILED')
    box.hr()
    box.centered('CHECK REPORT')
    box.hr()
    box.row('Status', '✓  PASSED' if success else '✗  FAILED')
    box.row('Branch', git_branch)
    box.row('Commit', git_commit)
    box.row('Check Time', check_time)
    box.row('Pages Checked', str(n_pages))
    box.row('Output Dir', str(out_dir))
    box.row('Strict Mode', str(strict))
    _report_issues(box, success, errors, warnings, strict)
    box.empty()
    box.centered('Site checks passed' if success else 'Site checks failed — fix issues above')
    box.empty()
    box.bottom()


def main(argv=None):
    ap = argparse.ArgumentParser(description='SEO validator for the compiled output.')
    ap.add_argument('--dir', default=str(OUT_DEFAULT), help='compiled folder (default: dist/)')
    ap.add_argument('--site-url', default=None, help='public https URL (default: SITE_URL or site_url in site.json)')
    ap.add_argument('--strict', action='store_true', help='warnings also fail')
    ap.add_argument('--prelaunch', action='store_true',
                    help='instead of the SEO checks: fail while any example data is left (exit 1)')
    args = ap.parse_args(argv)

    try:
        site_url = resolve_site_url(load_site_config(REPO), args.site_url)
    except BuildError as exc:
        return fail(exc)
    out = Path(args.dir)
    if args.prelaunch:
        findings = prelaunch_findings(REPO, out, args.site_url)
        print_prelaunch_report(findings)
        return 1 if findings else 0
    errors, warnings = run_checks(out, site_url)
    n_pages = len(list(out.rglob('*.html'))) if out.is_dir() else 0
    success = len(errors) == 0 and (not args.strict or len(warnings) == 0)
    check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    git_branch, git_commit = get_git_info(REPO)

    print_check_report(success, errors, warnings, n_pages, check_time, git_branch, git_commit, out, args.strict)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
