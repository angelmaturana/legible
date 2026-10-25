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
"""
import contextlib
import io
import json
import os
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

SITE = json.loads((REPO / 'src' / 'data' / 'site.json').read_text(encoding='utf-8'))
TOPIC_1 = build.COLLECTION_TOPICS[0]
_SERVICES = sorted(p.parent.name for p in (REPO / 'src' / 'pages' / 'services').glob('*/index.html'))
SERVICE_SLUG = _SERVICES[0]                  # a service that exists in this project
SERVICE = f'/services/{SERVICE_SLUG}/'
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


def run_build(project, out, site_url=None, minify=True):
    """Run the given project's build.py (without validating). Returns a CompletedProcess."""
    env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
    if site_url is not None:
        env['SITE_URL'] = site_url
    return subprocess.run(
        [sys.executable, str(project / 'legible' / 'build.py'),
         '--out', str(out), '--minify', 'true' if minify else 'false', '--no-validate'],
        capture_output=True, text=True, env=env, cwd=project)


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
        'service': SERVICE,
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
        <a href="{SERVICE}">related service</a>.</p>
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
        # Regression: `<strong>x</strong> <small>y</small>` came out glued ("xy"). It happened on /pricing/.
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
        service = self.pages / 'services' / SERVICE_SLUG
        service.mkdir(parents=True)
        (service / 'index.html').write_text('---\ntitle: S\ndescription: S\n---\n<main></main>', encoding='utf-8')

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
        self.add('guides', 'a', service='/services/does-not-exist/')
        self.assertIn('service "/services/does-not-exist/" does not point to an existing page', self.problems())

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
        for route in ('index.html', 'pricing/index.html', 'robots.txt', 'llms.txt', 'sitemap.xml'):
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
        page = self.project / 'src' / 'pages' / 'about' / 'index.html'
        page.write_text(page.read_text(encoding='utf-8').replace('<h1', '<p>{{made_up_marker}}</p>\n<h1', 1),
                          encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('{{made_up_marker}}', r.stderr + r.stdout)
        self.assertIn('texts.json', r.stderr + r.stdout)
        self.assertIn('/about/', r.stderr + r.stdout, 'must say which page it is on')
        self.assertNotIn('Traceback', r.stderr)

    def test_marker_resolved_from_texts_json(self):
        page = self.project / 'src' / 'pages' / 'about' / 'index.html'
        page.write_text(page.read_text(encoding='utf-8').replace('<h1', '<p>{{my_marker}}</p>\n<h1', 1),
                          encoding='utf-8')
        texts = self.project / 'src' / 'data' / 'texts.json'
        data = json.loads(texts.read_text(encoding='utf-8'))
        data['my_marker'] = 'Text added from texts.json'
        texts.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        self.build_ok()
        self.assertIn('Text added from texts.json',
                      (self.out / 'about' / 'index.html').read_text(encoding='utf-8'))

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
        svc = self.project / 'src' / 'pages' / 'services' / 'index.html'
        svc.write_text(svc.read_text(encoding='utf-8').replace(
            '<a href="/pricing/">', '<a href="/path-that-does-not-exist-with-a-fairly-long-name/">', 1), encoding='utf-8')
        pr = self.project / 'src' / 'pages' / 'pricing' / 'index.html'
        import re
        pr.write_text(re.sub(r'^description:.*$', 'description: Short.', pr.read_text(encoding='utf-8'), count=1, flags=re.M),
                      encoding='utf-8')

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
        page = self.project / 'src' / 'pages' / 'about' / 'index.html'
        text = page.read_text(encoding='utf-8')
        self.assertEqual(text.count('"@graph": ['), 1)
        page.write_text(text.replace(
            '"@graph": [', '"@graph": [{"@type": "ProfessionalService", "@id": "{{site_url}}/#business", "name": "Duplicate"},', 1),
            encoding='utf-8')
        r = run_build(self.project, self.out)
        self.assertNotEqual(r.returncode, 0, 'a duplicate @id must fail the build')
        self.assertIn('BUILD FAILED', r.stderr)
        self.assertIn('duplicate JSON-LD @id', r.stderr)
        self.assertIn('/#business', r.stderr)
        self.assertIn('/about/', r.stderr)
        self.assertNotIn('Traceback', r.stderr)

    def test_slug_containing_index_html_keeps_its_url(self):
        """The page URL drops only the final index.html: a folder named my-index.html-guide must not become my--guide."""
        slug = 'my-index.html-guide'
        page = self.project / 'src' / 'pages' / slug / 'index.html'
        page.parent.mkdir(parents=True)
        page.write_text((self.project / 'src' / 'pages' / 'about' / 'index.html').read_text(encoding='utf-8'),
                        encoding='utf-8')
        self.build_ok()
        text = (self.out / slug / 'index.html').read_text(encoding='utf-8')
        self.assertIn(f'/{slug}/', text)
        self.assertRegex(text, r'rel="canonical" href="https://[^"]+/' + slug + '/"')
        self.assertRegex(text, r'property="og:url" content="https://[^"]+/' + slug + '/"')
        self.assertNotIn('my--guide', text)

    def test_internal_http_link_is_an_error(self):
        self.build_ok()
        f = self.out / 'pricing' / 'index.html'
        f.write_text(f.read_text(encoding='utf-8').replace(
            '</main>', '<p><a href="http://YOUR-DOMAIN.com/contact/">c</a></p></main>', 1), encoding='utf-8')
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


if __name__ == '__main__':
    unittest.main()
