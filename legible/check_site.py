#!/usr/bin/env python3
"""SEO/integrity validator for the compiled output (dist/).

Usage:
    python3 legible/check_site.py                 # checks dist/
    python3 legible/check_site.py --dir .dev-dist # another folder
    python3 legible/check_site.py --strict        # warnings also fail

Also run by legible/build.py at the end of every build.
Exit code: 0 = OK, 1 = errors (or warnings with --strict).
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


def _apply_site_url_override():
    """Let the CLI URL override reach build.py before its import-time validation."""
    args = sys.argv[1:]
    for index, arg in enumerate(args):
        if arg == '--site-url':
            if index + 1 < len(args) and not args[index + 1].startswith('--'):
                os.environ['SITE_URL'] = args[index + 1]
            return
        if arg.startswith('--site-url='):
            os.environ['SITE_URL'] = arg.split('=', 1)[1]
            return


_apply_site_url_override()
sys.dont_write_bytecode = True  # importing build must not leave legible/__pycache__/
# Intentional circular import: this validator uses shared build settings and report helpers;
# build imports check_site only at the end, when validation is requested.
from build import SITE_URL, SITE_CONFIG, get_git_info, report_lines

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

    # -- helpers
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        if 'id' in a:
            self.ids.add(a['id'])
        if 'aria-current' in a:
            self.aria_current += 1
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = a.get('name') or a.get('property')
            if key:
                self.metas[key] = a.get('content', '')
        elif tag == 'link':
            rel = (a.get('rel') or '').lower()
            if rel == 'canonical':
                self.canonical = a.get('href')
            if a.get('href'):
                self.resources.append((a['href'], 'link:' + rel))
        elif tag == 'script':
            if a.get('type') == 'application/ld+json':
                self._in_script = 'ld'
                self.ld_raw.append('')
            else:
                self._in_script = 'js'
            if a.get('src'):
                self.resources.append((a['src'], 'script'))
        elif tag == 'style':
            self._in_style = True
        elif tag == 'main':
            self._in_main += 1
        elif tag == 'a':
            if a.get('href') is not None:
                self.links.append((a['href'], self._in_main > 0, 'a'))
                self.a_meta.append({
                    'href': a['href'],
                    'target': a.get('target'),
                    'rel': a.get('rel') or '',
                    'in_main': self._in_main > 0,
                })
        elif tag in ('img', 'source'):
            if tag == 'img':
                self.imgs.append(a)
            if a.get('src'):
                self.resources.append((a['src'], 'img'))
            for part in (a.get('srcset') or '').split(','):
                u = part.strip().split(' ')[0]
                if u:
                    self.resources.append((u, 'img'))
        elif re.fullmatch(r'h[1-6]', tag):
            self._cur_h = [int(tag[1]), '']
        elif tag == 'details':
            self._details.append({'q': '', 'a': [], 'in_summary': False})
        elif tag == 'summary' and self._details:
            self._details[-1]['in_summary'] = True
        if tag not in VOID:
            self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        elif tag == 'script':
            self._in_script = None
        elif tag == 'style':
            self._in_style = False
        elif tag == 'main':
            self._in_main = max(0, self._in_main - 1)
        elif re.fullmatch(r'h[1-6]', tag) and self._cur_h:
            self._cur_h[1] = re.sub(r'\s+', ' ', self._cur_h[1]).strip()
            self.h.append(tuple(self._cur_h))
            self._cur_h = None
        elif tag == 'summary' and self._details:
            self._details[-1]['in_summary'] = False
        elif tag == 'details' and self._details:
            d = self._details.pop()
            self.faq.append((re.sub(r'\s+', ' ', d['q']).strip(),
                             re.sub(r'\s+', ' ', ' '.join(d['a'])).strip()))
        if tag in self._stack:
            # closes up to the tag (tolerant of badly nested HTML)
            while self._stack and self._stack.pop() != tag:
                pass

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


def parse_page(path: Path) -> PageParser:
    p = PageParser()
    p.feed(path.read_text(encoding='utf-8'))
    p.close()
    return p


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

def check_page(rel_file, p: PageParser, out: Path, site_url: str, errors, warnings):
    E = lambda msg: errors.append((rel_file, msg))
    W = lambda msg: warnings.append((rel_file, msg))
    is404 = rel_file == '404.html'
    indexable = is_indexable(p)
    url = page_url(rel_file, site_url)

    # basic <head>
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
    title = norm(p.title)
    desc = norm(p.metas.get('description', ''))
    if not title:
        E('missing <title>')
    elif indexable:
        if len(title) > TITLE_MAX:
            W(f'title of {len(title)} characters (> {TITLE_MAX})')
        if len(title) < TITLE_MIN:
            W(f'title too short ({len(title)} characters)')
    if not desc:
        E('missing meta description')
    elif indexable:
        if len(desc) > DESC_MAX:
            W(f'description of {len(desc)} characters (> {DESC_MAX})')
        if len(desc) < DESC_MIN:
            W(f'description too short ({len(desc)} characters)')
    if 'robots' not in p.metas:
        E('missing <meta name="robots">')

    # canonical
    if is404:
        if p.canonical or 'og:url' in p.metas:
            E('the 404 page must not have canonical or og:url')
    elif indexable:
        if not p.canonical:
            E('indexable page without canonical')
        elif p.canonical != url:
            E(f'canonical {p.canonical} does not match the expected URL {url}')
    if p.canonical and not p.canonical.startswith('https://'):
        E(f'canonical without HTTPS: {p.canonical}')
    if p.canonical and p.metas.get('og:url') and p.metas['og:url'] != p.canonical:
        E('og:url differs from canonical')

    # Open Graph / Twitter
    common_og = (
        'og:title', 'og:description', 'og:image', 'og:type', 'og:site_name', 'og:locale',
        'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image',
    )
    for key in common_og:
        if key not in p.metas:
            W(f'missing {key}')
    if not is404 and 'og:url' not in p.metas:
        W('missing og:url')
    if p.metas.get('og:title') and norm(p.metas['og:title']) != title:
        W('og:title differs from <title>')
    if 'og:locale' in p.metas and not re.fullmatch(r'[a-z]{2,3}_[A-Z]{2}', p.metas['og:locale']):
        W(f'unusual og:locale format: {p.metas["og:locale"]}')
    if 'twitter:card' in p.metas and p.metas['twitter:card'] not in TWITTER_CARDS:
        W(f'unrecognised twitter:card: {p.metas["twitter:card"]}')
    og_img = p.metas.get('og:image', '')
    if og_img and not og_img.startswith('https://'):
        E(f'og:image without HTTPS: {og_img}')
    if og_img and 'og:image:alt' not in p.metas:
        W('og:image without og:image:alt')
    og_url = p.metas.get('og:url', '')
    if og_url and not og_url.startswith('https://'):
        E(f'og:url without HTTPS: {og_url}')
    if og_img.startswith(site_url):
        t, _, _ = resolve_internal(og_img, out, site_url)
        if t is not None and not t.exists():
            E(f'og:image does not exist in the output: {og_img}')

    # headings
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

    # images
    for img in p.imgs:
        src = img.get('src', '?')
        if not img.get('src') and not img.get('srcset'):
            W('<img> without src or srcset')
        if 'alt' not in img:
            E(f'<img> without alt: {src}')
        elif len(img['alt']) > ALT_MAX:
            W(f'alt of {len(img["alt"])} characters (> {ALT_MAX}): {src}')
        if not img.get('width') or not img.get('height'):
            W(f'<img> without width/height (CLS risk): {src}')

    # links with target="_blank" must carry rel="noopener"/"noreferrer"
    for meta in p.a_meta:
        if meta['target'] == '_blank':
            rel = (meta['rel'] or '').lower()
            if 'noopener' not in rel and 'noreferrer' not in rel:
                W(f'<a target="_blank"> without rel="noopener"/"noreferrer": {meta["href"][:60]}')

    # aria-current
    if p.aria_current > 1:
        E(f'{p.aria_current} elements with aria-current')

    # template leftovers / markers
    text = ' '.join(p.all_text)
    if '{{' in text or '{{' in str(p.canonical or '') or '{{' in title:
        E('unrendered {{...}} marker')
    if re.search(r'\bTODO\b|\[CONFIRM', text):
        W('contains TODO or [CONFIRM')

    # content
    if indexable and not is404:
        words = len(norm(' '.join(p.main_text)).split())
        if words < MIN_WORDS_INDEXABLE:
            W(f'thin content: {words} words in <main> (< {MIN_WORDS_INDEXABLE})')

    check_jsonld(rel_file, p, url, title, indexable, is404, errors, warnings)
    check_faq_matches_schema(rel_file, p, warnings, errors)


def walk_nodes(obj):
    """Iterate over all nested dicts of a JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_nodes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_nodes(v)


