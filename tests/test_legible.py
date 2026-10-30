#!/usr/bin/env python3
"""Minimal tests for legible. Standard library only.

    python3 -m unittest discover tests

What it covers (and nothing more; check_site.py already validates each page's HTML):
  1. Smoke: the template builds and passes check_site in strict mode.
  2. minify_css.
  3. minify_html.
  4. Guides and blog: valid and invalid front matter.
  5. Domain (SITE_URL) and unresolved markers.
  6. Geo tags and home links to guides and blog.
  7. FLOW_OFF.lock (the maintainer's local switch) is absent and gitignored.
  8. The suite does not depend on the template's sample pages or data (see "Page lookup" below).
  9. AGENTS.md: structure, router rows, limits, statuses and agreement with the other documents.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEGIBLE = REPO / 'legible'

# build.py reads SITE_URL on import: keep the caller's environment out of the tests.
os.environ.pop('SITE_URL', None)
sys.dont_write_bytecode = True  # tests must not leave legible/__pycache__/
sys.path.insert(0, str(LEGIBLE))
import build  # noqa: E402

PAGES = REPO / 'src' / 'pages'


# --------------------------------------------------------------------------- page lookup
# The tests never name a page of the template (`services/`, `pricing/`, `about/`...): an adapted site
# renames, replaces or drops them, and a suite that fails to import there is useless as a baseline.
# They ask for "a page that exists" instead. Anything that really reads the template's sample data
# is marked @ONLY_TEMPLATE.

def route_dir(route):
    """Folder of a route, relative to `src/pages/` or to the output: '/news/' -> 'news', '/' -> ''."""
    return route.strip('/')


def page_routes(pages_dir):
    """Routes (`/news/`) of the hand-written pages in `pages_dir`, alphabetical, home and 404 left out.

    Guide and blog pieces (front matter `type: guide` or `article`) are generated content, not pages."""
    pages_dir = Path(pages_dir)
    routes = []
    for f in pages_dir.rglob('index.html'):
        if f.parent == pages_dir:
            continue
        front, _ = build.parse_front_matter(f.read_text(encoding='utf-8'))
        if front.get('type') in ('guide', 'article'):
            continue
        routes.append('/' + f.parent.relative_to(pages_dir).as_posix() + '/')
    return sorted(routes)


def pick_page(pages_dir, accepts=None, what='an <h1>', skip=()):
    """(route, file) of the first page of `pages_dir` whose text `accepts` (default: it has an <h1>).

    The home page is the last resort; routes in `skip` are passed over. Fails, naming what was
    needed, if no page fits."""
    pages_dir = Path(pages_dir)
    accepts = accepts or (lambda text: '<h1' in text)
    for route in page_routes(pages_dir) + ['/']:
        f = pages_dir / route_dir(route) / 'index.html'
        if route not in skip and f.is_file() and accepts(f.read_text(encoding='utf-8')):
            return route, f
    raise AssertionError(f'no page of {pages_dir} has {what}; the tests need one page like that')


def has_dated_json_ld(text):
    """True when the page declares `updated` and repeats that date elsewhere (its JSON-LD `dateModified`)."""
    front, _ = build.parse_front_matter(text)
    return bool(front.get('updated')) and text.count(front['updated']) > 1


def is_indexable_with_description(text):
    """True for a page whose description the validator checks: it has one and is not `noindex`."""
    front, _ = build.parse_front_matter(text)
    return bool(front.get('description')) and 'noindex' not in front.get('robots', '')


def related_page(pages_dir):
    """A route a guide can use as its `service` (the field accepts any existing page): the first page, else home."""
    routes = page_routes(pages_dir)
    return routes[0] if routes else '/'


def write_stub_page(pages_dir, route):
    """Create the smallest valid page at `route` inside `pages_dir` (the home page for '/')."""
    d = Path(pages_dir) / route_dir(route)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text('---\ntitle: S\ndescription: S\n---\n<main></main>', encoding='utf-8')


def built_page(out, route):
    """The built file of a route inside the output folder."""
    return Path(out) / route_dir(route) / 'index.html'


SITE = json.loads((REPO / 'src' / 'data' / 'site.json').read_text(encoding='utf-8'))
TOPIC_1 = build.COLLECTION_TOPICS[0]
RELATED_PAGE = related_page(PAGES)           # a page that exists in this project, for the `service` field
WITHOUT_COLLECTIONS = not any((REPO / 'src' / 'pages' / c).exists() for c in ('guides', 'blog'))
IS_TEMPLATE = SITE.get('site_url', '').startswith('https://YOUR-DOMAIN')
ONLY_WITHOUT_COLLECTIONS = unittest.skipUnless(
    WITHOUT_COLLECTIONS, 'starts from a project without guides/ or blog/ (the template); this one has its own content')
ONLY_TEMPLATE = unittest.skipUnless(IS_TEMPLATE, 'checks the template\'s sample data')


# --------------------------------------------------------------------------- utilities

def copy_project(dest):
    """Copy src/ and legible/ to `dest` so the project can be changed without touching the original."""
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', 'dist', '.dev-dist')
    shutil.copytree(REPO / 'src', dest / 'src', ignore=ignore)
    shutil.copytree(LEGIBLE, dest / 'legible', ignore=ignore)
    return dest


def run_build(project, out, site_url=None, minify=True, strict=False):
    """Run the given project's build.py (without validating). Returns a CompletedProcess."""
    env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
    if site_url is not None:
        env['SITE_URL'] = site_url
    cmd = [sys.executable, str(project / 'legible' / 'build.py'),
           '--out', str(out), '--minify', 'true' if minify else 'false', '--no-validate']
    if strict:
        cmd.append('--strict')
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=project)


def run_check(project, out, site_url=None, strict=True):
    """Run check_site.py on `out`. Returns a CompletedProcess."""
    env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
    if site_url is not None:
        env['SITE_URL'] = site_url
    cmd = [sys.executable, str(project / 'legible' / 'check_site.py'), '--dir', str(out)]
    if strict:
        cmd.append('--strict')
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=project)


def read_all(out):
    """Text of every text file in `out`, keyed by relative path."""
    data = {}
    for f in Path(out).rglob('*'):
        if f.is_file() and f.suffix in ('.html', '.txt', '.xml', '.css', '.json'):
            data[f.relative_to(out).as_posix()] = f.read_text(encoding='utf-8')
    return data


