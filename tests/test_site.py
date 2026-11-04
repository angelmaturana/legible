#!/usr/bin/env python3
"""Tests of the template that ships in `src/` (the ones that read it) and of the command line.

    python3 -B -m unittest discover tests

Each test works on a temporary copy of `src/`, so nothing in the project changes. The rest (the command line
tests of the old suite) are here since F10C.
"""
import contextlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
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

LEGIBLE = REPO / 'legible'
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


def stylesheet(root):
    """`site.css` of a project copy, without comments."""
    css = (Path(root) / 'src' / 'css' / 'site.css').read_text(encoding='utf-8')
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def root_block(css):
    return re.search(r':root\s*\{(.*?)\n\}', css, re.S).group(1)


def relative_luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    high, low = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def rules(css):
    """(selectors, declarations) of every rule, also the ones inside @media."""
    for head, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        yield [x.strip() for x in head.split(',')], body


class TemplateCopy(unittest.TestCase):
    """A copy of src/ (and of legible/, when a command is run) in a temporary folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        shutil.copytree(REPO / 'src', self.root / 'src')

    def site(self, **changes):
        path = self.root / 'src' / 'data' / 'site.json'
        config = {**json.loads(path.read_text(encoding='utf-8')), **changes}
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def build(self, validate=True):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ok = build.build(self.root, no_validate=not validate)
        return ok, out.getvalue()

    def dist(self, rel):
        return (self.root / 'dist' / rel).read_text(encoding='utf-8')

    def strict_checks(self):
        errors, warnings = check_site.run_checks(self.root / 'dist', build.load_site(self.root).site_url)
        return errors + warnings


class TestTemplateContactIsOptional(TemplateCopy):
    """Phone and WhatsApp are optional. The email is too, except where the template's legal pages print it
    (decision 6): without it the build stops and names the page. The cases with an email pass strict mode."""

    CASES = {
        'both': {},
        'email only': {'phone_e164': ''},
    }
    NO_EMAIL = {
        'phone only': {'contact_email': ''},
        'none': {'contact_email': '', 'phone_e164': ''},
    }
    LEGAL_PAGES = ('privacy-policy', 'legal-notice')

    def without_legal_pages(self):
        """The template minus the pages that print the email: what a site with no email would write."""
        for slug in self.LEGAL_PAGES:
            shutil.rmtree(self.root / 'src' / 'pages' / slug)

    def test_every_case_with_an_email_builds_and_validates_in_strict_mode(self):
        for name, changes in self.CASES.items():
            with self.subTest(case=name):
                self.site(**changes)
                ok, stdout = self.build()
                self.assertTrue(ok, stdout)
                self.assertEqual(self.strict_checks(), [])

    def test_without_an_email_the_legal_pages_stop_the_build_and_name_the_page_and_the_fix(self):
        for name, changes in self.NO_EMAIL.items():
            with self.subTest(case=name):
                self.site(**changes)
                with self.assertRaises(build.BuildError) as ctx:
                    self.build()
                for expected in ('{{contact_email}}', 'contact_email', 'site.json'):
                    self.assertIn(expected, str(ctx.exception))
                self.assertTrue(any(f'/{slug}/' in str(ctx.exception) for slug in self.LEGAL_PAGES))

    def test_the_pages_only_have_the_channels_that_exist(self):
        pages = lambda: '\n'.join(p.read_text(encoding='utf-8') for p in (self.root / 'dist').rglob('*.html'))
        self.site(phone_e164='')
        self.build()
        for forbidden in ('wa.me', 'whatsapp-float', 'tel:'):
            self.assertNotIn(forbidden, pages())
        self.without_legal_pages()
        self.site(contact_email='', phone_e164='+34600111222')
        self.build(validate=False)
        self.assertIn('wa.me/34600111222', pages())
        self.assertNotIn('mailto:', self.dist('contact/index.html'))
        self.site(contact_email='', phone_e164='')
        self.build(validate=False)
        self.assertIn(build.UI['en']['contact_empty'], self.dist('contact/index.html'))
        self.assertNotIn('wa.me', pages())

    def test_the_template_has_no_hand_written_contact_links(self):
        for path in [self.root / 'src' / 'layout.html', *(self.root / 'src' / 'partials').rglob('*'),
                     *(self.root / 'src' / 'pages').rglob('*.html'), *(self.root / 'src' / 'static').rglob('*.txt')]:
            if path.is_file():
                text = path.read_text(encoding='utf-8')
                for forbidden in ('wa.me', 'whatsapp-float', 'mailto:'):
                    self.assertNotIn(forbidden, text, f'{path.relative_to(self.root)}: {forbidden}')


class TestTemplateOgImage(TemplateCopy):
    def test_the_published_size_is_the_one_of_the_png(self):
        header = (self.root / 'src' / 'static' / 'images' / 'og-image.png').read_bytes()[:24]
        width, height = struct.unpack('>II', header[16:24])
        ok, stdout = self.build()
        self.assertTrue(ok, stdout)
        home = self.dist('index.html')
        self.assertEqual(re.search(r'og:image:width" content="(\d+)"', home).group(1), str(width))
        self.assertEqual(re.search(r'og:image:height" content="(\d+)"', home).group(1), str(height))

    def test_the_template_image_is_a_good_size(self):
        self.assertEqual(self.build()[0], True)
        self.assertEqual([w for w in self.strict_checks() if 'og:image' in str(w)], [])


class TestSampleValues(unittest.TestCase):
    def test_the_table_matches_the_site_json_that_ships(self):
        config = json.loads((REPO / 'src' / 'data' / 'site.json').read_text(encoding='utf-8'))
        for key, sample in check_site.SAMPLE_VALUES.items():
            with self.subTest(key=key):
                self.assertEqual(config.get(key), sample)


class TestPrelaunchCommand(TemplateCopy):
    """`check_site.py --prelaunch` through the command line: fails with the base, passes with real data."""

    def setUp(self):
        super().setUp()
        shutil.copytree(REPO / 'legible', self.root / 'legible', ignore=shutil.ignore_patterns('__pycache__'))

    def run_py(self, *args):
        env = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
        return subprocess.run([sys.executable, '-B', *args], cwd=self.root, capture_output=True, text=True, env=env)

    def test_the_base_fails_and_names_its_keys_and_a_copy_with_real_data_passes(self):
        self.assertEqual(self.run_py('legible/build.py').returncode, 0)
        result = self.run_py('legible/check_site.py', '--prelaunch')
        self.assertEqual(result.returncode, 1, result.stdout)
        for key in ('site_url', 'site_name', 'contact_email', 'legal_name'):
            self.assertIn(f'"{key}"', result.stdout)
        self.assertIn('SAMPLE COPY', result.stdout)
        real = {key: f'Real {key}' for key in check_site.SAMPLE_VALUES}
        real.update(site_url='https://real.test', contact_email='real@real.test', phone_e164='+34600111222',
                    country_code='ES')
        self.site(**real)
        for page in (self.root / 'src' / 'pages').rglob('*.html'):
            text = page.read_text(encoding='utf-8')
            page.write_text(re.sub(r'\s*<!-- SAMPLE COPY[^>]*-->', '', text), encoding='utf-8')
        self.assertEqual(self.run_py('legible/build.py').returncode, 0)
        result = self.run_py('legible/check_site.py', '--prelaunch')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('Ready to publish', result.stdout)


class TestTemplateStylesheet(TemplateCopy):
    """`site.css` carries only what the template uses: no dead classes, no dead or undefined tokens."""

    def setUp(self):
        super().setUp()
        self.css = stylesheet(self.root)

    def classes_in_css(self):
        selectors = ' '.join(re.findall(r'([^{}]+)\{', re.sub(r'"[^"]*"', '', self.css)))
        return set(re.findall(r'\.([A-Za-z_][\w-]*)', selectors))

    def classes_in_use(self):
        used = set()
        for page in (self.root / 'src').rglob('*.html'):
            for value in re.findall(r'class="([^"]*)"', page.read_text(encoding='utf-8')):
                used.update(value.split())
        # The engine writes some classes itself (menu, contact buttons, floating WhatsApp button).
        engine = (REPO / 'legible' / 'build.py').read_text(encoding='utf-8')
        for value in re.findall(r'class=\\?"([^"\\{]*)', engine):
            used.update(value.split())
        used.update(re.findall(r'"([a-z][\w-]*)"', engine))
        return used

    def test_every_class_of_the_stylesheet_is_used_by_a_page_or_by_the_engine(self):
        dead = sorted(self.classes_in_css() - self.classes_in_use())
        self.assertEqual(dead, [], 'classes in site.css that nothing uses: %s' % ', '.join(dead))

    def tokens(self):
        root = re.search(r':root\s*\{(.*?)\n\}', self.css, re.S).group(1)
        return set(re.findall(r'(--[\w-]+)\s*:', root)), self.css.replace(root, '')

    def test_every_token_is_used_and_every_use_is_defined(self):
        defined, rest = self.tokens()
        used = set(re.findall(r'var\((--[\w-]+)', rest))
        self.assertEqual(sorted(defined - used), [], 'tokens that nothing uses')
        self.assertEqual(sorted(used - defined), [], 'tokens used but not defined')

    def test_the_old_token_names_are_gone(self):
        defined, rest = self.tokens()
        old = {'--ink', '--soft', '--muted', '--accent-ink', '--blue', '--blue-2', '--glow-teal', '--glow-amber',
               '--s1', '--s2', '--s3', '--term', '--deep', '--deep-line', '--line-2', '--green', '--amber',
               '--font-mono'}
        self.assertEqual(sorted(old & (defined | set(re.findall(r'var\((--[\w-]+)', rest)))), [])


class TestStylesheetAccessibility(TemplateCopy):
    """Colour, contrast, motion, focus and touch targets of `site.css`, read from the file itself.

    Every check is derived from the tokens in `:root`, so a different palette (a light theme, for example) that
    only changes `:root` keeps passing as long as it stays readable.
    """

    # (text token, background token, minimum ratio): WCAG 2.x AA for text (4.5) and for borders of controls (3).
    CONTRAST = (('text', 'bg', 4.5), ('text-muted', 'bg', 4.5), ('text-muted', 'surface-2', 4.5),
                ('accent', 'bg', 4.5), ('accent-text', 'accent', 4.5), ('edge', 'bg', 3.0),
                # Pairs the stylesheet really uses: eyebrow, footer titles and the ">" prompt, lead text,
                # menu links (header and submenu panel) and the hover state of the primary button / filled links.
                ('info-soft', 'bg', 4.5), ('warn', 'bg', 4.5), ('success', 'bg', 4.5),
                ('text-soft', 'bg', 4.5), ('text-soft', 'bg-header', 4.5), ('text-soft', 'bg-alt', 4.5),
                ('accent-text', 'accent-hi', 4.5))

    def setUp(self):
        super().setUp()
        self.css = stylesheet(self.root)
        self.root_css = root_block(self.css)
        self.outside_root = self.css.replace(self.root_css, '')

    def token(self, name):
        value = re.search(r'--%s:\s*([^;]+);' % re.escape(name), self.root_css)
        self.assertIsNotNone(value, 'the token --%s is not defined in :root' % name)
        return value.group(1).strip()

    def test_text_and_borders_have_enough_contrast(self):
        for fg, bg, minimum in self.CONTRAST:
            for name in (fg, bg):
                self.assertRegex(self.token(name), r'^#[0-9A-Fa-f]{6}$',
                                 '--%s is not #RRGGBB, so its contrast cannot be checked: write it as #RRGGBB '
                                 'or extend this test' % name)
            ratio = contrast_ratio(self.token(fg), self.token(bg))
            self.assertGreaterEqual(ratio, minimum, '--%s on --%s is %.2f:1 (needs %.1f)' % (fg, bg, ratio, minimum))

    def test_theme_color_is_the_background_token(self):
        bg = self.token('bg').lower()
        config = json.loads((self.root / 'src' / 'data' / 'site.json').read_text(encoding='utf-8'))
        self.assertEqual(config['theme_color'].lower(), bg)
        self.assertTrue(self.build()[0])
        self.assertIn('<meta name="theme-color" content="%s">' % config['theme_color'], self.dist('index.html'))

    def test_color_scheme_matches_the_palette(self):
        found = re.search(r'(?<![\w-])color-scheme:\s*([^;]+);', self.root_css)
        declared = found.group(1).strip() if found else None
        expected = 'dark' if relative_luminance(self.token('bg')) < 0.18 else 'light'
        self.assertEqual(declared, expected, 'color-scheme must say whether --bg is a dark or a light colour')
        layout = (self.root / 'src' / 'layout.html').read_text(encoding='utf-8')
        self.assertIn('<meta name="color-scheme" content="%s">' % expected, layout,
                      'the color-scheme meta of layout.html must say the same as :root')

    def test_no_colour_is_written_outside_root(self):
        found = re.findall(r'#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(',
                           self.outside_root)
        self.assertEqual(found, [], 'colours outside :root (use a token): %s' % ', '.join(found))

    def test_there_is_no_motion(self):
        found = re.findall(r'\b(transition[\w-]*|animation[\w-]*|@keyframes|scroll-behavior|will-change)\b', self.css)
        self.assertEqual(found, [], 'the stylesheet promises no motion: %s' % ', '.join(found))

    def test_keyboard_focus_is_visible_and_never_removed(self):
        self.assertRegex(self.css, r'(^|\n):focus-visible\s*\{[^}]*outline:\s*\d+px solid var\(--accent\)')
        self.assertEqual(re.findall(r'outline(?:-style)?\s*:\s*(?:none|0)\b', self.css), [],
                         'an outline is removed: keyboard users lose the focus ring')

    def declared(self, selector, prop):
        """Every `prop` value (in px) declared for exactly `selector`, in any rule or media query."""
        values = []
        for selectors, body in rules(self.css):
            if selector in selectors:
                values += [int(v) for v in re.findall(r'(?<![\w-])%s:\s*(\d+)px' % prop, body)]
        return values

    def test_touch_targets_are_at_least_44_px(self):
        for selector in ('.nav-link', '.nav-sublink', '.footer-nav a', '.footer-contact-item',
                         '.footer-logo', '.breadcrumb a', '.button'):
            values = self.declared(selector, 'min-height')
            self.assertTrue(values, '%s declares no min-height' % selector)
            self.assertGreaterEqual(min(values), 44, '%s has a target of %d px' % (selector, min(values)))
        for prop in ('width', 'height'):
            self.assertEqual(self.declared('.nav-toggle-label', prop), [44], 'the menu button must be 44 px')

    BREAKPOINTS = {640, 768, 960, 1100}

    def test_media_queries_use_only_the_documented_breakpoints(self):
        """Custom properties do not work in @media, so the four widths of the header comment are the whole set."""
        found = {int(v) for v in re.findall(r'@media\s*\((?:min|max)-width:\s*(\d+)px\)', self.css)}
        self.assertEqual(sorted(found - self.BREAKPOINTS), [],
                         'breakpoints outside %s: add the value to the header comment and to this test, or reuse one'
                         % sorted(self.BREAKPOINTS))

    def test_header_offsets_derive_from_the_header_height_token(self):
        self.assertRegex(self.token('header-h'), r'^\d+px$')
        derived = self.outside_root
        self.assertRegex(derived, r'\.site-header \.page-width\s*\{[^}]*min-height:\s*var\(--header-h\)')
        self.assertRegex(derived, r'\[id\]\s*\{[^}]*scroll-margin-top:\s*calc\(var\(--header-h\)')
        self.assertRegex(derived, r'max-height:\s*calc\(100dvh - var\(--header-h\)\)')
        self.assertEqual(re.findall(r'\b(?:min-height|scroll-margin-top):\s*1[0-9]{2}px', derived), [],
                         'a header-sized number is written by hand: use --header-h')

    def test_the_mobile_menu_scrolls_on_its_own(self):
        panel = [body for selectors, body in rules(self.css) if selectors == ['.site-nav']][0]
        self.assertIn('overflow-y: auto', panel)
        self.assertIn('max-height: calc(100dvh', panel)
        self.assertIn('overscroll-behavior: contain', panel)

    def test_the_logo_proportion_is_one_token_used_by_header_and_footer(self):
        width, height = [float(x) for x in re.split(r'\s*/\s*', self.token('logo-ratio'))]
        self.assertEqual(self.outside_root.count('var(--logo-ratio)'), 2)
        self.assertNotRegex(self.outside_root, r'aspect-ratio:\s*\d')
        for part in ('header', 'footer'):
            html = (self.root / 'src' / 'partials' / (part + '.html')).read_text(encoding='utf-8')
            img = re.search(r'<img[^>]*logo\.svg[^>]*>', html).group(0)
            w, h = [float(re.search(r'%s="(\d+)"' % a, img).group(1)) for a in ('width', 'height')]
            self.assertAlmostEqual((w / h) / (width / height), 1, delta=0.02,
                                   msg='the %s logo declares %sx%s, not the proportion of the token' % (part, w, h))

    def test_home_and_example_use_the_same_card_component(self):
        for page in ('index.html', 'example/index.html'):
            html = (self.root / 'src' / 'pages' / page).read_text(encoding='utf-8')
            grid = re.search(r'<div class="card-grid">(.*?)</div>', html, re.S)
            self.assertIsNotNone(grid, '%s has no .card-grid' % page)
            cards, headings = grid.group(1).count('class="card"'), grid.group(1).count('<h3>')
            self.assertGreaterEqual(cards, 3)
            self.assertEqual(cards, headings, '%s: every item of the grid must be a .card with its own heading' % page)

    def test_the_menu_button_stays_visible_in_forced_colors_mode(self):
        """Windows high contrast overrides `background`, so the three bars must be painted with a system colour."""
        block = re.search(r'@media\s*\(forced-colors:\s*active\)\s*\{(.*?)\n\}', self.css, re.S)
        self.assertIsNotNone(block, 'site.css has no @media (forced-colors: active) rule: the menu button would vanish')
        inner = [(selectors, body) for selectors, body in rules(block.group(1))]
        self.assertEqual(len(inner), 1, 'the forced-colors block must hold exactly one rule')
        selectors, body = inner[0]
        self.assertEqual(sorted(selectors),
                         sorted(['.nav-toggle-label span', '.nav-toggle-label::before', '.nav-toggle-label::after']),
                         'the rule must cover the three bars of the menu button')
        self.assertRegex(body, r'background(-color)?:\s*CanvasText\s*;?')
        self.assertNotRegex(body, r'#[0-9A-Fa-f]{3,8}\b', 'a system colour needs no hexadecimal value')




class TestSmoke(TemplateCopy):
    """Build the template as it ships and require a clean validator run (errors and warnings)."""

    def build_to(self, minify):
        out = self.root / 'output'
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            ok = build.build(self.root, out_dir=out, minify=minify, no_validate=True)
        self.assertTrue(ok, stdout.getvalue())
        return out

    def _build_and_validate(self, minify):
        out = self.build_to(minify)
        problems = check_site.run_checks(out, build.load_site(self.root).site_url)
        self.assertEqual([x for part in problems for x in part], [], 'the validator should pass in strict mode')
        self.assertTrue((out / 'index.html').is_file())
        self.assertTrue((out / 'sitemap.xml').is_file())

    def test_template_minified(self):
        self._build_and_validate(minify=True)

    def test_template_unminified(self):
        self._build_and_validate(minify=False)

    def test_check_site_detects_an_error(self):
        """The smoke test only counts if the validator really fails when something is wrong."""
        out = self.build_to(True)
        index = out / 'index.html'
        index.write_text(index.read_text(encoding='utf-8').replace('<h1', '<h2').replace('</h1>', '</h2>'), encoding='utf-8')
        errors, _ = check_site.run_checks(out, build.load_site(self.root).site_url)
        self.assertTrue(errors)

    def test_whatsapp_links_well_formed(self):
        """Regression: duplicated "?text=" and unencoded spaces in wa.me links."""
        out = self.build_to(True)
        links = [h for f in out.rglob('*.html')
                 for h in re.findall(r'href="(https://wa\.me/[^"]*)"', f.read_text(encoding='utf-8'))]
        self.assertTrue(links, 'the template should have WhatsApp links')
        for h in links:
            self.assertEqual(h.count('?'), 1, f'repeated "?" in {h}')
            self.assertNotIn(' ', h, f'unencoded spaces in {h}')

    def test_no_validate_with_out_does_not_touch_the_projects_dist(self):
        self.build_to(True)
        self.assertFalse((self.root / 'dist').exists())


class TestNoDomainInTheSources(unittest.TestCase):
    def test_no_source_page_has_the_sample_domain_hardcoded(self):
        """Regression: in src/ only {{site_url}} (or {{page_url}}) is allowed; site.json holds the one value."""
        for f in (REPO / 'src').rglob('*'):
            if f.is_file() and f.suffix in ('.html', '.json', '.txt', '.css') and f.name != 'site.json':
                self.assertNotIn('YOUR-DOMAIN', f.read_text(encoding='utf-8'), f.relative_to(REPO).as_posix())


class TestTemplateMainType(TemplateCopy):
    """The template builds and passes the strict validator with the first type of every class of the business
    table (the list lives in `fixtures.MAIN_TYPES`, not in the documentation) and with a list of types."""

    def build_with_type(self, new_type):
        path = self.root / 'src' / 'data' / 'entity.json'
        nodes = json.loads(path.read_text(encoding='utf-8'))
        next(n for n in nodes if str(n.get('@id', '')).endswith('/#business'))['@type'] = new_type
        path.write_text(json.dumps(nodes, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        ok, out = self.build()
        self.assertTrue(ok, out)
        self.assertEqual(self.strict_checks(), [])

    def test_the_first_type_of_every_class_builds_and_passes_the_strict_validator(self):
        for new_type in fixtures.MAIN_TYPES:
            with self.subTest(type=new_type):
                self.build_with_type(new_type)

    def test_a_list_of_types_builds_and_passes_the_strict_validator(self):
        self.build_with_type(['VeterinaryCare', 'LocalBusiness'])


class TestTemplateInSpanish(TemplateCopy):
    """`language: es` on the template, end to end (the old TestLanguageRegression case that no in-process test
    had): it builds, passes the strict validator and publishes the lang and og:locale of Spanish."""

    def test_the_template_builds_and_passes_the_strict_validator_in_spanish(self):
        self.site(language='es')
        ok, out = self.build()
        self.assertTrue(ok, out)
        self.assertEqual(self.strict_checks(), [])
        home = self.dist('index.html')
        self.assertIn('<html lang="es"', home)
        self.assertIn('content="es_ES"', home)


class TestSamplePagesHaveUpdated(unittest.TestCase):
    """The sitemap takes the lastmod of every page from `updated`: the template's pages all carry it."""

    def test_every_sample_page_has_updated(self):
        pages = sorted(f for f in (REPO / 'src' / 'pages').rglob('*.html') if f.name != '404.html')  # the 404 is not in the sitemap
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.relative_to(REPO).as_posix()):
                front, _ = build.parse_front_matter(page.read_text(encoding='utf-8'))
                self.assertIn('updated', front)


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

    def test_build_script_warns_when_example_data_is_left(self):
        """Forgetting the real data must not pass silently, but it must not stop the build either (F8B: the
        notice of `build.py --all` replaces the old warning about the sample domain)."""
        r = self._run_build_script()
        self.assertEqual(r.returncode, 0, f'{r.stdout}\n{r.stderr}')
        self.assertIn('WARNING', r.stderr)
        self.assertIn('check_site.py --prelaunch', r.stderr)
        self.assertIn('BUILD SUCCESS', r.stdout)

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