def check_jsonld(rel_file, p, url, title, indexable, is404, errors, warnings):
    E = lambda msg: errors.append((rel_file, msg))
    W = lambda msg: warnings.append((rel_file, msg))
    if not p.ld_raw:
        if indexable and not is404:
            E('indexable page without JSON-LD')
        return
    defined, refs, graph_nodes = {}, [], []
    for raw in p.ld_raw:
        try:
            data = json.loads(raw)
        except ValueError as e:
            E(f'invalid JSON-LD: {e}')
            continue
        if data.get('@context') not in ('https://schema.org', 'https://schema.org/', 'http://schema.org', 'http://schema.org/'):
            E('JSON-LD without schema.org @context')
        nodes = data.get('@graph') or [data]
        for n in nodes:
            graph_nodes.append(n)
            nid = n.get('@id')
            if nid:
                if nid in defined:
                    E(f'duplicate @id on the page: {nid}')
                defined[nid] = n
        for sub in walk_nodes(nodes):
            # a reference is a dict that contains only @id
            if set(sub.keys()) == {'@id'}:
                refs.append(sub['@id'])
    for r in refs:
        if r not in defined:
            E(f'undefined @id reference on the page: {r}')
    if indexable:
        types = {n.get('@type') for n in graph_nodes}
        for needed in ('ProfessionalService', 'WebSite'):
            if needed not in types:
                E(f'missing {needed} node in the JSON-LD')
    for n in graph_nodes:
        t = n.get('@type')
        if t in ('WebPage', 'CollectionPage', 'AboutPage', 'ContactPage'):
            if n.get('url') != url:
                E(f'{t}.url ({n.get("url")}) differs from the page URL ({url})')
            if n.get('name') and norm(n['name']) != title:
                W(f'{t}.name differs from <title>')
            dm = n.get('dateModified')
            if dm and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', dm):
                W(f'dateModified in non-ISO format: {dm}')
        if t == 'FAQPage':
            if not n.get('mainEntity'):
                E('FAQPage without mainEntity')
            else:
                for q in n.get('mainEntity', []):
                    if q.get('@type') != 'Question':
                        W(f'FAQPage.mainEntity with @type {q.get("@type")!r}, expected "Question"')
                    ans = q.get('acceptedAnswer') or {}
                    if ans.get('@type') != 'Answer':
                        W(f'FAQPage Question "{norm(q.get("name", ""))[:40]}" without acceptedAnswer @type="Answer"')