def lorem(n_words):
    """Filler text with no markers and no words the validator forbids."""
    base = ('We explain calmly what to do first, what can wait until later '
            'and which mistakes keep repeating in similar businesses, without promising specific results. ')
    words = base.split()
    return ' '.join((words * (n_words // len(words) + 1))[:n_words]) + '.'


def piece_html(coll, slug, **over):
    """HTML of a valid guide or article. `over` replaces (or, with None, removes) front matter fields."""
    front = {
        'title': f'Test piece {slug} for the business | {{{{site_name}}}}',
        'description': f'Sample piece "{slug}" for the automated tests: it explains a specific case '
                       'without promises or guaranteed results.',
        'robots': 'index, follow',
        'canonical': 'auto',
        'type': 'guide' if coll == 'guides' else 'article',
        'topic': TOPIC_1,
        'published': '2026-01-10',
        'updated': '2026-02-15',
        'summary': 'Short summary of the test piece.',
        'service': RELATED_PAGE,
    }
    front.update(over)
    fm = '\n'.join(f'{k}: {v}' for k, v in front.items() if v is not None)
    url = f'{{{{site_url}}}}/{coll}/{slug}/'
    ld = json.dumps({'@context': 'https://schema.org', '@graph': [{
        '@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': front['title'],
        'description': front['description'], 'inLanguage': '{{in_language}}', 'dateModified': front['updated'],
        'isPartOf': {'@id': '{{site_url}}/#website'}, 'about': {'@id': '{{site_url}}/#business'}}]}, ensure_ascii=False)
    return f"""---
{fm}
---

<script type="application/ld+json">{ld}</script>

<main id="main">
    <section class="inner-hero page-width">
        <h1>Test piece {slug}</h1>
        <p class="lead">{lorem(60)}</p>
    </section>
    <section class="section page-width">
        <h2>First steps</h2>
        <p>{lorem(130)}</p>
        <p>{lorem(80)} If you want us to do it for you, see the
        <a href="{RELATED_PAGE}">related service</a>.</p>
    </section>
</main>
"""


def add_piece(project, coll, slug, **over):
    d = project / 'src' / 'pages' / coll / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(piece_html(coll, slug, **over), encoding='utf-8')


class TempProject(unittest.TestCase):
    """Base: a copy of the project and an output folder per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.project = copy_project(self.tmp / 'project')
        self.out = self.tmp / 'output'

    def build_ok(self, **kw):
        r = run_build(self.project, self.out, **kw)
        self.assertEqual(r.returncode, 0, f'the build should pass:\n{r.stdout}\n{r.stderr}')
        return r

    def check_ok(self, **kw):
        r = run_check(self.project, self.out, **kw)
        mode = 'strict' if kw.get('strict', True) else 'errors only'
        self.assertEqual(r.returncode, 0, f'check_site should pass ({mode}):\n{r.stdout}')
        return r

    def use_marker_in_a_page(self, marker):
        """Put `marker` before the <h1> of a page of the project. Returns the page's route and source path."""
        route, page = pick_page(self.project / 'src' / 'pages')
        page.write_text(page.read_text(encoding='utf-8').replace('<h1', f'<p>{marker}</p>\n<h1', 1), encoding='utf-8')
        return route, page.relative_to(self.project).as_posix()


# --------------------------------------------------------------------------- 1. smoke

class TestSmoke(unittest.TestCase):
    """Build the template as is and require a clean check_site (errors and warnings)."""

    def _build_and_validate(self, minify):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output'
            r = run_build(REPO, out, minify=minify)
            self.assertEqual(r.returncode, 0, f'build failed:\n{r.stdout}\n{r.stderr}')
            r = run_check(REPO, out)
            self.assertEqual(r.returncode, 0, f'check_site failed in strict mode:\n{r.stdout}')
            self.assertTrue((out / 'index.html').is_file())
            self.assertTrue((out / 'sitemap.xml').is_file())

    def test_template_minified(self):
        self._build_and_validate(minify=True)

    def test_template_unminified(self):
        self._build_and_validate(minify=False)

    def test_check_site_detects_an_error(self):
        """The smoke test only counts if check_site really fails when something is wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output'
            run_build(REPO, out)
            index = out / 'index.html'
            index.write_text(index.read_text(encoding='utf-8').replace('<h1', '<h2').replace('</h1>', '</h2>'),
                             encoding='utf-8')
            self.assertNotEqual(run_check(REPO, out).returncode, 0)

    def test_whatsapp_links_well_formed(self):
        """Regression: duplicated "?text=" and unencoded spaces in wa.me links."""
        import re
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output'
            run_build(REPO, out)
            links = [h for f in out.rglob('*.html')
                       for h in re.findall(r'href="(https://wa\.me/[^"]*)"', f.read_text(encoding='utf-8'))]
            self.assertTrue(links, 'the template should have WhatsApp links')
            for h in links:
                self.assertEqual(h.count('?'), 1, f'repeated "?" in {h}')
                self.assertNotIn(' ', h, f'unencoded spaces in {h}')

    def test_no_validate_mode_does_not_touch_the_project_output(self):
        """Building with --out must not write to the project's dist/."""
        existed = (REPO / 'dist').exists()
        with tempfile.TemporaryDirectory() as tmp:
            run_build(REPO, Path(tmp) / 'output')
        self.assertEqual((REPO / 'dist').exists(), existed)


# --------------------------------------------------------------------------- locales

class TestLocale(unittest.TestCase):
    def test_format_long_date_in_both_languages(self):
        self.assertEqual(build.format_long_date('2026-03-05', build.load_locale('en')), 'March 5, 2026')
        self.assertEqual(build.format_long_date('2026-03-05', build.load_locale('es')), '5 de marzo de 2026')


# --------------------------------------------------------------------------- 2. minify_css

class TestMinifyCss(unittest.TestCase):
    def m(self, css):
        return build.minify_css(css)

    def test_calc_keeps_operator_spaces(self):
        self.assertEqual(self.m('a{width:calc(100% - 2rem)}'), 'a{width:calc(100% - 2rem)}')
        self.assertEqual(self.m('a{width:calc(100%   +   2rem)}'), 'a{width:calc(100% + 2rem)}')

    def test_nested_calc_with_parentheses(self):
        self.assertEqual(self.m('a{width:calc( 100%  -  (2rem + 1px) )}'),
                         'a{width:calc(100% - (2rem + 1px))}')

    def test_clamp_min_max(self):
        self.assertEqual(self.m('a{width:clamp(1rem, 2.5vw, 2rem)}'), 'a{width:clamp(1rem,2.5vw,2rem)}')
        self.assertEqual(self.m('a{width:min(10px , 5vw);height:max(1px, 2px)}'),
                         'a{width:min(10px,5vw);height:max(1px,2px)}')

    def test_functions_with_decimal_numbers(self):
        out = self.m('a{padding:clamp(24px, 4.50vw, 48.0px)}')
        self.assertEqual(out, 'a{padding:clamp(24px,4.50vw,48.0px)}')

    def test_strings_are_untouched(self):
        self.assertEqual(self.m('a::before{content:"a  b: c;"}'), 'a::before{content:"a  b: c;"}')
        self.assertEqual(self.m("a::before{content:'x   y ; 0.50'}"), "a::before{content:'x   y ; 0.50'}")

    def test_string_with_escaped_quotes(self):
        css = r'a::before{content:"say \"hello  world\" now"}'
        self.assertEqual(self.m(css), css)

    def test_quoted_url(self):
        self.assertEqual(self.m('a{background:url("a  b.png")}'), 'a{background:url("a  b.png")}')

    def test_important(self):
        self.assertEqual(self.m('a{color:red ! important}'), 'a{color:red!important}')
        self.assertEqual(self.m('a{color:red   !important;margin:0}'), 'a{color:red!important;margin:0}')

    def test_comments_removed(self):
        self.assertEqual(self.m('/* hello */ a{b:c} /* bye\nmultiline */'), 'a{b:c}')

    def test_last_semicolon(self):
        self.assertEqual(self.m('a{b:c;d:e;}'), 'a{b:c;d:e}')

    def test_numbers(self):
        self.assertEqual(self.m('a{margin:0px 0.5em 1.0px 1.50rem}'), 'a{margin:0 .5em 1px 1.5rem}')
        self.assertEqual(self.m('a{opacity:0.50;line-height:1.0}'), 'a{opacity:.5;line-height:1}')

    def test_numbers_that_must_not_change(self):
        css = 'a{top:100px;z-index:100;margin:10px;width:20.05px;height:1.05em;flex:0 0 100px}'
        self.assertEqual(self.m(css), css)

    def test_hex_colors(self):
        self.assertEqual(self.m('a{color:#FFFFFF}'), 'a{color:#FFF}')
        self.assertEqual(self.m('a{color:#aabbcc}'), 'a{color:#abc}')
        self.assertEqual(self.m('a{color:#abcdef}'), 'a{color:#abcdef}')

    def test_selectors_and_combinators(self):
        self.assertEqual(self.m('a  >  b ~ c + d{x:y}'), 'a>b~c+d{x:y}')

    def test_media_query(self):
        self.assertEqual(self.m('@media (min-width: 768px) { a { b: c } }'), '@media (min-width:768px){a{b:c}}')

    def test_media_query_with_and_keeps_spaces(self):
        # `) and (` and `screen and (` cannot lose their space: the browser reads `and(` as a function.
        self.assertEqual(self.m('@media (min-width:1px) and (max-width:2px){a{b:c}}'),
                         '@media (min-width:1px) and (max-width:2px){a{b:c}}')
        self.assertEqual(self.m('@media screen  and  (min-width: 600px){a{b:c}}'),
                         '@media screen and (min-width:600px){a{b:c}}')

    def test_descendant_after_parenthesis(self):
        # `a:not(.b) .c` (descendant) must not become `a:not(.b).c` (same element).
        self.assertEqual(self.m('a:not(.b) .c{x:y}'), 'a:not(.b) .c{x:y}')
        self.assertEqual(self.m('a:not( .b )  .c{x:y}'), 'a:not(.b) .c{x:y}')

    def test_descendant_with_pseudo_class(self):
        # `a :hover` (descendant) and `a:hover` (a itself) are different selectors.
        self.assertEqual(self.m('a :hover{x:y}'), 'a :hover{x:y}')
        self.assertEqual(self.m('a:hover{x:y}'), 'a:hover{x:y}')

    def test_var_inside_calc(self):
        self.assertEqual(self.m('a{width:calc(var(--x) * 2)}'), 'a{width:calc(var(--x) * 2)}')
        self.assertEqual(self.m('a{width:calc(var(--a) + var(--b))}'), 'a{width:calc(var(--a) + var(--b))}')

    def test_negative_number_inside_calc(self):
        self.assertEqual(self.m('a{width:calc(100% + -1px)}'), 'a{width:calc(100% + -1px)}')

    def test_nested_math_functions(self):
        css = 'a{width:clamp(1px,calc(var(--a) * (1 + 2)),3px)}'
        self.assertEqual(self.m(css), css)

    def test_decimal_zero_with_unit(self):
        self.assertEqual(self.m('a{margin:0.0px}'), 'a{margin:0}')
        self.assertEqual(self.m('a{margin:-0.50em 0.0 1.0px}'), 'a{margin:-.5em 0 1px}')

    def test_zero_with_units_that_cannot_be_dropped(self):
        # For times, angles and percentages a unitless 0 is invalid or changes the meaning.
        css = 'a{transition:0s;width:0%;transform:rotate(0deg)}@keyframes k{0%{a:b}}'
        self.assertEqual(self.m(css), css)

    def test_zero_in_custom_property_keeps_the_unit(self):
        # `--x:0` inside calc(var(--x) + 1px) would be invalid.
        self.assertEqual(self.m('a{--gap:0px;margin:0px}'), 'a{--gap:0px;margin:0}')

    def test_unquoted_url_and_unicode_range_are_untouched(self):
        css = '@font-face{unicode-range:U+0025-00FF;src:url(fonts/a-0.50.woff2)}'
        self.assertEqual(self.m(css), css)

    def test_comment_inside_a_string_is_kept(self):
        css = 'a::after{content:"/* I am not a comment */"}'
        self.assertEqual(self.m(css), css)

    def test_pseudo_class_with_parentheses_without_descendant(self):
        # What site.css uses today: the child combinator after ")" is safe.
        self.assertEqual(self.m('li:nth-child( 2n + 1 ) > a{x:y}'), 'li:nth-child(2n+1)>a{x:y}')

    def test_real_minified_css_keeps_the_rules(self):
        """Same rules before and after: same number of braces and declarations."""
        css = (REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8')
        mini = build.minify_css(css)
        without_comments = build.re.sub(r'/\*[\s\S]*?\*/', '', css)
        self.assertEqual(mini.count('{'), without_comments.count('{'))
        self.assertEqual(mini.count('}'), without_comments.count('}'))
        self.assertEqual(mini.count('{'), mini.count('}'))
        self.assertLess(len(mini), len(css))

    def test_real_css_has_no_internal_marker_leftovers(self):
        mini = build.minify_css((REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8'))
        for leftover in ('__STR_', '__MATH_', '\x00'):
            self.assertNotIn(leftover, mini)


# --------------------------------------------------------------------------- 3. minify_html

class TestMinifyHtml(unittest.TestCase):
    def m(self, html):
        return build.minify_html(html)

    def test_attributes_with_double_spaces(self):
        self.assertEqual(self.m('<img alt="a  b" src="x">'), '<img alt="a  b" src="x">')
        self.assertEqual(self.m('<p title="z   w" data-x="a\n b">t</p>'), '<p title="z   w" data-x="a\n b">t</p>')

    def test_attributes_with_single_quotes(self):
        self.assertEqual(self.m("<input value='a  b'>"), "<input value='a  b'>")

    def test_attribute_with_greater_than(self):
        self.assertEqual(self.m('<p title="a > b">x</p>'), '<p title="a > b">x</p>')

    def test_pre_untouched(self):
        html = '<pre>a   b\n  c\n\n    d</pre>'
        self.assertEqual(self.m(html), html)

    def test_pre_with_tags_inside(self):
        html = '<pre class="x">  <code>one   two</code>\n  three</pre>'
        self.assertEqual(self.m(html), html)

    def test_textarea_untouched(self):
        html = '<textarea name="t">  a   b \n  c </textarea>'
        self.assertEqual(self.m(html), html)

    def test_valid_jsonld_is_compacted_and_stays_the_same_json(self):
        data = {'@context': 'https://schema.org', 'name': 'a  b', 'list': [1, 2, {'x': 'ñ  é'}]}
        src = '<script type="application/ld+json">\n' + json.dumps(data, indent=4, ensure_ascii=False) + '\n</script>'
        out = self.m(src)
        inner = out[out.index('>') + 1:out.rindex('</script>')]
        self.assertEqual(json.loads(inner), data)
        self.assertNotIn('\n', inner)
        self.assertLess(len(out), len(src))

    def test_broken_jsonld_is_untouched(self):
        src = '<script type="application/ld+json">{ broken:   unclosed </script>'
        self.assertEqual(self.m(src), src)

    def test_regular_script_untouched(self):
        src = '<script>var a = 1;   var b = 2;</script>'
        self.assertEqual(self.m(src), src)

    def test_style_untouched(self):
        src = '<style>a  {  color :  red  }</style>'
        self.assertEqual(self.m(src), src)

    def test_comments_removed(self):
        self.assertEqual(self.m('<!-- c --><p>x</p>'), '<p>x</p>')
        self.assertEqual(self.m('<p>a<!-- c\nmultiline -->b</p>'), '<p>ab</p>')

    def test_spaces_and_line_breaks_in_text(self):
        self.assertEqual(self.m('<p>hello   world\n\n  bye</p>'), '<p>hello world bye</p>')

    def test_structural_spaces_between_attributes(self):
        self.assertEqual(self.m('<a href="/x"   class="a"   >t</a>'), '<a href="/x" class="a">t</a>')

    def test_space_between_inline_elements_is_kept(self):
        # Regression: `<strong>x</strong> <small>y</small>` came out glued ("xy"). It happened on a pricing page.
        html = '<p><strong>299 €</strong> <small>(on request)</small></p>'
        self.assertEqual(self.m(html), html)
        self.assertEqual(self.m('<span>a</span>\n   <span>b</span>'), '<span>a</span> <span>b</span>')
        self.assertEqual(self.m('<p>t <b>x</b> <img src="a"> <a href="/">y</a></p>'),
                         '<p>t <b>x</b> <img src="a"> <a href="/">y</a></p>')

    def test_space_between_blocks_and_between_block_and_inline_is_removed(self):
        self.assertEqual(self.m('<li><a>1</a></li>\n<li><a>2</a></li>'), '<li><a>1</a></li><li><a>2</a></li>')
        self.assertEqual(self.m('<p>a</p> <span>b</span>'), '<p>a</p><span>b</span>')

    def test_pricing_keeps_the_price_space(self):
        html = self.m('<p><strong>99 €</strong> <small>/month</small></p>')
        self.assertIn('</strong> <small>', html)

    def test_space_between_blocks_is_removed(self):
        self.assertEqual(self.m('<div>\n  <p>a</p>\n  <p>b</p>\n</div>'), '<div><p>a</p><p>b</p></div>')

    def test_no_internal_markers_left(self):
        src = ('<script type="application/ld+json">{"a": 1}</script><pre>x</pre><p title="a  b">t</p>'
               '<textarea>q</textarea><style>a{}</style>')
        self.assertNotIn('\x00', self.m(src))

    def test_several_protected_blocks_are_restored_in_place(self):
        src = '<pre>1  1</pre><p>mid</p><pre>2  2</pre><textarea>3  3</textarea>'
        self.assertEqual(self.m(src), src)

    def test_real_page_keeps_the_visible_text(self):
        """The text of the built pages (ignoring whitespace) does not change when minifying."""
        from html.parser import HTMLParser

        class Text(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts, self.skip = [], 0

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.skip += 1

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self.skip -= 1

            def handle_data(self, d):
                if not self.skip:
                    self.parts.append(d)

        def without_spaces(html):
            t = Text()
            t.feed(html)
            return ''.join(''.join(t.parts).split())

        with tempfile.TemporaryDirectory() as tmp:
            raw, mini = Path(tmp) / 'raw', Path(tmp) / 'mini'
            self.assertEqual(run_build(REPO, raw, minify=False).returncode, 0)
            self.assertEqual(run_build(REPO, mini, minify=True).returncode, 0)
            pages = sorted(raw.rglob('*.html'))
            self.assertGreater(len(pages), 5)
            for f in pages:
                a = without_spaces(f.read_text(encoding='utf-8'))
                b = without_spaces((mini / f.relative_to(raw)).read_text(encoding='utf-8'))
                self.assertEqual(a, b, f'the text of {f.relative_to(raw)} changes when minifying')


# --------------------------------------------------------------------------- 4. guides and blog

class TestDirectCollections(unittest.TestCase):
    """load_collections on temporary folders: each error must say what is wrong and where."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pages = Path(self._tmp.name)
        write_stub_page(self.pages, RELATED_PAGE)

    def add(self, coll, slug, **over):
        d = self.pages / coll / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(piece_html(coll, slug, **over), encoding='utf-8')

    def problems(self):
        with self.assertRaises(build.CollectionError) as cm:
            build.load_collections(self.pages)
        return str(cm.exception)

    def test_no_collections(self):
        self.assertEqual(build.load_collections(self.pages), {'guides': [], 'blog': []})

    def test_valid_guide_and_article(self):
        self.add('guides', 'my-guide')
        self.add('blog', 'my-article')
        pieces = build.load_collections(self.pages)
        self.assertEqual([p['rel'] for p in pieces['guides']], ['/guides/my-guide/'])
        self.assertEqual([p['rel'] for p in pieces['blog']], ['/blog/my-article/'])
        self.assertEqual(pieces['guides'][0]['topic'], TOPIC_1)

    def test_slug_with_accents_or_uppercase(self):
        self.add('guides', 'guía-útil')
        self.add('guides', 'Uppercase')
        p = self.problems()
        self.assertIn('guía-útil', p)
        self.assertIn('lowercase, without accents', p)
        self.assertIn('Uppercase', p)

    def test_topic_outside_the_list(self):
        self.add('guides', 'a', topic='Invented')
        p = self.problems()
        self.assertIn('topic "Invented" is not in the taxonomy', p)
        self.assertIn(TOPIC_1, p, 'the message must list the valid topics')

    def test_related_with_more_than_two(self):
        for s in ('a', 'b', 'c', 'd'):
            self.add('guides', s)
        self.add('guides', 'e', related='/guides/a/, /guides/b/, /guides/c/')
        self.assertIn('related allows at most 2 links and has 3', self.problems())

    def test_related_to_a_missing_piece_or_to_itself(self):
        self.add('guides', 'a', related='/guides/does-not-exist/, /guides/a/')
        p = self.problems()
        self.assertIn('"/guides/does-not-exist/" is not an existing guide or article', p)
        self.assertIn('cannot point to the piece itself', p)

    def test_valid_related(self):
        self.add('guides', 'a', related='/blog/b/')
        self.add('blog', 'b', related='/guides/a/')
        build.load_collections(self.pages)

    def test_missing_required_field(self):
        self.add('guides', 'a', summary=None, service=None)
        p = self.problems()
        self.assertIn('missing "summary"', p)
        self.assertIn('missing "service"', p)

    def test_wrong_type_for_the_folder(self):
        self.add('guides', 'a', type='article')
        self.assertIn('type "article" is not valid in guides/', self.problems())

    def test_invalid_or_misordered_dates(self):
        self.add('guides', 'a', published='10/01/2026')
        self.add('guides', 'b', published='2026-05-01', updated='2026-01-01')
        p = self.problems()
        self.assertIn('is not an ISO date', p)
        self.assertIn('earlier than published', p)

    def test_service_that_does_not_exist(self):
        self.add('guides', 'a', service='/does-not-exist/')
        self.assertIn('service "/does-not-exist/" does not point to an existing page', self.problems())

    def test_handwritten_index_and_misplaced_path(self):
        (self.pages / 'guides').mkdir()
        (self.pages / 'guides' / 'index.html').write_text('---\ntitle: x\ndescription: x\n---\n', encoding='utf-8')
        (self.pages / 'blog').mkdir()
        (self.pages / 'blog' / 'loose.html').write_text('---\ntitle: x\ndescription: x\n---\n', encoding='utf-8')
        p = self.problems()
        self.assertIn('the /guides/ index is generated', p)
        self.assertIn('must be blog/<slug>/index.html', p)

    def test_collection_type_outside_its_folder(self):
        d = self.pages / 'other'
        d.mkdir()
        (d / 'index.html').write_text('---\ntitle: x\ndescription: x\ntype: guide\n---\n', encoding='utf-8')
        self.assertIn('is only allowed inside guides/ or blog/', self.problems())

    def test_reports_all_problems_at_once(self):
        self.add('guides', 'MAL', topic='x', published='no')
        self.assertGreaterEqual(self.problems().count('\n') + 1, 3)

    def test_blog_states(self):
        def arts(n):
            return [{'slug': str(i)} for i in range(n)]
        self.assertEqual(build.blog_state(arts(0)), 'none')
        self.assertEqual(build.blog_state(arts(1)), 'hidden')
        self.assertEqual(build.blog_state(arts(2)), 'hidden')
        self.assertEqual(build.blog_state(arts(3)), 'visible')
        self.assertFalse(build.blog_visible(arts(2)))
        self.assertTrue(build.blog_visible(arts(3)))


@ONLY_WITHOUT_COLLECTIONS
class TestCollectionsInTheBuild(TempProject):
    """Full build with pieces: index pages, menu, sitemap and build errors."""

    def test_without_guides_there_is_no_link_or_index(self):
        self.build_ok()
        self.assertFalse((self.out / 'guides').exists())
        self.assertFalse((self.out / 'blog').exists())
        self.assertNotIn('href="/guides/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_a_real_guide_appears_in_menu_index_sitemap_and_llms(self):
        add_piece(self.project, 'guides', 'my-first-guide')
        self.build_ok()
        self.check_ok(strict=False)
        self.assertTrue((self.out / 'guides' / 'index.html').is_file())
        self.assertTrue((self.out / 'guides' / 'my-first-guide' / 'index.html').is_file())
        self.assertIn('href="/guides/"', (self.out / 'index.html').read_text(encoding='utf-8'),
                      'the menu or the footer must link to /guides/')
        sitemap = (self.out / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('/guides/</loc>', sitemap)
        self.assertIn('/guides/my-first-guide/</loc>', sitemap)
        self.assertIn('/guides/my-first-guide/', (self.out / 'llms.txt').read_text(encoding='utf-8'))

    def test_blog_with_two_articles_is_noindex_and_not_announced(self):
        add_piece(self.project, 'blog', 'one')
        add_piece(self.project, 'blog', 'two')
        self.build_ok()
        self.check_ok(strict=False)
        index_html = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('noindex', index_html)
        self.assertNotIn('/blog/</loc>', (self.out / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertNotIn('href="/blog/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_blog_with_three_articles_is_indexable_and_in_the_menu(self):
        for s in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', s)
        self.build_ok()
        self.check_ok(strict=False)
        index_html = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('noindex', index_html)
        self.assertIn('/blog/</loc>', (self.out / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertIn('href="/blog/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_generated_indexes_have_contact_resolved(self):
        """Regression: the _lead_strip_html f-string left `mailto:{contact_email}` unreplaced."""
        add_piece(self.project, 'guides', 'a')
        for s in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', s)
        self.build_ok()
        for coll in ('guides', 'blog'):
            html = (self.out / coll / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('{contact_email}', html, coll)
            self.assertNotIn('{whatsapp_link}', html, coll)
            self.assertIn('mailto:', html)
            self.assertRegex(html, r'href="https://wa\.me/[^"]+"')

    def test_real_guide_passes_the_strict_validator(self):
        # Regression: the /guides/ index had ~120 words (minimum 250) and nothing linked to it from a <main>,
        # so `build.sh` (strict) failed as soon as there was a guide.
        add_piece(self.project, 'guides', 'my-first-guide')
        self.build_ok()
        self.check_ok(strict=True)

    def test_visible_blog_passes_the_strict_validator(self):
        # Regression: /blog/ had ~195 words and no incoming contextual link.
        for slug in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', slug)
        self.build_ok()
        self.check_ok(strict=True)

    def test_guides_and_blog_together_pass_the_strict_validator(self):
        add_piece(self.project, 'guides', 'my-guide', title='Test guide my-guide | {{site_name}}',
                  description='Sample guide for the automated tests: it explains a specific case without promises.')
        for slug in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', slug)
        self.build_ok()
        self.check_ok(strict=True)

    def test_home_links_to_guides_and_blog_only_if_they_exist(self):
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('home-resources', home)
        add_piece(self.project, 'guides', 'my-guide')
        add_piece(self.project, 'blog', 'one')   # a single article: the blog is not announced
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        main = home[home.index('<main'):home.index('</main>')]
        self.assertIn('href=/guides/', main.replace('"', ''))
        self.assertNotIn('href=/blog/', main.replace('"', ''))
        add_piece(self.project, 'blog', 'two')
        add_piece(self.project, 'blog', 'three')
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        main = home[home.index('<main'):home.index('</main>')]
        self.assertIn('href=/blog/', main.replace('"', ''))

    def test_custom_collection_paths_change_folders_and_urls(self):
        site = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(site.read_text(encoding='utf-8'))
        cfg['collection_paths'] = {'guides': 'how-to', 'blog': 'news'}
        site.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
        for coll, slug in (('how-to', 'my-guide'), ('news', 'one'), ('news', 'two'), ('news', 'three')):
            kind = 'guides' if coll == 'how-to' else 'blog'
            d = self.project / 'src' / 'pages' / coll / slug
            d.mkdir(parents=True)
            html = piece_html(kind, slug).replace(f'/{kind}/{slug}', f'/{coll}/{slug}')
            (d / 'index.html').write_text(html, encoding='utf-8')
        self.build_ok()
        self.check_ok(strict=True)
        self.assertTrue((self.out / 'how-to' / 'index.html').is_file())
        self.assertTrue((self.out / 'news' / 'one' / 'index.html').is_file())
        self.assertFalse((self.out / 'guides').exists())
        self.assertIn('/how-to/my-guide/</loc>', (self.out / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertIn('href="/how-to/"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_invalid_collection_paths_stop_the_build(self):
        site = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(site.read_text(encoding='utf-8'))
        for bad in ({'guides': 'Guías'}, {'guides': 'x', 'blog': 'x'}, {'other': 'x'}):
            cfg['collection_paths'] = bad
            site.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
            r = run_build(self.project, self.out)
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn('collection_paths', r.stderr)
            self.assertNotIn('Traceback', r.stderr)

    def test_invalid_front_matter_stops_the_build_with_a_useful_message(self):
        add_piece(self.project, 'guides', 'bad-guide', topic='Invented')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('invalid Guides/Blog front matter', r.stderr)
        self.assertIn('guides/bad-guide/index.html', r.stderr, 'must say which file has the problem')
        self.assertIn('topic "Invented"', r.stderr)
        self.assertNotIn('Traceback', r.stderr)


# --------------------------------------------------------------------------- language (full build)

class TestLanguageRegression(TempProject):
    """language in site.json, end to end: lang/og:locale, locale strings, errors and collection_paths."""

    def _set_language(self, value=None):
        site = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(site.read_text(encoding='utf-8'))
        if value is None:
            cfg.pop('language', None)
        else:
            cfg['language'] = value
        site.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')

    def test_default_build_is_english(self):
        self._set_language(None)
        self.build_ok()
        self.check_ok(strict=True)
        index_html = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<html lang="en"', index_html)
        self.assertIn('content="en_US"', index_html)

    def test_language_es_builds_and_validates_with_spanish_months_and_breadcrumb(self):
        self._set_language('es')
        add_piece(self.project, 'blog', 'one', published='2026-03-05', updated='2026-03-05')
        add_piece(self.project, 'blog', 'two')
        add_piece(self.project, 'blog', 'three')
        self.build_ok()
        self.check_ok(strict=True)
        index_html = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<html lang="es"', index_html)
        self.assertIn('content="es_ES"', index_html)
        blog_index = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('5 de marzo de 2026', blog_index, 'month name must be in Spanish')
        self.assertIn('Migas de pan', blog_index, 'breadcrumb aria-label must be in Spanish')
        self.assertIn('>Inicio<', blog_index, 'breadcrumb Home link must say Inicio')

    def test_unknown_language_fails_with_a_clear_message(self):
        self._set_language('fr')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unsupported language 'fr'", r.stderr)
        self.assertIn('supported: en, es', r.stderr)
        self.assertNotIn('Traceback', r.stderr)

    def test_collection_paths_localisation_works_together_with_language(self):
        self._set_language('en')
        site = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(site.read_text(encoding='utf-8'))
        cfg['collection_paths'] = {'guides': 'how-to', 'blog': 'blog'}
        site.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
        d = self.project / 'src' / 'pages' / 'how-to' / 'my-guide'
        d.mkdir(parents=True)
        html = piece_html('guides', 'my-guide', published='2026-03-05', updated='2026-03-05').replace(
            '/guides/my-guide', '/how-to/my-guide')
        (d / 'index.html').write_text(html, encoding='utf-8')
        self.build_ok()
        self.check_ok(strict=True)
        self.assertIn('<a href="/how-to/">Guides</a>', (self.out / 'index.html').read_text(encoding='utf-8'))
        guides_index = (self.out / 'how-to' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('>Home<', guides_index, 'locale label must be English regardless of the custom path')


# --------------------------------------------------------------------------- 5. domain and markers

class TestDomain(TempProject):
    def test_default_uses_the_sample_domain(self):
        self.build_ok()
        everything = read_all(self.out)
        self.assertIn(SITE['site_url'].rstrip('/') + '/', everything['index.html'])
        self.assertIn(SITE['site_url'].rstrip('/') + '/sitemap.xml', everything['robots.txt'])

    def test_site_url_changes_the_domain_across_the_output(self):
        self.build_ok(site_url='https://example.org')
        everything = read_all(self.out)
        for route, text in everything.items():
            self.assertNotIn('YOUR-DOMAIN', text, f'{route} keeps the default domain')
        a_page = built_page(self.out, pick_page(self.project / 'src' / 'pages')[0]).relative_to(self.out).as_posix()
        for route in ('index.html', a_page, 'robots.txt', 'llms.txt', 'sitemap.xml'):
            self.assertIn('https://example.org', everything[route], f'{route} does not use the new domain')
        self.assertIn('<link rel="canonical" href="https://example.org/">', everything['index.html'].replace('"/>', '">'))
        self.assertIn('https://example.org/sitemap.xml', everything['robots.txt'])

    def test_output_with_a_new_domain_passes_the_validator(self):
        self.build_ok(site_url='https://example.org')
        self.check_ok(site_url='https://example.org')

    def test_two_domains_do_not_mix(self):
        self.build_ok(site_url='https://one.example')
        self.assertFalse(any('two.example' in t for t in read_all(self.out).values()))
        self.build_ok(site_url='https://two.example')
        everything = read_all(self.out)
        self.assertFalse(any('one.example' in t for t in everything.values()), 'the second build keeps leftovers of the first')
        self.assertTrue(any('two.example' in t for t in everything.values()))

    def test_trailing_slash_is_removed(self):
        self.build_ok(site_url='https://example.org/')
        everything = read_all(self.out)
        self.assertNotIn('https://example.org//', ''.join(everything.values()))

    def test_empty_site_url_falls_back_to_site_json(self):
        """An empty SITE_URL (common in CI panels) must behave as if it were not set."""
        self.build_ok(site_url='')
        everything = read_all(self.out)
        self.assertIn(SITE['site_url'].rstrip('/') + '/', everything['index.html'])
        self.assertIn(SITE['site_url'].rstrip('/') + '/sitemap.xml', everything['robots.txt'])

    def test_invalid_domain_aborts_with_a_clear_message(self):
        for value in ('http://example.org', 'example.org'):
            r = run_build(self.project, self.out, site_url=value)
            self.assertNotEqual(r.returncode, 0, value)
            self.assertIn('SITE_URL must start with https://', r.stdout + r.stderr)
            self.assertNotIn('Traceback', r.stderr)

    def test_no_source_page_has_the_domain_hardcoded(self):
        """Regression: in src/ only {{site_url}} is allowed."""
        for f in (REPO / 'src').rglob('*'):
            if f.is_file() and f.suffix in ('.html', '.json', '.txt', '.css') and f.name != 'site.json':
                self.assertNotIn('YOUR-DOMAIN', f.read_text(encoding='utf-8'), f.relative_to(REPO).as_posix())


class TestMarkers(TempProject):
    def test_stray_marker_in_a_page_stops_the_build(self):
        route, _ = self.use_marker_in_a_page('{{made_up_marker}}')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{{made_up_marker}}', r.stderr + r.stdout)
        self.assertIn('texts.json', r.stderr + r.stdout)
        self.assertIn(route, r.stderr + r.stdout, 'must say which page it is on')
        self.assertNotIn('Traceback', r.stderr)

    def test_marker_resolved_from_texts_json(self):
        route, _ = self.use_marker_in_a_page('{{my_marker}}')
        texts = self.project / 'src' / 'data' / 'texts.json'
        data = json.loads(texts.read_text(encoding='utf-8'))
        data['my_marker'] = 'Text added from texts.json'
        texts.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertIn('Text added from texts.json', built_page(self.out, route).read_text(encoding='utf-8'))

    def test_computed_entity_json_values_win_over_texts_json(self):
        texts = self.project / 'src' / 'data' / 'texts.json'
        data = json.loads(texts.read_text(encoding='utf-8'))
        data['site_name'] = 'NAME-FROM-TEXTS'
        texts.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertNotIn('NAME-FROM-TEXTS', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_broken_texts_json_gives_a_clear_error(self):
        (self.project / 'src' / 'data' / 'texts.json').write_text('{ this is not json', encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('texts.json', r.stderr + r.stdout)
        self.assertNotIn('Traceback', r.stderr)

    def test_output_contains_no_markers(self):
        self.build_ok()
        for route, text in read_all(self.out).items():
            self.assertNotIn('{{', text, route)

    def _write_texts(self, **extra):
        texts = self.project / 'src' / 'data' / 'texts.json'
        data = json.loads(texts.read_text(encoding='utf-8'))
        data.update(extra)
        texts.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def _edit_entity(self, edit):
        path = self.project / 'src' / 'data' / 'entity.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        edit(data)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    @staticmethod
    def _business(data):
        nodes = data if isinstance(data, list) else data.get('@graph', [data])
        return next(n for n in nodes if 'areaServed' in n)

    def test_a_text_can_reference_an_earlier_text(self):
        """Regression: a text that uses another text defined BEFORE it used to fail with a misleading 'has no value'."""
        self._write_texts(nest_a='Alpha', nest_b='Beta {{nest_a}}')
        route, _ = self.use_marker_in_a_page('{{nest_b}}')
        r = self.build_ok()
        self.assertNotIn('Traceback', r.stderr)
        text = built_page(self.out, route).read_text(encoding='utf-8')
        self.assertIn('Beta Alpha', text)
        self.assertNotIn('{{', text)

    def test_circular_text_references_still_fail_cleanly(self):
        self._write_texts(circ_a='{{circ_b}}', circ_b='{{circ_a}}')
        self.use_marker_in_a_page('{{circ_a}}')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('has no value', r.stderr + r.stdout)
        self.assertNotIn('Traceback', r.stderr)

    def test_area_served_as_plain_strings_fails_with_a_clear_message(self):
        self._edit_entity(lambda d: self._business(d).__setitem__('areaServed', ['Madrid', 'Getafe']))
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('areaServed', r.stderr + r.stdout)
        self.assertNotIn('Traceback', r.stderr)

    def test_missing_free_offer_points_to_entity_json(self):
        """Without an offer priced 0, {{featured_action_name}} has no value: the message must point at entity.json."""
        def drop_free(d):
            for node in (d if isinstance(d, list) else d.get('@graph', [d])):
                for offer in node.get('hasOfferCatalog', {}).get('itemListElement', []):
                    if offer.get('price') in ('0', 0):
                        offer['price'] = '5'
        self._edit_entity(drop_free)
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        out = r.stderr + r.stdout
        self.assertIn('has no value', out)
        self.assertIn('derived marker', out)
        self.assertIn('entity.json', out)
        self.assertIn('first found on page', out)
        self.assertNotIn('Traceback', r.stderr)


class TestOptionalContactData(TempProject):
    """Regression: a derived site without email/telephone/address in entity.json used to crash
    the build with an unreadable TypeError/AttributeError instead of falling back to
    src/data/site.json, as DOCUMENTATION says optional business data should."""

    @staticmethod
    def _business(data):
        nodes = data if isinstance(data, list) else data.get('@graph', [data])
        return next(n for n in nodes if 'areaServed' in n)

    def _edit_entity(self, edit):
        path = self.project / 'src' / 'data' / 'entity.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        edit(data)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _edit_site(self, **over):
        path = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        cfg.update(over)
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')

    def _home(self):
        return (self.out / 'index.html').read_text(encoding='utf-8')

    def _published_with(self, needle):
        """Text of every built HTML page that contains `needle`."""
        return [text for route, text in read_all(self.out).items() if route.endswith('.html') and needle in text]

    def _assert_location_fallback(self):
        """The address printed by the pages comes from site.json "city"/"region" and never says None."""
        location = f'{SITE.get("city", "")}, {SITE.get("region", "")}'
        pages = self._published_with(location)
        self.assertTrue(pages, f'no page prints the site.json fallback address "{location}"')
        for text in pages:
            self.assertNotIn('None', text)

    def _assert_email_fallback(self):
        """The email printed by the pages comes from site.json "contact_email" and never says None."""
        email = SITE.get('contact_email', '')
        if not email:
            self.skipTest('site.json has no contact_email to fall back to')
        self.assertTrue(self._published_with(email), f'no page prints the site.json fallback email "{email}"')
        self.assertNotIn('None', self._home())

    def test_missing_contact_point_falls_back_to_site_json(self):
        self._edit_entity(lambda d: self._business(d).pop('contactPoint', None))
        r = self.build_ok()
        self.assertNotIn('Traceback', r.stderr)
        self.assertNotIn('None', self._home())

    def test_null_contact_point_falls_back_to_site_json(self):
        """entity.json may have "contactPoint": null, not just a missing key."""
        self._edit_entity(lambda d: self._business(d).__setitem__('contactPoint', None))
        r = self.build_ok()
        self.assertNotIn('Traceback', r.stderr)
        self.assertNotIn('None', self._home())

    def test_missing_telephone_with_no_fallback_omits_whatsapp_instead_of_crashing(self):
        self._edit_entity(lambda d: self._business(d)['contactPoint'].pop('telephone', None))
        self._edit_site(phone_e164='')
        self.build_ok()
        home = self._home()
        self.assertNotIn('wa.me', home)
        self.assertNotIn('None', home)

    def test_null_address_falls_back_to_site_json(self):
        """entity.json may have "address": null, not just a missing key."""
        self._edit_entity(lambda d: self._business(d).__setitem__('address', None))
        self.build_ok()
        self._assert_location_fallback()

    def test_missing_address_falls_back_to_site_json(self):
        self._edit_entity(lambda d: self._business(d).pop('address', None))
        self.build_ok()
        self._assert_location_fallback()

    def test_missing_email_falls_back_to_site_json(self):
        self._edit_entity(lambda d: self._business(d).pop('email', None))
        self.build_ok()
        self._assert_email_fallback()

    def test_null_email_falls_back_to_site_json(self):
        self._edit_entity(lambda d: self._business(d).__setitem__('email', None))
        self.build_ok()
        self._assert_email_fallback()


class TestSampleFallbacks(TempProject):
    """Regression: a marker for an offer, city or category that entity.json does not provide used to be
    filled with sample text ("Service 2", "$149", "City 4") and published with no warning at all."""

    @staticmethod
    def _business(data):
        nodes = data if isinstance(data, list) else data.get('@graph', [data])
        return next(n for n in nodes if 'areaServed' in n)

    def _edit_entity(self, edit):
        path = self.project / 'src' / 'data' / 'entity.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        edit(self._business(data))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    @staticmethod
    def _keep_two_offers(business):
        """Leave one paid offer and the free one, so the slots from 3 on have no data."""
        items = business['hasOfferCatalog']['itemListElement']
        free = [o for o in items if o.get('price') in ('0', 0)]
        business['hasOfferCatalog']['itemListElement'] = [o for o in items if o not in free][:1] + free

    # -- the pure functions

    def test_filled_slots_use_entity_values_and_report_no_fallback(self):
        business = {'knowsAbout': ['Plumbing'], 'areaServed': [{'name': 'Leeds'}],
                    'hasOfferCatalog': {'itemListElement': [{'name': 'Boiler repair', 'price': 120}]}}
        values, fallbacks = build.sample_slots(business)
        self.assertEqual(values['{{service_category_1}}'], 'Plumbing')
        self.assertEqual(values['{{city_1}}'], 'Leeds')
        self.assertEqual(values['{{service_1_name}}'], 'Boiler repair')
        self.assertEqual(values['{{service_1_price}}'], '120')
        self.assertFalse([m for m in fallbacks if '_1' in m], 'filled slots are not fallbacks')

    def test_empty_slots_get_a_sample_value_and_are_listed_as_fallbacks(self):
        values, fallbacks = build.sample_slots({'hasOfferCatalog': {'itemListElement': [{'name': 'Only', 'price': '5'}]}})
        self.assertEqual(values['{{service_2_name}}'], 'Service 2')
        self.assertEqual(values['{{service_2_price}}'], '$149')
        self.assertEqual(values['{{city_4}}'], 'City 4')
        self.assertIn('{{service_2_name}}', fallbacks)
        self.assertIn('hasOfferCatalog has 1 offer', fallbacks['{{service_2_name}}'][2])
        self.assertIn('areaServed has 0 entries', fallbacks['{{city_1}}'][2])

    def test_a_placeholder_or_null_value_counts_as_empty(self):
        business = {'knowsAbout': ['{{service_category_1}}', None],
                    'hasOfferCatalog': {'itemListElement': [{'name': None, 'price': '{{x}}'}]}}
        values, fallbacks = build.sample_slots(business)
        for marker in ('{{service_category_1}}', '{{service_category_2}}', '{{service_1_name}}', '{{service_1_price}}'):
            self.assertIn(marker, fallbacks, marker)

    def test_an_offer_without_a_price_does_not_publish_the_word_none(self):
        values, fallbacks = build.sample_slots({'hasOfferCatalog': {'itemListElement': [{'name': 'Quote only'}]}})
        self.assertNotIn('None', ''.join(values.values()))
        self.assertIn('offer 1 price is empty', fallbacks['{{service_1_price}}'][2])

    def test_free_offer_name_falls_back_only_when_it_has_none(self):
        values, fallbacks = build.sample_slots({'hasOfferCatalog': {'itemListElement': [{'name': 'Intro call', 'price': '0'}]}})
        self.assertEqual(values['{{featured_action_name}}'], 'Intro call')
        self.assertNotIn('{{featured_action_name}}', fallbacks)
        values, fallbacks = build.sample_slots({'hasOfferCatalog': {'itemListElement': [{'price': 0}]}})
        self.assertEqual(values['{{featured_action_name}}'], 'Free Consultation')
        self.assertIn('{{featured_action_name}}', fallbacks)
        values, _ = build.sample_slots({'hasOfferCatalog': {'itemListElement': [{'name': 'Paid', 'price': '9'}]}})
        self.assertNotIn('{{featured_action_name}}', values, 'with no free offer the marker must stay unresolved')

    def test_null_and_malformed_lists_do_not_raise_a_traceback(self):
        values, _ = build.sample_slots({'knowsAbout': None, 'areaServed': None, 'hasOfferCatalog': None})
        self.assertEqual(values['{{service_category_1}}'], 'Service 1')
        values, _ = build.sample_slots({'hasOfferCatalog': {'itemListElement': ['not an offer']}})
        self.assertEqual(values['{{service_1_name}}'], 'Service 1')
        with self.assertRaises(SystemExit):
            build.sample_slots({'knowsAbout': 'Plumbing'})

    def test_a_fallback_nobody_publishes_is_not_reported(self):
        _, fallbacks = build.sample_slots({})
        self.assertEqual(build.sample_fallback_warnings(fallbacks, set()), [])

    def test_markers_of_one_offer_are_reported_together_once(self):
        _, fallbacks = build.sample_slots({})
        hits = {'{{service_2_name}}', '{{service_2_price}}', '{{city_1}}'}
        warnings = build.sample_fallback_warnings(fallbacks, hits)
        self.assertEqual(len(warnings), 2)
        offer = next(msg for _, msg in warnings if '{{service_2_name}}' in msg)
        self.assertIn('{{service_2_price}}', offer)
        self.assertIn("'Service 2'", offer)
        self.assertIn('entity.json', offer)

    # -- the whole build

    @ONLY_TEMPLATE
    def test_the_template_has_no_sample_fallbacks_even_in_strict_mode(self):
        r = run_build(self.project, self.out, strict=True)
        self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
        self.assertIn('No warnings', r.stdout)

    def test_a_published_sample_value_is_a_warning_that_names_marker_and_page(self):
        self._edit_entity(self._keep_two_offers)
        _, source = self.use_marker_in_a_page('{{service_5_name}}')
        r = run_build(self.project, self.out)
        self.assertEqual(r.returncode, 0, 'without --strict it is only a warning')
        text = ' '.join(r.stdout.split())
        self.assertIn('{{service_5_name}}', text)
        self.assertIn("'Service 5'", text)
        self.assertIn('hasOfferCatalog has 2 offers', text)
        self.assertIn(source, text)
        self.assertNotIn('Traceback', r.stderr)

    def test_strict_mode_fails_on_a_published_sample_value(self):
        self._edit_entity(self._keep_two_offers)
        self.use_marker_in_a_page('{{service_5_name}}')
        r = run_build(self.project, self.out, strict=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Errors', r.stdout)
        self.assertIn('{{service_5_name}}', ' '.join(r.stdout.split()))
        self.assertNotIn('Traceback', r.stderr)

    def test_a_sample_value_that_no_page_uses_stays_silent(self):
        """Dropping every page that mentioned the last services leaves nothing to warn about."""
        self._edit_entity(self._keep_two_offers)
        for path in list((self.project / 'src').rglob('*.html')) + [self.project / 'src' / 'data' / 'texts.json',
                                                                    self.project / 'src' / 'static' / 'llms.txt']:
            text = path.read_text(encoding='utf-8')
            for n in range(3, 6):
                for suffix in ('name', 'price_number', 'price'):
                    text = text.replace('{{service_%d_%s}}' % (n, suffix), 'Fixed text')
            path.write_text(text, encoding='utf-8')
        entity = self.project / 'src' / 'data' / 'entity.json'
        entity.write_text(entity.read_text(encoding='utf-8').replace('{{service_category_3}}', 'Fixed').replace(
            '{{service_category_4}}', 'Fixed').replace('{{service_category_5}}', 'Fixed'), encoding='utf-8')
        r = run_build(self.project, self.out, strict=True)
        self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
        self.assertNotIn('sample value', ' '.join(r.stdout.split()))

    def test_build_script_fails_on_a_sample_value_unless_check_strict_is_false(self):
        self._edit_entity(self._keep_two_offers)
        self.use_marker_in_a_page('{{service_5_name}}')
        env = {k: v for k, v in os.environ.items() if k not in ('SITE_URL', 'CHECK_STRICT')}
        env['SITE_URL'] = 'https://example.com'
        def run_script(**extra):
            return subprocess.run(['bash', str(self.project / 'legible' / 'build.sh')], capture_output=True,
                                  text=True, cwd=self.project, env={**env, **extra})
        strict = run_script()
        self.assertNotEqual(strict.returncode, 0, 'strict by default')
        self.assertNotIn('Build finished', strict.stdout)
        relaxed = run_script(CHECK_STRICT='FALSE')
        self.assertIn('{{service_5_name}}', ' '.join(relaxed.stdout.split()), 'the warning is still shown')


class TestLeadStripContact(TempProject):
    """Regression: the closing strip of /guides/ and /blog/ always linked to WhatsApp. Without a telephone the
    link came out as href="" (the validator fails on it) and a business with no email got mailto:"".
    The line now offers only the channels the site has, and `lead_strip.contact_html` can replace it."""

    @staticmethod
    def _business(data):
        nodes = data if isinstance(data, list) else data.get('@graph', [data])
        return next(n for n in nodes if 'areaServed' in n)

    def _edit_entity(self, edit):
        path = self.project / 'src' / 'data' / 'entity.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        edit(self._business(data))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _edit_site(self, **over):
        path = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        cfg.update(over)
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')

    def _no_phone(self):
        self._edit_entity(lambda b: (b.get('contactPoint') or {}).pop('telephone', None))
        self._edit_site(phone_e164='')

    def _no_email(self):
        self._edit_entity(lambda b: b.pop('email', None))
        self._edit_site(contact_email='')

    def _strips(self):
        """The closing strip (`lead-strip` section) of the guides and blog indexes, built from scratch."""
        import re
        add_piece(self.project, 'guides', 'a')
        for s in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', s)
        self.build_ok()
        found = {}
        for coll in ('guides', 'blog'):
            page = (self.out / coll / 'index.html').read_text(encoding='utf-8')
            m = re.search(r'<section class="lead-strip.*?</section>', page, re.S)
            self.assertIsNotNone(m, f'/{coll}/ has no closing strip')
            found[coll] = m.group(0)
        return found

    # -- the function

    def test_the_contact_line_follows_the_available_channels(self):
        both = build._lead_strip_html(True, True)
        self.assertIn('mailto:{{contact_email}}', both)
        self.assertIn('href="{{whatsapp_link}}"', both)
        email_only = build._lead_strip_html(True, False)
        self.assertIn('mailto:{{contact_email}}', email_only)
        self.assertNotIn('whatsapp', email_only.lower())
        wa_only = build._lead_strip_html(False, True)
        self.assertIn('href="{{whatsapp_link}}"', wa_only)
        self.assertNotIn('mailto', wa_only)
        neither = build._lead_strip_html(False, False)
        self.assertNotIn('text-muted-lg', neither, 'no channel, no contact line')
        self.assertIn('class="button primary"', neither, 'the call-to-action button stays')

    def test_default_call_is_unchanged_for_other_callers(self):
        self.assertEqual(build._lead_strip_html(), build._lead_strip_html(True, True))

    def test_every_locale_has_the_three_contact_lines(self):
        en, es = build.load_locale('en'), build.load_locale('es')
        self.assertEqual(sorted(en), sorted(es), 'en.json and es.json must define the same keys')
        for data in (en, es):
            self.assertIn('{email}', data['lead_strip_contact_email_only'])
            self.assertNotIn('{whatsapp}', data['lead_strip_contact_email_only'])
            self.assertIn('{whatsapp}', data['lead_strip_contact_whatsapp_only'])
            self.assertNotIn('{email}', data['lead_strip_contact_whatsapp_only'])

    # -- the whole build

    @ONLY_TEMPLATE
    def test_with_both_channels_the_strip_is_the_one_it_always_was(self):
        for strip in self._strips().values():
            self.assertIn(f'mailto:{SITE["contact_email"]}', strip)
            self.assertRegex(strip, r'href="https://wa\.me/[^"]+"')

    def test_without_a_telephone_the_strip_has_only_the_email(self):
        self._no_phone()
        for coll, strip in self._strips().items():
            self.assertIn('mailto:', strip, coll)
            self.assertNotIn('WhatsApp', strip, coll)
            self.assertNotIn('href=""', strip, coll)

    def test_without_an_email_the_strip_has_only_whatsapp(self):
        self._no_email()
        for coll, strip in self._strips().items():
            self.assertRegex(strip, r'href="https://wa\.me/[^"]+"')
            self.assertNotIn('mailto', strip, coll)

    def test_without_any_contact_the_strip_keeps_its_button_and_no_empty_links(self):
        self._no_phone()
        self._no_email()
        for coll, strip in self._strips().items():
            self.assertIn('class="button primary"', strip, coll)
            self.assertNotIn('text-muted-lg', strip, coll)
            self.assertNotIn('href=""', strip, coll)
            self.assertNotIn('mailto', strip, coll)

    def test_contact_html_replaces_the_line_and_resolves_markers(self):
        self._no_phone()
        self._edit_site(generated_content={'lead_strip': {'contact_html': 'Visit us or write to {{contact_email}}.'}})
        for coll, strip in self._strips().items():
            self.assertIn(f'Visit us or write to {SITE["contact_email"]}.', strip, coll)
            self.assertNotIn('{{', strip, coll)

    def test_an_empty_contact_html_removes_the_line(self):
        self._edit_site(generated_content={'lead_strip': {'contact_html': ''}})
        for coll, strip in self._strips().items():
            self.assertNotIn('text-muted-lg', strip, coll)
            self.assertIn('class="button primary"', strip, coll)


class TestLocaleOverrides(TempProject):
    """Regression: the texts the engine generates (home resources, guides and blog indexes, closing strip,
    llms.txt) say "your business" and could not be changed from src/. `generated_content.locale_overrides`
    in site.json replaces any locale text, is validated (an unknown key or an empty text stops the build
    and names the key) and never touches the default output."""

    @staticmethod
    def _cfg(overrides):
        return {'generated_content': {'locale_overrides': overrides}}

    def _apply(self, overrides, language='en'):
        return build.apply_locale_overrides(build.load_locale(language), self._cfg(overrides), language)

    def _fails(self, overrides, *needles, language='en'):
        with self.assertRaises(SystemExit) as ctx:
            self._apply(overrides, language)
        message = str(ctx.exception)
        self.assertIn('locale_overrides', message)
        for needle in needles:
            self.assertIn(needle, message)
        return message

    def _edit_site(self, **over):
        path = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        cfg.update(over)
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')

    def _with_collections(self):
        add_piece(self.project, 'guides', 'a')
        for slug in ('one', 'two', 'three'):
            add_piece(self.project, 'blog', slug)

    # -- the function

    def test_without_overrides_the_locale_is_returned_as_it_is(self):
        locale = build.load_locale('en')
        for config in ({}, {'generated_content': {}}, {'generated_content': None},
                       {'generated_content': []}, {'generated_content': {'locale_overrides': None}}):
            self.assertIs(build.apply_locale_overrides(locale, config, 'en'), locale, config)

    def test_an_override_replaces_the_text_and_leaves_the_original_untouched(self):
        locale = build.load_locale('en')
        merged = build.apply_locale_overrides(locale, self._cfg({'nav_guides': 'Library'}), 'en')
        self.assertEqual(merged['nav_guides'], 'Library')
        self.assertEqual(locale['nav_guides'], 'Guides')
        self.assertEqual({k: v for k, v in merged.items() if k != 'nav_guides'},
                         {k: v for k, v in locale.items() if k != 'nav_guides'})

    def test_every_default_text_is_a_valid_override_of_itself(self):
        for language in ('en', 'es'):
            locale = build.load_locale(language)
            self.assertEqual(build.apply_locale_overrides(locale, self._cfg(dict(locale)), language), locale, language)

    def test_an_unknown_key_is_named_with_a_suggestion(self):
        self._fails({'home_resource_heading': 'x'}, '"home_resource_heading"', 'did you mean "home_resources_heading"',
                    'legible/locales/en.json')
        self._fails({'zzz': 'x'}, '"zzz"', 'no such key', language='es')

    def test_an_empty_or_wrong_typed_text_is_rejected(self):
        self._fails({'blog_index_lead': ''}, '"blog_index_lead"', 'non-empty')
        self._fails({'blog_index_lead': '   '}, '"blog_index_lead"', 'non-empty')
        self._fails({'nav_guides': 5}, '"nav_guides"', 'must be a text', 'int')
        self._fails({'nav_blog': None}, '"nav_blog"', 'must be a text')
        self._fails({'months': 'January'}, '"months"', '12')
        self._fails({'months': ['a'] * 11}, '"months"', '12')
        self._fails({'months': [''] + ['a'] * 11}, '"months"', '12')

    def test_overrides_must_be_an_object(self):
        self._fails(['nav_guides'], 'must be an object', 'list')
        self._fails('nav_guides', 'must be an object', 'str')

    def test_all_the_problems_are_reported_at_once(self):
        message = self._fails({'typo_key': 'x', 'nav_blog': '', 'nav_guides': 'Library'}, '2 problems', '"typo_key"', '"nav_blog"')
        self.assertNotIn('"nav_guides"', message, 'a valid override is not a problem')

    def test_placeholders_may_be_dropped_but_not_invented(self):
        merged = self._apply({'lead_strip_contact': 'Write to {email}', 'blog_index_lead': 'Notes for you.',
                              'lead_strip_lead_html': 'Ask for your {action_link} today.'})
        self.assertEqual(merged['lead_strip_contact'], 'Write to {email}')
        self._fails({'lead_strip_lead_html': 'Ask {action_url}'}, '"lead_strip_lead_html"', '{action_url}', '{action_link}')
        self._fails({'nav_guides': 'Guides {count}'}, '"nav_guides"', '{count}', 'no {placeholders}')
        self._fails({'lead_strip_contact_email_only': 'Call {whatsapp}'}, '{whatsapp}', '{email}')

    def test_site_markers_are_not_placeholders(self):
        merged = self._apply({'home_resources_heading': 'Resources from {{site_name}}',
                              'blog_index_lead': 'Notes from {{site_name}}; for steps, {guides_txt}.'})
        self.assertEqual(merged['home_resources_heading'], 'Resources from {{site_name}}')

    def test_the_date_format_and_the_months_can_be_overridden(self):
        merged = self._apply({'long_date': '{day}/{month}/{year}', 'months': [f'm{i}' for i in range(1, 13)]})
        self.assertEqual(build.format_long_date('2026-03-05', merged), '5/m3/2026')
        self._fails({'long_date': '{day} {'}, '"long_date"', 'not a valid date format')
        self._fails({'long_date': '{day} of {mes}'}, '"long_date"', '{mes}')

    def test_it_works_in_spanish_too(self):
        merged = self._apply({'nav_blog': 'Novedades'}, 'es')
        self.assertEqual(merged['nav_blog'], 'Novedades')
        self.assertEqual(merged['nav_guides'], build.load_locale('es')['nav_guides'])

    # -- the whole build

    def test_the_default_texts_are_published_when_nothing_is_overridden(self):
        self._with_collections()
        self.build_ok()
        locale = build.load_locale(SITE.get('language', 'en'))
        self.assertIn(locale['home_resources_heading'], (self.out / 'index.html').read_text(encoding='utf-8'))
        self.assertIn(locale['guides_index_lead'], (self.out / 'guides' / 'index.html').read_text(encoding='utf-8'))

    def test_overrides_reach_home_indexes_and_llms_with_markers_resolved(self):
        self._with_collections()
        self._edit_site(text={'zebra': 'Zebra Labs'}, generated_content={'locale_overrides': {
            'home_resources_heading': 'Resources from {{zebra}}',
            'guides_index_heading': 'Guides by {{zebra}}',
            'guides_index_lead': 'Practical help from {{zebra}}.',
            'blog_index_lead': 'Notes by {{zebra}}; for steps, {guides_txt}.',
            'lead_strip_headline': 'Talk to the {{zebra}} team',
            'llms_guides_description': 'Guides written by {{zebra}}.',
            'llms_blog_description': 'Articles by {{zebra}}.',
        }})
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        guides = (self.out / 'guides' / 'index.html').read_text(encoding='utf-8')
        blog = (self.out / 'blog' / 'index.html').read_text(encoding='utf-8')
        llms = (self.out / 'llms.txt').read_text(encoding='utf-8')
        self.assertIn('Resources from Zebra Labs', home)
        self.assertIn('Guides by Zebra Labs', guides)
        self.assertIn('Practical help from Zebra Labs.', guides)
        self.assertRegex(blog, r'Notes by Zebra Labs; for steps, see the <a href="/guides/">guides</a>\.')
        self.assertIn('Talk to the Zebra Labs team', guides)
        self.assertIn('Talk to the Zebra Labs team', blog)
        self.assertIn('Guides written by Zebra Labs.', llms)
        self.assertIn('Articles by Zebra Labs.', llms)
        for name, text in (('home', home), ('guides', guides), ('blog', blog), ('llms', llms)):
            self.assertNotIn('{{zebra}}', text, name)
            self.assertNotIn('{guides_txt}', text, name)

    def test_the_per_section_setting_wins_over_an_override(self):
        self._with_collections()
        self._edit_site(generated_content={
            'locale_overrides': {'guides_index_heading': 'From the locale', 'guides_index_lead': 'Lead from the locale.'},
            'guides_index': {'heading': 'From the section'}})
        self.build_ok()
        guides = (self.out / 'guides' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<h1>From the section</h1>', guides)
        self.assertNotIn('From the locale', guides)
        self.assertIn('Lead from the locale.', guides)

    def test_a_broken_override_stops_the_build_and_names_the_key(self):
        self._edit_site(generated_content={'locale_overrides': {'home_resource_heading': 'x'}})
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('"home_resource_heading"', r.stdout + r.stderr)
        self.assertIn('did you mean "home_resources_heading"', r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stdout + r.stderr)

    def test_card_labels_with_special_characters_keep_the_markup_valid(self):
        self._with_collections()
        self._edit_site(generated_content={'locale_overrides': {'card_read_guide': 'Read "the" guide & more'}})
        self.build_ok()
        guides = (self.out / 'guides' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Read &quot;the&quot; guide &amp; more', guides)
        self.assertNotIn('aria-label="Read "', guides)

    def test_the_override_of_the_date_reaches_the_published_pages(self):
        self._with_collections()
        self._edit_site(generated_content={'locale_overrides': {'long_date': '{day}.{month}.{year}'}})
        self.build_ok()
        self.assertRegex((self.out / 'blog' / 'index.html').read_text(encoding='utf-8'), r'>\d{1,2}\.[A-Za-zñé]+\.\d{4}</time>')


class TestSitemapDates(TempProject):
    def test_updated_and_json_ld_date_mismatch_fails_the_build(self):
        """Regression: changing only `updated` used to leave a stale sitemap lastmod and still pass."""
        route, page = pick_page(self.project / 'src' / 'pages', has_dated_json_ld,
                                what='an `updated` date that its JSON-LD repeats')
        text = page.read_text(encoding='utf-8')
        front, _ = build.parse_front_matter(text)
        old = front['updated']
        self.assertNotEqual(old, '2027-03-01')
        page.write_text(text.replace(f'updated: {old}', 'updated: 2027-03-01', 1), encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        out = r.stderr + r.stdout
        self.assertIn(route, out)
        self.assertIn('2027-03-01', out)
        self.assertIn(old, out)
        self.assertNotIn('Traceback', r.stderr)

    def test_matching_dates_pass(self):
        self.build_ok()
        sitemap = (self.out / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('<lastmod>', sitemap)

    @ONLY_TEMPLATE
    def test_every_sample_page_has_updated(self):
        for route in page_routes(PAGES) + ['/']:
            front, _ = build.parse_front_matter((PAGES / route_dir(route) / 'index.html').read_text(encoding='utf-8'))
            self.assertIn('updated', front, route)


# --------------------------------------------------------------------------- 6. geo tags

class TestGeo(TempProject):
    def test_geo_comes_from_business_data_not_a_fixed_value(self):
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertIn(f'name="geo.placename" content="{SITE["city"]}"', home.replace('\n', ' '))
        if SITE.get('geo_region_code'):
            self.assertIn(f'name="geo.region" content="{SITE["geo_region_code"]}"', home)
        else:
            self.assertNotIn('name="geo.region"', home, 'must not invent a region when there is no data')
        if IS_TEMPLATE:
            for route, content in read_all(self.out).items():
                self.assertNotIn('Valdemoro', content, route)

    @ONLY_TEMPLATE
    def test_geo_with_own_city_and_region(self):
        entity = self.project / 'src' / 'data' / 'entity.json'
        entity.write_text(entity.read_text(encoding='utf-8').replace('"{{city}}"', '"Seville"'), encoding='utf-8')
        texts = self.project / 'src' / 'data' / 'texts.json'
        texts_data = json.loads(texts.read_text(encoding='utf-8'))
        texts_data['geo_region'] = 'ES-AN'
        texts.write_text(json.dumps(texts_data, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('name="geo.placename" content="Seville"', home)
        self.assertIn('name="geo.region" content="ES-AN"', home)

    def test_without_geo_region_none_is_invented(self):
        self.assertEqual(build.render_geo(True, 'Seville', ''), '<meta name="geo.placename" content="Seville">')
        self.assertEqual(build.render_geo(True, '', ''), '')
        self.assertEqual(build.render_geo(False, 'Seville', 'ES-AN'), '')

    def test_geo_escapes_values(self):
        self.assertIn('content="A &amp; B"', build.render_geo(True, 'A & B', 'ES-MD'))

# --------------------------------------------------------------------------- output folder safety and CLI

class TestSafeOutput(unittest.TestCase):
    def rejected(self, path):
        """Run check_out_dir expecting an abort; capture the stderr message so it does not clutter the console."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            build.check_out_dir(path)
        self.assertIn('BUILD ABORTED', err.getvalue())

    def test_rejects_the_root_and_protected_folders(self):
        for path in (REPO, REPO / 'src', REPO / 'legible', REPO / 'src' / 'nested-output'):
            with self.subTest(path=path):
                self.rejected(path)

    def test_rejects_a_folder_that_contains_the_project(self):
        self.rejected(REPO.parent)

    def test_accepts_a_temporary_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.check_out_dir(Path(tmp) / 'output')

    def test_a_rejected_attempt_does_not_delete_repository_files(self):
        marker = REPO / 'src' / 'layout.html'
        before = marker.read_bytes()
        self.rejected(REPO)
        self.assertEqual(marker.read_bytes(), before)


class TestSpecialCharactersAndWarnings(TempProject):
    """Regressions: values with quotes/&, empty JSON-LD, a report that hid errors, and truncated messages."""

    NAME = 'Café "Ana" & Sons \\ Ltd.'

    def _with_name(self):
        path = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        cfg['site_name'] = self.NAME
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_quotes_and_ampersand_in_the_name_do_not_break_the_build(self):
        import re
        self._with_name()
        r = self.build_ok()
        self.assertNotIn('Traceback', r.stderr)
        for f in self.out.rglob('*.html'):
            text = f.read_text(encoding='utf-8')
            self.assertIn('<meta name="author" content="Café &quot;Ana&quot; &amp; Sons', text, f.name)
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
                names = {n.get('name') for n in json.loads(block)['@graph']}
                self.assertIn(self.NAME, names, f'{f.name}: the name must reach the JSON-LD intact')

    def test_name_with_special_characters_passes_the_validator(self):
        self._with_name()
        self.build_ok()
        r = run_check(self.project, self.out, strict=False)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_area_served_with_special_characters_is_escaped(self):
        """Regression: {{target_audience}} was the only derived marker not escaped, so the footer got raw `&` and `<`."""
        import re
        zone = 'Rock & Roll <City>'
        path = self.project / 'src' / 'data' / 'entity.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        nodes = data if isinstance(data, list) else data.get('@graph', [data])
        next(n for n in nodes if 'areaServed' in n)['areaServed'][0]['name'] = zone
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        self.build_ok()
        home = (self.out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('We help businesses in Rock &amp; Roll &lt;City&gt;', home)
        outside_json_ld = re.sub(r'<script type="application/ld\+json">.*?</script>', '', home, flags=re.S)
        self.assertNotIn('<City>', outside_json_ld)
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', home, re.S)
        self.assertTrue(blocks)
        self.assertTrue(any(zone in json.dumps(json.loads(b), ensure_ascii=False) for b in blocks),
                        'the zone name must reach the JSON-LD intact')
        r = run_check(self.project, self.out, strict=False)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_empty_price_range_is_not_published_in_json_ld(self):
        self.build_ok()
        self.assertNotIn('"priceRange"', (self.out / 'index.html').read_text(encoding='utf-8'))
        path = self.project / 'src' / 'data' / 'site.json'
        cfg = json.loads(path.read_text(encoding='utf-8'))
        cfg['price_range'] = '€€'
        path.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertIn('"priceRange":"€€"', (self.out / 'index.html').read_text(encoding='utf-8'))

    def _break(self):
        """One error (broken link) and one warning (short description) at once."""
        pages = self.project / 'src' / 'pages'
        link = re.compile(r'(<a\b[^>]*?\bhref=")/[a-z0-9][^"]*(")')
        route, linked = pick_page(pages, lambda text: bool(link.search(text)), what='a link to another page')
        linked.write_text(link.sub(r'\1/path-that-does-not-exist-with-a-fairly-long-name/\2',
                                   linked.read_text(encoding='utf-8'), count=1), encoding='utf-8')
        _, described = pick_page(pages, is_indexable_with_description,
                                 what='an indexable page with a description', skip=(route,))
        described.write_text(re.sub(r'^description:.*$', 'description: Short.', described.read_text(encoding='utf-8'),
                                    count=1, flags=re.M), encoding='utf-8')

    def test_build_report_shows_errors_even_with_warnings(self):
        self._break()
        r = subprocess.run([sys.executable, str(self.project / 'legible' / 'build.py'), '--out', str(self.out)],
                           capture_output=True, text=True, cwd=self.project)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Errors', r.stdout)
        self.assertIn('broken internal link', r.stdout)
        self.assertIn('description too short', r.stdout)

    def test_report_messages_are_not_truncated(self):
        self._break()
        self.build_ok()
        r = run_check(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        flat = ''.join(l.strip('║ ').strip() for l in r.stdout.splitlines())
        self.assertIn('/path-that-does-not-exist-with-a-fairly-long-name/', flat.replace('•', '').replace(' ', ''))

    def test_duplicate_jsonld_id_fails_the_build_and_names_the_id_and_the_page(self):
        """A page node that repeats an entity @id used to drop the whole JSON-LD silently (misleading later error)."""
        route, page = pick_page(self.project / 'src' / 'pages', lambda text: text.count('"@graph": [') == 1,
                                what='exactly one JSON-LD "@graph"')
        text = page.read_text(encoding='utf-8')
        page.write_text(text.replace(
            '"@graph": [', '"@graph": [{"@type": "ProfessionalService", "@id": "{{site_url}}/#business", "name": "Duplicate"},', 1),
            encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0, 'a duplicate @id must fail the build')
        self.assertIn('BUILD FAILED', r.stderr)
        self.assertIn('duplicate JSON-LD @id', r.stderr)
        self.assertIn('/#business', r.stderr)
        self.assertIn(route, r.stderr)
        self.assertNotIn('Traceback', r.stderr)

    def test_slug_containing_index_html_keeps_its_url(self):
        """The page URL drops only the final index.html: a folder named my-index.html-guide must not become my--guide."""
        slug = 'my-index.html-guide'
        _, source = pick_page(self.project / 'src' / 'pages')
        page = self.project / 'src' / 'pages' / slug / 'index.html'
        page.parent.mkdir(parents=True)
        page.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
        self.build_ok()
        text = (self.out / slug / 'index.html').read_text(encoding='utf-8')
        self.assertIn(f'/{slug}/', text)
        self.assertRegex(text, r'rel="canonical" href="https://[^"]+/' + slug + '/"')
        self.assertRegex(text, r'property="og:url" content="https://[^"]+/' + slug + '/"')
        self.assertNotIn('my--guide', text)

    def test_internal_http_link_is_an_error(self):
        self.build_ok()
        f = self.out / 'index.html'
        insecure = SITE['site_url'].replace('https://', 'http://').rstrip('/')
        f.write_text(f.read_text(encoding='utf-8').replace(
            '</main>', f'<p><a href="{insecure}{RELATED_PAGE}">c</a></p></main>', 1), encoding='utf-8')
        r = run_check(self.project, self.out, strict=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('http instead of https', r.stdout)


class TestCommandLine(unittest.TestCase):
    def build_py(self, *args):
        return subprocess.run([sys.executable, str(LEGIBLE / 'build.py'), *args],
                              capture_output=True, text=True, cwd=REPO)

    def test_unknown_argument_fails_without_traceback(self):
        r = self.build_py('--bogus')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('Traceback', r.stderr)

    def test_flags_without_value_or_with_invalid_value_fail_without_traceback(self):
        for args in (('--minify',), ('--out',), ('--minify', 'maybe')):
            with self.subTest(args=args):
                r = self.build_py(*args)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn('Traceback', r.stderr)

    def test_correct_usage_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.build_py('--minify', 'true', '--out', str(Path(tmp) / 'o'), '--no-validate')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(tmp) / 'o' / 'index.html').is_file())

    def _run_build_script(self, site_url=None):
        """Run build.sh of a temporary copy of the project (it writes to that copy's dist/)."""
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_project(Path(tmp) / 'project')
            env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
            if site_url is not None:
                env['SITE_URL'] = site_url
            return subprocess.run(['bash', str(project / 'legible' / 'build.sh')],
                                  capture_output=True, text=True, cwd=project, env=env)

    @ONLY_TEMPLATE
    def test_build_script_warns_when_the_sample_domain_is_used(self):
        """Forgetting SITE_URL must not pass silently, but it must not stop the build either."""
        r = self._run_build_script()
        self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
        self.assertIn('WARNING', r.stderr)
        self.assertIn('YOUR-DOMAIN', r.stderr)
        self.assertIn('Build finished in dist/', r.stdout)

    def test_build_script_does_not_warn_with_a_real_domain(self):
        r = self._run_build_script(site_url='https://example.com')
        self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
        self.assertNotIn('WARNING', r.stderr)

    def test_build_script_rejects_python_older_than_3_8(self):
        """The build script should explain the minimum version and stop before building."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp)
            fake_python = fake_bin / 'python3'
            fake_python.write_text(
                '#!/usr/bin/env bash\n'
                'if [[ "${1:-}" == "-c" ]]; then exit 1; fi\n'
                'if [[ "${1:-}" == "--version" ]]; then echo "Python 3.7.17"; exit 0; fi\n'
                'exit 2\n',
                encoding='utf-8')
            fake_python.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f'{fake_bin}{os.pathsep}{env.get("PATH", "")}'
            r = subprocess.run(['bash', str(LEGIBLE / 'build.sh')], capture_output=True, text=True,
                               cwd=REPO, env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Python 3.8 or newer is required', r.stderr)
            self.assertIn('Python 3.7.17', r.stderr)
            self.assertNotIn('Building and minifying', r.stdout)

    def test_standalone_validator_site_url_overrides_invalid_config(self):
        """--site-url must be applied before build.py validates site.json during import."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'project'
            copy_project(project)
            out = Path(tmp) / 'output'
            built = run_build(project, out, site_url='https://example.com')
            self.assertEqual(built.returncode, 0, f'{built.stdout}\n{built.stderr}')

            config_path = project / 'src' / 'data' / 'site.json'
            config = json.loads(config_path.read_text(encoding='utf-8'))
            config['site_url'] = 'http://invalid.example'
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

            without_override = run_check(project, out)
            self.assertNotEqual(without_override.returncode, 0)
            self.assertIn('SITE_URL must start with https://',
                          without_override.stdout + without_override.stderr)

            env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
            script = project / 'legible' / 'check_site.py'
            for flag in (['--site-url', 'https://example.com'], ['--site-url=https://example.com']):
                with self.subTest(flag=flag):
                    r = subprocess.run(
                        [sys.executable, str(script), '--dir', str(out), '--strict', *flag],
                        capture_output=True, text=True, env=env, cwd=project)
                    self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')


class TestFlowSwitch(unittest.TestCase):
    """FLOW_OFF.lock is a maintainer's local switch and must never ship in a zip."""

    def test_flow_off_lock_is_absent(self):
        self.assertFalse(
            (REPO / 'FLOW_OFF.lock').exists(),
            'FLOW_OFF.lock exists: run "legible flow on" (delete it) before packaging or distributing')

    def test_flow_off_lock_is_gitignored(self):
        gitignore = (REPO / '.gitignore').read_text(encoding='utf-8').splitlines()
        self.assertIn('FLOW_OFF.lock', gitignore)


# --------------------------------------------------------------------------- 8. independence from the sample pages

# Names of the template's sample pages and data. A line of this file may use them only if it says
# `# template-only` (the tests marked @ONLY_TEMPLATE that really read the sample data).
_SAMPLE_PAGE_NAMES = ('services', 'pricing', 'about', 'contact', 'featured-action', 'sample-service', 'privacy-policy', 'cookie-policy', 'legal-notice')  # template-only
_SAMPLE_DATA = ('Your City', 'Your Region', 'Your Business', 'hello@example.com')  # template-only
# Classes that build projects and edit pages: the ones that used to name a sample page.
_PAGE_EDITING_TESTS = ('TestMarkers', 'TestSitemapDates', 'TestDirectCollections', 'TestOptionalContactData',
                       'TestDomain', 'TestSpecialCharactersAndWarnings')


class TestPageLookup(unittest.TestCase):
    """The helpers that find "a page that exists" so the tests do not have to name one."""

    HTML = '---\ntitle: t\ndescription: d\n---\n<main><h1>x</h1></main>'

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pages = Path(self._tmp.name)

    def page(self, route, text=HTML):
        d = self.pages / route_dir(route)
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(text, encoding='utf-8')

    def test_route_dir(self):
        self.assertEqual((route_dir('/news/'), route_dir('/news/item/'), route_dir('/')), ('news', 'news/item', ''))

    def test_routes_are_alphabetical_and_leave_out_home_404_and_generated_pieces(self):
        for route in ('/', '/zeta/', '/alpha/', '/alpha/inner/'):
            self.page(route)
        (self.pages / '404.html').write_text(self.HTML, encoding='utf-8')
        self.page('/guides/g/', '---\ntype: guide\n---\n<h1>x</h1>')
        self.page('/blog/b/', '---\ntype: article\n---\n<h1>x</h1>')
        self.assertEqual(page_routes(self.pages), ['/alpha/', '/alpha/inner/', '/zeta/'])

    def test_pick_page_takes_the_first_page_that_fits(self):
        self.page('/', self.HTML + ' only-home')
        self.page('/a/', '---\ntitle: t\n---\n<main>no heading</main>')
        self.page('/b/')
        self.page('/c/')
        self.assertEqual(pick_page(self.pages)[0], '/b/', 'a page with no <h1> does not fit')
        self.assertEqual(pick_page(self.pages, skip=('/b/',))[0], '/c/')
        route, f = pick_page(self.pages, lambda text: 'only-home' in text)
        self.assertEqual((route, f), ('/', self.pages / 'index.html'), 'the home page is a valid page too')

    def test_pick_page_uses_home_as_the_last_resort_and_fails_clearly_without_a_match(self):
        self.page('/')
        self.assertEqual(pick_page(self.pages)[0], '/')
        with self.assertRaises(AssertionError) as cm:
            pick_page(self.pages, lambda text: False, what='a page nobody has')
        self.assertIn('a page nobody has', str(cm.exception))

    def test_related_page_is_the_first_page_or_home(self):
        self.assertEqual(related_page(self.pages), '/', 'a project with no pages but the home')
        self.page('/zeta/')
        self.page('/alpha/')
        self.assertEqual(related_page(self.pages), '/alpha/')

    def test_a_guide_can_point_to_home_or_to_a_nested_stub_page(self):
        """Regression: `service` was fixed to the template's first service and the whole suite stopped importing
        in a project without it."""
        for route in ('/', '/deep/page/'):
            with self.subTest(route=route):
                pages = self.pages / route_dir(route).replace('/', '_')
                pages.mkdir(exist_ok=True)
                write_stub_page(pages, route)
                d = pages / 'guides' / 'a'
                d.mkdir(parents=True)
                (d / 'index.html').write_text(piece_html('guides', 'a', service=route), encoding='utf-8')
                self.assertEqual(build.load_collections(pages)['guides'][0]['service'], route)

    def test_dated_json_ld_and_indexable_description_predicates(self):
        self.assertTrue(has_dated_json_ld('---\nupdated: 2026-01-02\n---\n"dateModified": "2026-01-02"'))
        self.assertFalse(has_dated_json_ld('---\nupdated: 2026-01-02\n---\nno repeated date'))
        self.assertFalse(has_dated_json_ld('---\ntitle: t\n---\nbody'))
        self.assertTrue(is_indexable_with_description('---\ndescription: d\nrobots: index, follow\n---\n'))
        self.assertFalse(is_indexable_with_description('---\ndescription: d\nrobots: noindex, follow\n---\n'))
        self.assertFalse(is_indexable_with_description('---\nrobots: index, follow\n---\n'))


class TestSuiteIsIndependentOfTheSamplePages(unittest.TestCase):
    """Regression: the suite named the template's pages (`services/`, `pricing/`, `about/`...) and its sample
    data. In an adapted site it did not even import (`_SERVICES[0]` raised IndexError), so every pilot lost
    the suite as a baseline. These two checks keep it that way."""

    def test_no_test_names_a_sample_page_or_its_data(self):
        names = '|'.join(re.escape(n) for n in _SAMPLE_PAGE_NAMES)
        patterns = [re.compile(r"/ '(?:%s)'" % names),               # a path join such as `pages / 'news'`
                    re.compile(r"(?<![\w.:/])/(?:%s)/" % names)]     # a route such as '/news/'
        patterns += [re.compile(re.escape(s)) for s in _SAMPLE_DATA]
        offenders = [f'line {n}: {line.strip()}'
                     for n, line in enumerate(Path(__file__).read_text(encoding='utf-8').splitlines(), 1)
                     if '# template-only' not in line and any(p.search(line) for p in patterns)]
        self.assertEqual(offenders, [], 'a test names a sample page or sample data: find the page with pick_page(), '
                                        'read the value from SITE, or mark the line `# template-only`')

    @ONLY_TEMPLATE
    def test_the_page_editing_tests_pass_in_a_site_whose_pages_were_renamed(self):
        """Rename every sample page, change the domain, the city and the email, and run those tests there."""
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_project(Path(tmp) / 'project')
            shutil.copytree(REPO / 'tests', project / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
            routes = sorted(page_routes(project / 'src' / 'pages'), key=len, reverse=True)
            top = sorted({r.split('/')[1] for r in routes})
            for name in top:
                (project / 'src' / 'pages' / name).rename(project / 'src' / 'pages' / f'x-{name}')
            for f in (project / 'src').rglob('*'):
                if f.is_file() and f.suffix in ('.html', '.json', '.txt', '.xml'):
                    text = f.read_text(encoding='utf-8')
                    for name in top:
                        text = text.replace(f'/{name}/', f'/x-{name}/')
                    f.write_text(text, encoding='utf-8')
            site = project / 'src' / 'data' / 'site.json'
            cfg = json.loads(site.read_text(encoding='utf-8'))
            cfg.update(site_url='https://adapted-site.test', city='Elsewhere', region='Another Region',
                       contact_email='write@adapted-site.test', project_stage='in_progress')
            site.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
            env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
            r = subprocess.run([sys.executable, '-B', '-m', 'unittest', *(f'test_legible.{c}' for c in _PAGE_EDITING_TESTS)],
                               capture_output=True, text=True, env=env, cwd=project / 'tests')
            self.assertEqual(r.returncode, 0, f'the suite fails in an adapted site:\n{r.stderr[-3000:]}')


# --------------------------------------------------------------------------- 9. AGENTS.md guards

def _agents_text():
    return (REPO / 'AGENTS.md').read_text(encoding='utf-8')


def _agents_section(text, n):
    """The text of `## n. ...` up to the next `## ` header ('' if it does not exist)."""
    m = re.search(r'^## %d\. .*?(?=^## \d+\. |\Z)' % n, text, re.S | re.M)
    return m.group(0) if m else ''


def _table_rows(block):
    return [line for line in block.splitlines() if line.startswith('|')]


class TestAgentsGuards(unittest.TestCase):
    """AGENTS.md is the entry point for AI agents (the router, the states, the limits). No other test reads it, so
    these static guards keep its structure, its figures and its agreement with DOCUMENTATION.md and the README.
    They check stable fragments, not whole paragraphs: rewording a sentence must not fail them."""

    @classmethod
    def setUpClass(cls):
        cls.agents = _agents_text()
        cls.docs = {name: (REPO / name).read_text(encoding='utf-8')
                    for name in ('AGENTS.md', 'DOCUMENTATION.md', 'README.md')}

    def test_the_ten_sections_exist_in_order(self):
        numbers = [int(n) for n in re.findall(r'^## (\d+)\. ', self.agents, re.M)]
        self.assertEqual(numbers, list(range(1, 11)))

    def test_section_references_point_to_existing_sections(self):
        bad = []
        for name, text in self.docs.items():
            if name == 'AGENTS.md':
                refs = re.findall(r'\bsections? ((?:\d+(?:\.\d+)?(?:, | and | to )?)+)', text)
            else:
                refs = re.findall(r'`?AGENTS\.md`?,? sections? ((?:\d+(?:\.\d+)?(?:, | and | to )?)+)', text)
            for group in refs:
                for number in re.findall(r'\d+(?:\.\d+)?', group):
                    if '.' not in number and not 1 <= int(number) <= 10:
                        bad.append(f'{name}: section {number}')
        self.assertEqual(bad, [], 'a reference points to a section AGENTS.md does not have')

    def test_every_mode_is_chosen_by_the_router_and_listed_in_the_modes_section(self):
        router = _agents_section(self.agents, 1)
        modes = _agents_section(self.agents, 3)
        for mode in ('Interview', 'Execution', 'Recovery', 'Refinement', 'Maintenance', 'Engine', 'One-session'):
            self.assertIn(f'**{mode} mode**', router, f'section 1 never routes to {mode} mode')
            self.assertIn(mode, modes, f'section 3 does not list {mode} mode')

    def test_the_router_rows_are_well_formed_and_keep_the_rows_added_for_the_edge_cases(self):
        router = _agents_section(self.agents, 1)
        start = router.index('| Plan | `project_stage` |')
        table = []
        for line in router[start:].splitlines():
            if not line.startswith('|'):
                break
            table.append(line)
        self.assertGreaterEqual(len(table), 14, 'the router table lost rows')
        for line in table:
            self.assertEqual(line.count('|'), 6, f'a router row must have 5 cells: {line[:70]}')
        joined = '\n'.join(table)
        for fragment in ('`legible help`', 'one session', '`engine mode`', '`legible start` with inputs',
                         'any other value', 'Recovery mode', 'Refinement mode', 'Interview mode'):
            self.assertIn(fragment, joined, f'the router table lost its row for: {fragment}')

    def test_the_commands_are_in_agents_the_readme_and_the_documentation(self):
        commands = ('legible start', 'legible continue', 'legible help', 'legible flow off', 'legible flow on')
        top = self.agents.split('## 1. ')[0]
        for name, text in self.docs.items():
            scope = top if name == 'AGENTS.md' else text
            for command in commands:
                self.assertIn(f'`{command}`', scope, f'{name} does not list `{command}`')

    def test_the_plan_limits_are_stated_and_agree_with_each_other(self):
        plan = _agents_section(self.agents, 5)
        for fragment in ('120 lines or fewer', 'wc -l SITE_PLAN.md', "grep -cE '^\\| *[0-9]+ *\\|' SITE_PLAN.md",
                         'ten phases', 'twelve', 'three pages or three large files'):
            self.assertIn(fragment, plan, f'section 5 lost: {fragment}')
        budget5 = set(re.findall(r'\b(\d{2},?\d{3}) bytes', plan))
        budget6 = set(re.findall(r'\b(\d{2},?\d{3}) bytes', _agents_section(self.agents, 6)))
        self.assertEqual({b.replace(',', '') for b in budget5}, {'50000'}, 'the session budget changed in section 5')
        self.assertEqual({b.replace(',', '') for b in budget6}, {'50000'}, 'sections 5 and 6 disagree on the budget')

    def test_the_plan_template_respects_its_own_limits(self):
        template = re.search(r'````markdown\n(.*?)\n````', self.agents, re.S).group(1)
        self.assertLessEqual(len(template.splitlines()), 120)
        phases = [line for line in template.splitlines() if re.match(r'^\| *[0-9]+ *\|', line)]
        self.assertEqual(len(phases), 10, 'the default catalogue is ten phases')
        self.assertEqual([re.match(r'^\| *(\d+)', p).group(1) for p in phases], [str(i) for i in range(1, 11)])

    def test_the_statuses_are_in_the_template_and_in_the_plan_validation(self):
        plan = _agents_section(self.agents, 5)
        validation = re.search(r'\*\*Validate the plan first\*\*.*?\*\*Without a shell\*\*', self.agents, re.S)
        self.assertIsNotNone(validation, 'section 6 lost "Validate the plan first" or "Without a shell"')
        for status in ('pending', 'in_progress', 'done', 'blocked'):
            self.assertIn(f'`{status}`', plan.split('Allowed phase statuses:')[1].splitlines()[0])
            self.assertIn(f'`{status}`', validation.group(0))
        status_line = next(l for l in plan.splitlines() if l.startswith('**Status:**'))
        for status in ('not started', 'in progress', 'complete', 'complete (example data: N)'):
            self.assertIn(status, status_line)
            self.assertIn(status, validation.group(0))

    def test_no_document_runs_the_build_with_the_example_domain(self):
        for name, text in self.docs.items():
            blocks = re.findall(r'```.*?```', text, re.S)
            self.assertFalse([b for b in blocks if 'SITE_URL=https://example.com' in b],
                             f'{name}: a code block sets SITE_URL=https://example.com (it fills dist/ with that domain)')

    def test_nothing_asks_to_write_a_confirm_marker(self):
        """The marker is only described (the validator and the sweep detect it); facts that are missing keep the sample value."""
        allowed = ('validator', 'sweep', 'grep', 'hits', 'Leftovers', 'no `[CONFIRM', 'No `[CONFIRM')
        offenders = [f'{name}: {line.strip()[:90]}' for name, text in self.docs.items()
                     for line in text.splitlines()
                     if '[CONFIRM' in line and not any(a in line for a in allowed)]
        self.assertEqual(offenders, [], 'a document mentions `[CONFIRM` in a way that may ask the AI to write it')

    def test_the_lessons_log_does_not_come_back(self):
        for name, text in self.docs.items():
            self.assertNotIn('lessons-log', text.lower(), f'{name} mentions a LESSONS-LOG')


if __name__ == '__main__':
    unittest.main()