def _agents_text():
    return (REPO / 'AGENTS.md').read_text(encoding='utf-8')


class TestAgentsGuards(unittest.TestCase):
    """AGENTS.md is the prompt an AI reads first. Three static guards keep it short, keep the commands the user
    types and keep the rules that protect the user. They check stable fragments, not whole paragraphs."""

    COMMANDS = ('legible start', 'legible continue', 'legible help')

    def test_agents_exists_and_stays_within_150_lines(self):
        lines = _agents_text().splitlines()
        self.assertGreater(len(lines), 0)
        self.assertLessEqual(len(lines), 150, 'AGENTS.md is a prompt: keep it at 150 lines or fewer')

    def test_each_command_is_in_agents_and_in_the_readme(self):
        agents = _agents_text()
        readme = (REPO / 'README.md').read_text(encoding='utf-8')
        for command in self.COMMANDS:
            self.assertIn(f'`{command}`', agents, f'AGENTS.md does not list `{command}`')
            self.assertIn(f'`{command}`', readme, f'README.md does not list `{command}`')

    def test_the_rules_that_protect_the_user_are_kept(self):
        agents = _agents_text()
        for fragment in ('<!-- SAMPLE COPY -->', 'not legal advice', 'Never invent facts',
                         'legible/build.py --all', 'check_site.py --prelaunch', 'ONE question'):
            self.assertIn(fragment, agents, f'AGENTS.md lost: {fragment}')


if __name__ == '__main__':
    unittest.main()