def check_faq_matches_schema(rel_file, p, warnings, errors):
    """JSON-LD FAQs must match the visible questions."""
    schema_faq = []
    for raw in p.ld_raw:
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        for n in data.get('@graph') or [data]:
            if n.get('@type') == 'FAQPage':
                for q in n.get('mainEntity', []):
                    schema_faq.append((norm(q.get('name', '')),
                                       norm(q.get('acceptedAnswer', {}).get('text', ''))))
    if not schema_faq:
        return
    visible = {q: a for q, a in p.faq}
    for q, a in schema_faq:
        if q not in visible:
            errors.append((rel_file, f'JSON-LD FAQ not visible on the page: "{q[:60]}"'))
        elif visible[q] != a:
            errors.append((rel_file, f'FAQ answer differs between JSON-LD and visible text: "{q[:60]}"'))


# --------------------------------------------------------------------------- site rules

def check_links(pages, out: Path, site_url: str, errors, warnings):
    """Internal links and resources: file and anchor existence."""
    inlinks = {rel: set() for rel in pages}
    for rel_file, p in pages.items():
        E = lambda msg, r=rel_file: errors.append((r, msg))
        W = lambda msg, r=rel_file: warnings.append((r, msg))
        for href, in_main, _ in p.links:
            href = href.strip()
            if not href:
                E('link with empty href')
                continue
            if href.startswith('mailto:'):
                if not re.fullmatch(r'mailto:[^@\s]+@[^@\s]+\.[^@\s?]+(\?.*)?', href):
                    E(f'malformed mailto: {href[:60]}')
                continue
            if href.startswith('tel:'):
                if not re.fullmatch(r'tel:\+?[\d\s().-]{6,}', href):
                    E(f'malformed tel: {href}')
                continue
            own_http = 'http://' + site_url.split('://', 1)[1]
            if href.startswith(own_http) and href[len(own_http):len(own_http) + 1] in ('', '/', '?', '#'):
                E(f'internal link with http instead of https: {href}')
                continue
            if href.startswith(('http://', 'https://')) and not href.startswith(site_url):
                if href.startswith('http://'):
                    W(f'external link without HTTPS: {href[:60]}')
                continue
            if href.startswith('//'):
                continue
            if href.startswith('#'):
                frag = href[1:]
                if frag and frag not in p.ids:
                    E(f'anchor not found on the same page: {href}')
                continue
            if not (href.startswith('/') or href.startswith(site_url)):
                W(f'relative link (an absolute path is better): {href[:60]}')
                continue
            target, frag, err = resolve_internal(href, out, site_url)
            if err:
                E(err)
                continue
            if target is None or not target.exists():
                E(f'broken internal link: {href}')
                continue
            if frag:
                key = str(target.relative_to(out))
                tp = pages.get(key)
                if tp is not None and frag not in tp.ids:
                    E(f'anchor not found: {href}')
            key = str(target.relative_to(out)) if target.exists() else None
            if key in inlinks and key != rel_file and in_main:
                inlinks[key].add(rel_file)
        for url, kind in p.resources:
            if url.startswith(('data:', 'http://', 'https://')) and not url.startswith(site_url):
                continue
            if kind.startswith('link:') and kind not in ('link:stylesheet', 'link:icon', 'link:apple-touch-icon', 'link:preload'):
                # alternate, describedby, canonical, sitemap... are checked the same way if internal
                pass
            target, _, err = resolve_internal(url, out, site_url)
            if err:
                continue
            if target is not None and not target.exists():
                E(f'missing resource ({kind}): {url}')
    # orphans: indexable pages without inbound contextual links
    for rel_file, p in pages.items():
        if rel_file in ('404.html', 'index.html') or not is_indexable(p):
            continue
        if len(inlinks[rel_file]) < MIN_CONTEXTUAL_INLINKS:
            warnings.append((rel_file, 'no inbound contextual links from other pages (menu/footer only)'))


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


