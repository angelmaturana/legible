#!/usr/bin/env python3
"""One test per validator rule (standard library only).

    python3 -B -m unittest tests.test_validator_rules

How it works: `fixtures.make_clean_project` builds a site for which `run_checks` reports NOTHING. Each row of
`RULES` changes ONE thing in one built page (`old` -> `new`, every occurrence) and states the exact message that
must appear, and nothing else. A rule that is deleted or changed breaks its row; a message that changes
text breaks it too. The ids (R01...) are those of the rule inventory in `docs/PLAN-refactor-check-site.md`.

Row: (id, page, old, new, severity, text, also)
  severity  'E' (error) or 'W' (warning)
  text      the exact message
  also      (severity, text) pairs of rules that the same change turns on legitimately (usually none)
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ.pop('SITE_URL', None)
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'legible'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_site  # noqa: E402
import fixtures  # noqa: E402

URL = fixtures.CLEAN_SITE_URL
HOME_TITLE, HOME_DESC = fixtures.CLEAN_PAGES['index']

LONG_TITLE = HOME_TITLE + ' plus a tail that goes past the limit'
SHORT_TITLE = 'Short title'
LONG_DESC = HOME_DESC + ' It goes on with more words, so that the description is longer than the limit of the validator.'
SHORT_DESC = 'A description that is too short.'

VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
ROBOTS = '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">\n'
DESCRIPTION_TAG = f'<meta name="description" content="{HOME_DESC}">\n'
CANONICAL = f'<link rel="canonical" href="{URL}/">\n'
OG_URL = f'<meta property="og:url" content="{URL}/">\n'
OG_TITLE = f'<meta property="og:title" content="{HOME_TITLE}">'
OG_IMAGE = f'<meta property="og:image" content="{URL}/images/og-image.png">'
OG_ALT = '<meta property="og:image:alt" content="Fixture Site">\n'
OG_WIDTH = '<meta property="og:image:width" content="1200">'
OG_SITE_NAME = '<meta property="og:site_name" content="Fixture Site">\n'
H1_TAG = f'<h1>{HOME_TITLE}</h1>'
H2_TAG = '<h2>More information</h2>'
MAIN_END = '</main>'
FILLER = 'This sentence is plain filler text with no claim in it. It only exists so that the page has enough words in the main area to count as real content for the validator. '
LONG_ALT = 'a' * 126
URL_DIFFERS = ('E', 'og:url differs from canonical')

# (id, page, old, new, severity, text, also)
RULES = [
    # --- basic <head> (R01-R11)
    ('R01', 'index.html', ' lang="en"', '', 'E', '<html> without lang attribute', ()),
    ('R02', 'index.html', 'lang="en"', 'lang="english"', 'W', "unusual lang value: 'english'", ()),
    ('R03', 'index.html', VIEWPORT, '', 'E', 'missing <meta name="viewport">', ()),
    ('R04', 'index.html', 'width=device-width, initial-scale=1', 'initial-scale=1', 'W',
     'viewport without width=device-width', ()),
    ('R05', 'index.html', f'<title>{HOME_TITLE}</title>', '<title></title>', 'E', 'missing <title>',
     (('W', 'og:title differs from <title>'), ('W', 'WebPage.name differs from <title>'))),
    ('R06', 'index.html', HOME_TITLE, LONG_TITLE, 'W', f'title of {len(LONG_TITLE)} characters (> 60)', ()),
    ('R07', 'index.html', HOME_TITLE, SHORT_TITLE, 'W', f'title too short ({len(SHORT_TITLE)} characters)', ()),
    ('R08', 'index.html', DESCRIPTION_TAG, '', 'E', 'missing meta description', ()),
    ('R09', 'index.html', HOME_DESC, LONG_DESC, 'W', f'description of {len(LONG_DESC)} characters (> 160)', ()),
    ('R10', 'index.html', HOME_DESC, SHORT_DESC, 'W', f'description too short ({len(SHORT_DESC)} characters)', ()),
    ('R11', 'index.html', ROBOTS, '', 'E', 'missing <meta name="robots">', ()),

    # --- canonical (R12-R16)
    ('R12', '404.html', '<meta name="robots" content="noindex, follow">\n',
     f'<meta name="robots" content="noindex, follow">\n<link rel="canonical" href="{URL}/404.html">\n', 'E',
     'the 404 page must not have canonical or og:url', ()),
    ('R13', 'index.html', CANONICAL, '', 'E', 'indexable page without canonical', ()),
    ('R14', 'index.html', CANONICAL, f'<link rel="canonical" href="{URL}/about/">\n', 'E',
     f'canonical {URL}/about/ does not match the expected URL {URL}/', (URL_DIFFERS,)),
    ('R15', 'index.html', CANONICAL, f'<link rel="canonical" href="{URL.replace("https", "http")}/">\n', 'E',
     f'canonical without HTTPS: {URL.replace("https", "http")}/',
     (('E', f'canonical {URL.replace("https", "http")}/ does not match the expected URL {URL}/'), URL_DIFFERS)),
    ('R16', 'index.html', OG_URL, f'<meta property="og:url" content="{URL}/other/">\n', 'E',
     'og:url differs from canonical', ()),

    # --- Open Graph / Twitter (R17-R27)
    ('R17', 'index.html', OG_SITE_NAME, '', 'W', 'missing og:site_name', ()),
    ('R18', 'index.html', OG_URL, '', 'W', 'missing og:url', ()),
    ('R19', 'index.html', OG_TITLE, '<meta property="og:title" content="Another title for social networks">', 'W',
     'og:title differs from <title>', ()),
    ('R20', 'index.html', 'content="en_US"', 'content="english"', 'W', 'unusual og:locale format: english', ()),
    ('R21', 'index.html', 'content="summary_large_image"', 'content="huge"', 'W', 'unrecognised twitter:card: huge', ()),
    ('R22', 'index.html', OG_IMAGE, '<meta property="og:image" content="http://fixture.test/images/og-image.png">', 'E',
     'og:image without HTTPS: http://fixture.test/images/og-image.png', ()),
    ('R23', 'index.html', OG_ALT, '', 'W', 'og:image without og:image:alt', ()),
    ('R24', 'index.html', OG_WIDTH, '<meta property="og:image:width" content="wide">', 'W',
     'og:image:width and og:image:height are not numbers: the engine could not read the size of og-image.png '
     '(see the build warning)', ()),
    ('R25', 'index.html', OG_WIDTH, '<meta property="og:image:width" content="1000">', 'W',
     'og:image is 1000x630: use at least 1200 px wide and a 1.91:1 ratio (1200x630)', ()),
    ('R26', 'index.html', OG_URL, f'<meta property="og:url" content="{URL.replace("https", "http")}/">\n', 'E',
     f'og:url without HTTPS: {URL.replace("https", "http")}/', (URL_DIFFERS,)),
    ('R27', 'index.html', OG_IMAGE, f'<meta property="og:image" content="{URL}/images/missing.png">', 'E',
     f'og:image does not exist in the output: {URL}/images/missing.png', ()),
    # --- headings (R28-R31)
    ('R28', 'index.html', H1_TAG, H1_TAG + '<h1>Second</h1>', 'E', 'expected 1 <h1>, found 2', ()),
    ('R29', 'index.html', H1_TAG, '<h2>Intro</h2>' + H1_TAG, 'W', 'the first heading is h2 ("Intro"), expected h1', ()),
    ('R30', 'index.html', H2_TAG, '<h4>More information</h4>', 'W', 'heading level skipped h1 → h4 ("More information")', ()),
    ('R31', 'index.html', H2_TAG, '<h2></h2>', 'E', 'empty h2 heading', ()),

    # --- images (R32-R35)
    ('R32', 'index.html', MAIN_END, '<img alt="x" width="1" height="1">' + MAIN_END, 'W', '<img> without src or srcset', ()),
    ('R33', 'index.html', MAIN_END, '<img src="/images/og-image.png" width="1" height="1">' + MAIN_END, 'E',
     '<img> without alt: /images/og-image.png', ()),
    ('R34', 'index.html', MAIN_END, f'<img src="/images/og-image.png" alt="{LONG_ALT}" width="1" height="1">' + MAIN_END, 'W',
     f'alt of {len(LONG_ALT)} characters (> 125): /images/og-image.png', ()),
    ('R35', 'index.html', MAIN_END, '<img src="/images/og-image.png" alt="x">' + MAIN_END, 'W',
     '<img> without width/height (CLS risk): /images/og-image.png', ()),

    # --- page body (R36-R41)
    ('R36', 'index.html', MAIN_END, '<p><a href="https://other.test/" target="_blank">Out</a></p>' + MAIN_END, 'W',
     '<a target="_blank"> without rel="noopener"/"noreferrer": https://other.test/', ()),
    ('R37', 'index.html', MAIN_END, '<p><a href="https://example.com/">Out</a></p>' + MAIN_END, 'W',
     'URL on a sample domain (example.com, example.org or example.net): https://example.com/; '
     'use the real address or remove the link', ()),
    ('R38', 'index.html', '<a class="nav-link" href="/about/">About</a>',
     '<a class="nav-link" href="/about/" aria-current="page">About</a>', 'E', '2 elements with aria-current', ()),
    ('R39', 'index.html', MAIN_END, '<p>{{ name }}</p>' + MAIN_END, 'E', 'unrendered {{...}} marker', ()),
    ('R40', 'index.html', MAIN_END, '<p>TODO</p>' + MAIN_END, 'W', 'contains TODO or [CONFIRM', ()),
    ('R41', 'index.html', FILLER, '', 'W', 'thin content: 13 words in <main> (< 250)', ()),

    # --- JSON-LD that is not a JSON value (R44, R45); R42 and R43 are the E/W helpers, not messages
    ('R44', 'index.html', '<script type="application/ld+json">', '<script type="text/plain">', 'E',
     'indexable page without JSON-LD', ()),
    ('R45', 'index.html', '"@context": "https://schema.org",', '"@context" "https://schema.org",', 'E',
     "invalid JSON-LD: Expecting ':' delimiter: line 3 column 16 (char 18)",
     (('E', 'missing WebSite node in the JSON-LD'),
      ('E', f'missing main node (@id {URL}/#business) in the JSON-LD'))),
]

def _node(data, kind):
    return next(n for n in data['@graph'] if n['@type'] == kind)


def _with_faq(main_entity):
    def change(data):
        data['@graph'].append({'@type': 'FAQPage', '@id': f'{URL}/#faq', 'mainEntity': main_entity})
        return data
    return change


def _set(kind, key, value):
    def change(data):
        _node(data, kind)[key] = value
        return data
    return change


def _graph_with(extra):
    def change(data):
        data['@graph'].append(extra)
        return data
    return change


QUESTION = {'@type': 'Question', 'name': 'Q1', 'acceptedAnswer': {'@type': 'Answer', 'text': 'A1'}}
VISIBLE_FAQ = '<details><summary>Q1</summary><p>A1</p></details>'
VISIBLE_FAQ_OTHER = '<details><summary>Q1</summary><p>Another answer</p></details>'


def _faq(*questions):
    return _graph_with({'@type': 'FAQPage', '@id': f'{URL}/#faq', 'mainEntity': list(questions)})


def _no_main(data):
    _node(data, 'Organization')['@id'] = f'{URL}/#other'
    return data


def _dup_website(data):
    data['@graph'].append(dict(_node(data, 'WebSite')))
    return data


def _context(value):
    def change(data):
        data['@context'] = value
        return data
    return change


def _no_website(data):
    _node(data, 'WebSite')['@type'] = 'Thing'
    return data


def _undefined_ref(data):
    _node(data, 'WebPage')['publisher'] = {'@id': f'{URL}/#nope'}
    return data


SHAPE = 'JSON-LD with an unexpected shape: '


# (id, change to the JSON-LD of index.html, html added at the end of <main>, severity, text, also)
LD_RULES = [
    ('R46', _context('https://schema.test'), '', 'E', 'JSON-LD without schema.org @context', ()),
    ('R47', _dup_website, '', 'E', f'duplicate @id on the page: {URL}/#website', ()),
    ('R48', _undefined_ref, '', 'E', f'undefined @id reference on the page: {URL}/#nope', ()),
    ('R49', _no_main, '', 'E', f'missing main node (@id {URL}/#business) in the JSON-LD',
     (('E', f'undefined @id reference on the page: {URL}/#business'),) * 2),
    ('R50', _no_website, '', 'E', 'missing WebSite node in the JSON-LD', ()),
    ('R51', _set('WebPage', 'url', f'{URL}/other/'), '', 'E',
     f'WebPage.url ({URL}/other/) differs from the page URL ({URL}/)', ()),
    ('R52', _set('WebPage', 'name', 'Different name'), '', 'W', 'WebPage.name differs from <title>', ()),
    ('R53', _set('WebPage', 'dateModified', '01/01/2026'), '', 'W', 'dateModified in non-ISO format: 01/01/2026',
     (('W', 'sitemap.xml', f'lastmod 2026-01-01 ≠ dateModified 01/01/2026 in {URL}/'),)),
    ('R54', _graph_with({'@type': 'FAQPage', '@id': f'{URL}/#faq'}), '', 'E', 'FAQPage without mainEntity', ()),
    ('R55', _faq(dict(QUESTION, **{'@type': 'Thing'})), VISIBLE_FAQ, 'W',
     'FAQPage.mainEntity with @type \'Thing\', expected "Question"', ()),
    ('R56', _faq(dict(QUESTION, acceptedAnswer={'text': 'A1'})), VISIBLE_FAQ, 'W',
     'FAQPage Question "Q1" without acceptedAnswer @type="Answer"', ()),
    ('R57', _faq(QUESTION), '', 'E', 'JSON-LD FAQ not visible on the page: "Q1"', ()),
    ('R58', _faq(QUESTION), VISIBLE_FAQ_OTHER, 'E', 'FAQ answer differs between JSON-LD and visible text: "Q1"', ()),
    # R89-R95 (added in F4): JSON-LD with an unexpected shape used to CRASH the build; now it is a message
    ('R89', lambda d: [{'@context': 'https://schema.org'}], '', 'E', SHAPE + 'the root is a list, expected an object',
     (('E', 'missing WebSite node in the JSON-LD'), ('E', f'missing main node (@id {URL}/#business) in the JSON-LD'))),
    ('R90', lambda d: None, '', 'E', SHAPE + 'the root is null, expected an object',
     (('E', 'missing WebSite node in the JSON-LD'), ('E', f'missing main node (@id {URL}/#business) in the JSON-LD'))),
    ('R91', _graph_with('x'), '', 'E', SHAPE + '@graph item is not an object: "x"', ()),
    ('R92', _with_faq({'@type': 'Question', 'name': 'Q'}), '', 'E', SHAPE + 'FAQPage.mainEntity is an object, expected a list', ()),
    ('R93', _with_faq(['a', 'b']), '', 'E', SHAPE + 'FAQPage.mainEntity item is not an object: "a"',
     (('E', SHAPE + 'FAQPage.mainEntity item is not an object: "b"'),)),
    ('R94', _set('WebPage', 'dateModified', 2024), '', 'W', 'dateModified is not text: 2024', ()),
    ('R95', _set('WebPage', 'name', 5), '', 'W', 'name is not text: 5', ()),
    # R96-R101 (added after F10): the other shapes that still crashed the build (unhashable @id, numbers as FAQ texts,
    # acceptedAnswer as text)
    ('R96', _graph_with({'@type': 'Thing', '@id': ['x']}), '', 'E', SHAPE + '@id is not text: ["x"]', ()),
    ('R97', _set('WebPage', 'publisher', {'@id': ['x']}), '', 'E', SHAPE + '@id is not text: ["x"]', ()),
    ('R98', _faq(dict(QUESTION, name=5)), VISIBLE_FAQ, 'W', 'FAQPage Question name is not text: 5', ()),
    ('R99', _faq(dict(QUESTION, acceptedAnswer={'@type': 'Answer', 'text': 5})), VISIBLE_FAQ, 'W',
     'FAQPage Answer text is not text: 5', ()),
    ('R100', _faq(dict(QUESTION, acceptedAnswer='A1')), VISIBLE_FAQ, 'W',
     'FAQPage Question "Q1" without acceptedAnswer @type="Answer"',
     (('E', 'FAQ answer differs between JSON-LD and visible text: "Q1"'),)),
    ('R101', _graph_with({'@type': 'Thing', '@id': 5}), '', 'E', SHAPE + '@id is not text: 5', ()),
    # R102-R104 (G1): an odd @type used to pass in silence; WebPage.url as a number was never pinned by a test
    ('R102', _graph_with({'@type': {'a': 1}, '@id': f'{URL}/#thing'}), '', 'W',
     'JSON-LD @type is not text or a list of texts: {"a": 1}', ()),
    ('R103', _graph_with({'@type': ['Thing', 5], '@id': f'{URL}/#thing'}), '', 'W',
     'JSON-LD @type is not text or a list of texts: ["Thing", 5]', ()),
    ('R104', _set('WebPage', 'url', 5), '', 'E', f'WebPage.url (5) differs from the page URL ({URL}/)', ()),
]


# --- site rules (R61-R88). Row: (id, [(page, old, new), ...], [(severity, file, text), ...]) = EXACT findings.
# R59, R60 are the E/W lambdas of `check_links` and R88 is the diagnosis `find_broken_markup` returns (below).
def _main(html):
    return [('index.html', '</main>', html + '</main>')]


LEGAL_LASTMOD = ('sitemap.xml', '/legal/</loc>\n        <lastmod>2026-01-01', '/legal/</loc>\n        <lastmod>%s')
ABOUT_TITLE = fixtures.CLEAN_PAGES['about'][0]
ABOUT_DESC = fixtures.CLEAN_PAGES['about'][1]
HOME_LINKS = '<a href="/about/">About us</a> <a href="/legal/">Legal notice</a>'
LEGAL_WARN = lambda a, b: f'lastmod {a} ≠ dateModified {b} in {URL}/legal/'  # noqa: E731
SITEMAP_END = '</urlset>'
SITEMAP_LEGAL = f'<url>\n        <loc>{URL}/legal/</loc>\n        <lastmod>2026-01-01</lastmod>\n    </url>\n'
LD_OPEN = '<script type="application/ld+json">'

SITE_RULES = [
    # --- links
    ('R61', _main('<a href="">x</a>'), [('E', 'index.html', 'link with empty href')]),
    ('R62', _main('<a href="mailto:bad">x</a>'), [('E', 'index.html', 'malformed mailto: mailto:bad')]),
    ('R63', _main('<a href="tel:abc">x</a>'), [('E', 'index.html', 'malformed tel: tel:abc')]),
    ('R64', _main('<a href="http://fixture.test/about/">x</a>'),
     [('E', 'index.html', 'internal link with http instead of https: http://fixture.test/about/')]),
    ('R65', _main('<a href="http://other.test/">x</a>'),
     [('W', 'index.html', 'external link without HTTPS: http://other.test/')]),
    ('R66', _main('<a href="#nope">x</a>'), [('E', 'index.html', 'anchor not found on the same page: #nope')]),
    ('R67', _main('<a href="about/">x</a>'),
     [('W', 'index.html', 'relative link (an absolute path is better): about/')]),
    ('R68', _main('<a href="/about">x</a>'), [('E', 'index.html', 'missing trailing slash in /about')]),
    ('R69', _main('<a href="/nothing/">x</a>'), [('E', 'index.html', 'broken internal link: /nothing/')]),
    ('R70', _main('<a href="/about/#nope">x</a>'), [('E', 'index.html', 'anchor not found: /about/#nope')]),
    ('R71', [('index.html', 'href="/css/site.css"', 'href="/css/missing.css"')],
     [('E', 'index.html', 'missing resource (link:stylesheet): /css/missing.css')]),
    ('R72', [('index.html', HOME_LINKS, '<a href="/about/">About us</a>')],
     [('W', 'legal/index.html', 'no inbound contextual links from other pages (menu/footer only)')]),

    # --- duplicates (the one that comes later in path order is reported)
    ('R73', [('about/index.html', f'<title>{ABOUT_TITLE}</title>', f'<title>{HOME_TITLE}</title>')],
     [('E', 'index.html', 'title duplicated with about/index.html'),
      ('W', 'about/index.html', 'og:title differs from <title>'),
      ('W', 'about/index.html', 'WebPage.name differs from <title>')]),
    ('R74', [('about/index.html', f'content="{ABOUT_DESC}"', f'content="{HOME_DESC}"')],
     [('E', 'index.html', 'description duplicated with about/index.html')]),

    # --- sitemap
    ('R75', [('sitemap.xml', SITEMAP_END, '')],
     [('E', 'sitemap.xml', 'invalid XML: no element found: line 16, column 0')]),
    ('R76', [('sitemap.xml', SITEMAP_END, f'<url><loc>{URL}/</loc></url>' + SITEMAP_END)],
     [('E', 'sitemap.xml', f'duplicate URL: {URL}/')]),
    ('R77', [('sitemap.xml', SITEMAP_END, '<url><loc>https://other.test/</loc></url>' + SITEMAP_END)],
     [('E', 'sitemap.xml', 'URL outside the domain: https://other.test/')]),
    ('R78', [('sitemap.xml', SITEMAP_END, f'<url><loc>{URL}/ghost/</loc></url>' + SITEMAP_END)],
     [('E', 'sitemap.xml', f'sitemap URL without a generated page: {URL}/ghost/'),
      ('E', 'sitemap.xml', f'the sitemap includes a noindex or non-existent page: {URL}/ghost/')]),
    ('R79', [(LEGAL_LASTMOD[0], LEGAL_LASTMOD[1], LEGAL_LASTMOD[2] % '01/01/2026')],
     [('W', 'sitemap.xml', f'lastmod in non-ISO format: {URL}/legal/ → 01/01/2026'),
      ('W', 'sitemap.xml', LEGAL_WARN('01/01/2026', '2026-01-01'))]),
    ('R80', [('sitemap.xml', SITEMAP_LEGAL, '')],
     [('E', 'sitemap.xml', f'indexable page missing from the sitemap: {URL}/legal/')]),
    ('R81', [('sitemap.xml', SITEMAP_END, f'<url><loc>{URL}/404.html</loc></url>' + SITEMAP_END)],
     [('E', 'sitemap.xml', f'the sitemap includes a noindex or non-existent page: {URL}/404.html')]),
    ('R82', [(LEGAL_LASTMOD[0], LEGAL_LASTMOD[1], LEGAL_LASTMOD[2] % '2026-02-02')],
     [('W', 'sitemap.xml', LEGAL_WARN('2026-02-02', '2026-01-01'))]),

    # --- robots
    ('R83', [('robots.txt', f'Sitemap: {URL}/sitemap.xml', '')],
     [('W', 'robots.txt', f'does not declare "Sitemap: {URL}/sitemap.xml"')]),
    ('R84', [('robots.txt', 'Allow: /', 'Disallow: /')],
     [('E', 'robots.txt', 'Disallow: / for all crawlers (blocks the whole site)')]),

    # --- run_checks
    ('R87', [('about/index.html', None, b'\xff\xfe<html>')],
     [('E', 'about/index.html', "could not read/parse: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"),
      ('E', 'sitemap.xml', f'the sitemap includes a noindex or non-existent page: {URL}/about/')]),
    ('R88', [('index.html', LD_OPEN, LD_OPEN.replace('json"', 'json'))],
     [('E', 'index.html', 'broken markup at line 32: the tag <script> never closes (an attribute quote or the ">" '
                          'is missing): <script type="application/ld+json> { "@context": "https:'),
      ('E', 'index.html', 'expected 1 <h1>, found 0'),
      ('E', 'index.html', 'indexable page without JSON-LD'),
      ('W', 'index.html', 'thin content: 0 words in <main> (< 250)'),
      ('W', 'about/index.html', 'no inbound contextual links from other pages (menu/footer only)'),
      ('W', 'legal/index.html', 'no inbound contextual links from other pages (menu/footer only)')]),
]
# R85 / R86 delete a file (the rows above only edit text)
MISSING_FILES = [
    ('R85', 'robots.txt', 'E', 'required file missing'),
    ('R86', 'llms.txt', 'W', 'recommended file missing'),
]


class _CleanBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        root = fixtures.make_clean_project(Path(cls._tmp.name) / 'clean')
        with contextlib.redirect_stdout(io.StringIO()):
            ok = build.build(root, no_validate=True)
        assert ok, 'the clean project does not build'
        cls.clean_out = root / 'dist'

    def mutated(self, page, old, new):
        """Copy of the clean output where `old` is replaced by `new` (every occurrence) in `page`. Returns its path."""
        out = Path(self._tmp.name) / f'mutated-{next(self._counter)}'
        shutil.copytree(self.clean_out, out)
        path = out / page
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text, f'the row does not apply to {page}: {old[:50]!r} not found')
        path.write_text(text.replace(old, new), encoding='utf-8', newline='')
        return out

    _counter = iter(range(1, 10**6))

    def findings(self, out):
        errors, warnings = check_site.run_checks(out, URL)
        return sorted([('E', f, m) for f, m in errors] + [('W', f, m) for f, m in warnings])

    def mutated_files(self, changes):
        """Copy of the clean output with several (file, old, new) edits; old=None deletes the file, bytes replace it."""
        out = Path(self._tmp.name) / f'mutated-{next(self._counter)}'
        shutil.copytree(self.clean_out, out)
        for page, old, new in changes:
            path = out / page
            if old is None and isinstance(new, bytes):
                path.write_bytes(new)
                continue
            text = path.read_text(encoding='utf-8')
            self.assertIn(old, text, f'the row does not apply to {page}: {old[:50]!r} not found')
            path.write_text(text.replace(old, new), encoding='utf-8', newline='')
        return out

    def with_jsonld(self, page, change, html=''):
        """Copy of the clean output where the JSON-LD of `page` is `change(current data)` (any JSON value)."""
        out = self.mutated(page, '<script type="application/ld+json">', '<script type="application/ld+json">')
        path = out / page
        text = path.read_text(encoding='utf-8')
        m = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', text, re.S)
        data = change(json.loads(m.group(2)))
        text = text[:m.start(2)] + json.dumps(data) + text[m.end(2):]
        path.write_text(text.replace('</main>', html + '</main>'), encoding='utf-8', newline='')
        return out


class RuleTable(_CleanBase):
    def test_clean_project_has_no_findings(self):
        """Without this test nothing else in the file is reliable: the base must report nothing."""
        self.assertEqual(check_site.run_checks(self.clean_out, URL), ([], []))

    def test_rule_ids_are_unique(self):
        ids = [row[0] for row in RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ld_rule_ids_are_unique_and_do_not_overlap(self):
        ids = [row[0] for table in (RULES, LD_RULES, SITE_RULES, MISSING_FILES) for row in table]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_jsonld_rule_fires_alone(self):
        for rule_id, change, html, severity, text, also in LD_RULES:
            with self.subTest(rule=rule_id):
                extra = [a if len(a) == 3 else (a[0], 'index.html', a[1]) for a in also]
                expected = sorted([(severity, 'index.html', text)] + extra)
                self.assertEqual(self.findings(self.with_jsonld('index.html', change, html)), expected)

    def test_each_site_rule_fires_alone(self):
        for rule_id, changes, expected in SITE_RULES:
            with self.subTest(rule=rule_id):
                self.assertEqual(self.findings(self.mutated_files(changes)), sorted(expected))

    def test_missing_files(self):
        for rule_id, name, severity, text in MISSING_FILES:
            with self.subTest(rule=rule_id):
                out = self.mutated(name, '', '')
                (out / name).unlink()
                self.assertEqual(self.findings(out), [(severity, name, text)])

    def test_consistent_faq_reports_nothing(self):
        out = self.with_jsonld('index.html', _faq(QUESTION), VISIBLE_FAQ)
        self.assertEqual(check_site.run_checks(out, URL), ([], []))

    def test_each_rule_fires_alone(self):
        for rule_id, page, old, new, severity, text, also in RULES:
            with self.subTest(rule=rule_id):
                expected = sorted([(severity, page, text)] + [(s, page, t) for s, t in also])
                self.assertEqual(self.findings(self.mutated(page, old, new)), expected)


class TestMalformedJsonLd(_CleanBase):
    """JSON-LD with an unexpected shape used to CRASH `run_checks` (and so the build) with a traceback; since F4 each
    case is a validator message. One test per case (the rows R89-R104 of `LD_RULES` also feed the golden)."""

    def check_row(self, rule_id):
        row = next(r for r in LD_RULES if r[0] == rule_id)
        _, change, html, severity, text, also = row
        out = self.with_jsonld('index.html', change, html)
        errors, warnings = check_site.run_checks(out, URL)          # must not raise
        extra = [a if len(a) == 3 else (a[0], 'index.html', a[1]) for a in also]
        self.assertEqual(self.findings(out), sorted([(severity, 'index.html', text)] + extra))
        self.assertTrue(errors or warnings)

    def test_root_is_a_list(self):
        self.check_row('R89')

    def test_root_is_null(self):
        self.check_row('R90')

    def test_graph_item_is_not_an_object(self):
        self.check_row('R91')

    def test_faq_main_entity_is_an_object(self):
        self.check_row('R92')

    def test_faq_main_entity_is_a_list_of_texts(self):
        self.check_row('R93')

    def test_date_modified_is_a_number(self):
        self.check_row('R94')

    def test_name_is_a_number(self):
        self.check_row('R95')

    def test_id_is_a_list(self):
        self.check_row('R96')

    def test_reference_id_is_a_list(self):
        self.check_row('R97')

    def test_faq_question_name_is_a_number(self):
        self.check_row('R98')

    def test_faq_answer_text_is_a_number(self):
        self.check_row('R99')

    def test_faq_accepted_answer_is_text(self):
        self.check_row('R100')

    def test_id_is_a_number(self):
        self.check_row('R101')

    def test_type_is_an_odd_value(self):
        self.check_row('R102')

    def test_type_is_a_list_with_a_number(self):
        self.check_row('R103')

    def test_web_page_url_is_a_number(self):
        self.check_row('R104')

    def test_a_list_of_texts_as_type_is_valid(self):
        change = _graph_with({'@type': ['Thing', 'Other'], '@id': f'{URL}/#thing'})
        out = self.with_jsonld('index.html', change)
        self.assertEqual(check_site.run_checks(out, URL), ([], []))

    def test_faq_with_null_name_does_not_crash(self):
        out = self.with_jsonld('index.html', _faq(dict(QUESTION, name=None)), VISIBLE_FAQ)
        check_site.run_checks(out, URL)

    def test_the_other_json_ld_readers_do_not_crash_either(self):
        """`sample_domain_urls` and `check_faq_matches_schema` read the same JSON-LD (the sitemap check ran above)."""
        for label, change in [(r[0], r[1]) for r in LD_RULES if r[0] in ('R89', 'R90', 'R91', 'R92', 'R93')]:
            with self.subTest(case=label):
                out = self.with_jsonld('index.html', change)
                p = check_site.parse_page(out / 'index.html')
                check_site.sample_domain_urls(p, URL)
                check_site.check_faq_matches_schema('index.html', p, [], [])


if __name__ == '__main__':
    unittest.main()