def check_sitemap(pages, out: Path, site_url: str, errors, warnings):
    sm = out / 'sitemap.xml'
    if not sm.exists():
        return
    try:
        root = ET.fromstring(sm.read_text(encoding='utf-8'))
    except ET.ParseError as e:
        errors.append(('sitemap.xml', f'invalid XML: {e}'))
        return
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    in_sitemap, lastmods = {}, {}
    for u in root.findall('s:url', ns):
        loc = (u.findtext('s:loc', default='', namespaces=ns) or '').strip()
        lm = (u.findtext('s:lastmod', default='', namespaces=ns) or '').strip()
        if loc in in_sitemap:
            errors.append(('sitemap.xml', f'duplicate URL: {loc}'))
        in_sitemap[loc] = True
        lastmods[loc] = lm
        if not loc.startswith(site_url + '/'):
            errors.append(('sitemap.xml', f'URL outside the domain: {loc}'))
            continue
        target, _, err = resolve_internal(loc, out, site_url)
        if err or target is None or not target.exists():
            errors.append(('sitemap.xml', f'sitemap URL without a generated page: {loc}'))
        if lm and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', lm):
            warnings.append(('sitemap.xml', f'lastmod in non-ISO format: {loc} → {lm}'))
    indexable = {page_url(rel, site_url): p for rel, p in pages.items()
                 if is_indexable(p) and rel != '404.html'}
    for u in sorted(set(indexable) - set(in_sitemap)):
        errors.append(('sitemap.xml', f'indexable page missing from the sitemap: {u}'))
    for u in sorted(set(in_sitemap) - set(indexable)):
        if u.startswith(site_url + '/'):
            errors.append(('sitemap.xml', f'the sitemap includes a noindex or non-existent page: {u}'))
    # lastmod <-> JSON-LD dateModified consistency
    for u, p in indexable.items():
        for raw in p.ld_raw:
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            for n in data.get('@graph') or [data]:
                dm = n.get('dateModified')
                if dm and lastmods.get(u) and dm != lastmods[u]:
                    warnings.append(('sitemap.xml', f'lastmod {lastmods[u]} ≠ dateModified {dm} in {u}'))


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

def run_checks(out_dir, site_url: str = SITE_URL):
    """Return (errors, warnings): lists of (file, message) tuples."""
    out = Path(out_dir)
    errors, warnings = [], []
    if not out.is_dir():
        return [(str(out), 'the output folder does not exist: build first')], []
    files = sorted(out.rglob('*.html'))
    if not files:
        return [(str(out), 'no .html page found: the build is empty')], []
    for req in REQUIRED_FILES:
        if not (out / req).exists():
            errors.append((req, 'required file missing'))
    for rec in RECOMMENDED_FILES:
        if not (out / rec).exists():
            warnings.append((rec, 'recommended file missing'))
    pages = {}
    for f in files:
        rel = str(f.relative_to(out)).replace('\\', '/')
        try:
            pages[rel] = parse_page(f)
        except (OSError, UnicodeError, ValueError) as e:
            errors.append((rel, f'could not read/parse: {e}'))
    for rel, p in pages.items():
        check_page(rel, p, out, site_url, errors, warnings)
    check_duplicates(pages, errors)
    check_links(pages, out, site_url, errors, warnings)
    check_sitemap(pages, out, site_url, errors, warnings)
    check_robots(out, site_url, errors, warnings)
    return errors, warnings


def print_check_report(success, errors, warnings, n_pages, check_time, git_branch, git_commit, out_dir, strict):
    COL = 50
    LBL = 15
    W = 2 + LBL + 2 + COL  # interior width
    BANNER = str(SITE_CONFIG.get('check_banner', SITE_CONFIG.get('site_name', 'Legible') + ' • Site validator'))

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
        centered('✓  CHECK PASSED')
    else:
        centered('✗  CHECK FAILED')
    hr()

    centered('CHECK REPORT')
    hr()

    status = '✓  PASSED' if success else '✗  FAILED'
    row('Status', status)
    row('Branch', git_branch)
    row('Commit', git_commit)
    row('Check Time', check_time)
    row('Pages Checked', str(n_pages))
    row('Output Dir', str(out_dir))
    row('Strict Mode', str(strict))

    if success:
        hr()
        centered('✓  No issues')
    else:
        hr()
        if errors:
            centered('✗  Errors')
            for line in report_lines(errors, W - 2):
                print(f'║  {line:<{W-2}}║')
        if warnings:
            centered('⚠  Warnings (treated as errors)' if strict else '⚠  Warnings')
            for line in report_lines(warnings, W - 2):
                print(f'║  {line:<{W-2}}║')

    empty()
    if success:
        centered('Site checks passed')
    else:
        centered('Site checks failed — fix issues above')
    empty()
    print('╚' + '═' * W + '╝')


def main(argv=None):
    ap = argparse.ArgumentParser(description='SEO validator for the compiled output.')
    ap.add_argument('--dir', default=str(OUT_DEFAULT), help='compiled folder (default: dist/)')
    ap.add_argument('--site-url', default=SITE_URL)
    ap.add_argument('--strict', action='store_true', help='warnings also fail')
    args = ap.parse_args(argv)

    out = Path(args.dir)
    errors, warnings = run_checks(out, args.site_url)
    n_pages = len(list(out.rglob('*.html'))) if out.is_dir() else 0
    success = len(errors) == 0 and (not args.strict or len(warnings) == 0)
    check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    git_branch, git_commit = get_git_info()

    print_check_report(success, errors, warnings, n_pages, check_time, git_branch, git_commit, out, args.strict)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())