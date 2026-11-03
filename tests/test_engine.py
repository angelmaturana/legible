#!/usr/bin/env python3
"""Engine tests (in process, standard library only): shared code, errors, the Site object and file I/O.

    python3 -B -m unittest discover tests

They use the fixture of `fixtures.py`, not the template in `src/` (the one exception is the smoke test of
the LF output). The rest of the engine tests migrate here in F10A-F10C.
"""
import ast
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
from html import escape as html_escape
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
LEGIBLE = REPO / 'legible'

os.environ.pop('SITE_URL', None)  # the caller's environment must not leak into the tests
sys.dont_write_bytecode = True  # tests must not leave legible/__pycache__/
sys.path.insert(0, str(LEGIBLE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_site  # noqa: E402
import common  # noqa: E402
import fixtures  # noqa: E402
import minify  # noqa: E402

REMOVED_GLOBALS = ('SITE_CONFIG', 'SITE_URL', 'LANGUAGE', 'LANG', 'OG_LOCALE', 'IN_LANGUAGE', 'LOCALE', 'REPO',
                   '_SAMPLE_WATCH', '_SAMPLE_HITS', '_STARTUP_ERROR', 'SAMPLE_OFFERS')


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


def env_without_site_url():
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != 'SITE_URL'}, clear=True)


class Project(unittest.TestCase):
    """Base class: a fresh fixture project in `self.root`."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        fixtures.make_project(self.root)
        self.enterContext(env_without_site_url())

    def run_build(self, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        kwargs.setdefault('no_validate', True)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ok = build.build(self.root, **kwargs)
        return ok, out.getvalue(), err.getvalue()


class TestNoGlobalState(unittest.TestCase):
    def test_the_old_globals_are_gone(self):
        for name in REMOVED_GLOBALS:
            self.assertFalse(hasattr(build, name), f'build.{name} must not exist: the Site object replaces it')

    def test_importing_the_engine_does_not_need_a_project(self):
        """The engine imports from a folder that is not a project; check_site does not import build."""
        self.assertTrue(callable(build.load_site))
        self.assertNotIn('build', vars(check_site))


class TestLoadSite(Project):
    def test_fields(self):
        site = build.load_site(self.root)
        self.assertEqual(site.root, self.root)
        self.assertEqual(site.site_url, 'https://fixture.test')
        self.assertEqual((site.language, site.lang, site.og_locale, site.in_language),
                         ('en', 'en', 'en_US', 'en-US'))
        self.assertEqual(site.business['@type'], 'Organization')
        self.assertEqual(site.ui, build.UI['en'])

    def test_spanish(self):
        fixtures.make_project(self.root, site={'language': 'es'})
        site = build.load_site(self.root)
        self.assertEqual((site.lang, site.og_locale, site.in_language), ('es', 'es_ES', 'es-ES'))

    def test_the_url_override_wins_over_site_json_and_environment(self):
        with mock.patch.dict(os.environ, {'SITE_URL': 'https://env.test'}):
            self.assertEqual(build.load_site(self.root).site_url, 'https://env.test')
            self.assertEqual(build.load_site(self.root, 'https://cli.test/').site_url, 'https://cli.test')

    def test_ui_overrides_reach_the_site(self):
        fixtures.make_project(self.root, site={'ui': {'home': 'Start'}})
        self.assertEqual(build.load_site(self.root).ui['home'], 'Start')
        self.assertEqual(build.UI['en']['home'], 'Home')

    def test_two_sites_do_not_share_state(self):
        first, second = build.load_site(self.root), build.load_site(self.root)
        first.nav_markers['{{x}}'] = 'changed'
        first.config['site_name'] = 'changed'
        self.assertNotIn('{{x}}', second.nav_markers)
        self.assertEqual(second.config['site_name'], 'Fixture Site')


class TestClearErrors(Project):
    def error(self, **project):
        fixtures.make_project(self.root, **project)
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(self.root)
        return str(ctx.exception)

    def test_unsupported_language(self):
        message = self.error(site={'language': 'fr'})
        self.assertIn("unsupported language 'fr'", message)
        self.assertIn('supported: en, es', message)

    def test_unreadable_site_json(self):
        self.assertIn('could not read src/data/site.json', self.error(site='{ not json'))

    def test_site_json_that_is_not_an_object(self):
        self.assertIn('must contain a JSON object', self.error(site='[1, 2]'))

    def test_invalid_url(self):
        self.assertIn('SITE_URL must start with https://', self.error(site={'site_url': 'http://fixture.test'}))

    def test_first_problem_wins(self):
        self.assertIn('SITE_URL must start with https://', self.error(site={'site_url': 'nope', 'language': 'fr'}))

    def test_bad_ui_override(self):
        message = self.error(site={'ui': {'hom': 'x'}})
        self.assertIn('src/data/site.json › ui', message)
        self.assertIn('"hom"', message)

    def test_unreadable_entity(self):
        self.assertIn('could not read src/data/entity.json', self.error(entity='[ not json'))

    def test_entity_without_a_main_node(self):
        self.assertIn('no main node', self.error(entity=[{'@type': 'Thing', '@id': 'x'}]))

    def test_a_folder_that_is_not_a_project(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(common.BuildError):
            build.load_site(tmp)  # no site.json: SITE_URL is empty


class TestBuildWithTheFixture(Project):
    def test_builds_a_project_that_is_not_the_repository(self):
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok)
        self.assertIn('Site ready for deployment', stdout)
        dist = self.root / 'dist'
        self.assertEqual(sorted(p.relative_to(dist).as_posix() for p in dist.rglob('*') if p.is_file()),
                         ['404.html', 'css/site.css', 'index.html', 'robots.txt', 'sitemap.xml'])
        home = (dist / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<h1>Fixture Site</h1>', home)
        self.assertIn('href="https://fixture.test/"', home)
        self.assertIn('<loc>https://fixture.test/</loc>', (dist / 'sitemap.xml').read_text(encoding='utf-8'))
        self.assertIn('Sitemap: https://fixture.test/sitemap.xml', (dist / 'robots.txt').read_text(encoding='utf-8'))

    def test_out_dir_and_minify(self):
        out = self.root / 'elsewhere'
        ok, _, _ = self.run_build(out_dir=out, minify=True)
        self.assertTrue(ok)
        self.assertTrue((out / 'index.html').exists())
        self.assertFalse((self.root / 'dist').exists())

    def test_the_url_override_reaches_the_pages(self):
        self.run_build(site_url_override='https://other.test')
        self.assertIn('https://other.test/', (self.root / 'dist' / 'index.html').read_text(encoding='utf-8'))

    def test_a_page_without_title_fails_the_build(self):
        fixtures.write(self.root, 'src/pages/broken/index.html', '---\ndescription: only a description\n---\n<main id="main"></main>\n')
        ok, stdout, _ = self.run_build()
        self.assertFalse(ok)
        self.assertIn('missing title or description', stdout)

    def test_builds_do_not_leak_into_each_other(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        fixtures.make_project(other.name, site={'site_url': 'https://second.test', 'site_name': 'Second Site',
                                                'contact_email': 'hi@second.test'})
        self.run_build()
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(other.name, no_validate=True)
        self.assertIn('Fixture Site', (self.root / 'dist' / 'index.html').read_text(encoding='utf-8'))
        second = (Path(other.name) / 'dist' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Second Site', second)
        self.assertNotIn('fixture.test', second)

    def test_the_output_folder_cannot_be_the_project(self):
        with self.assertRaises(common.BuildError) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                build.build(self.root, out_dir=self.root / 'src', no_validate=True)
        self.assertEqual(ctx.exception.label, 'BUILD ABORTED')
        self.assertTrue((self.root / 'src' / 'layout.html').exists())

class TestNav(Project):
    """`nav` and `legal_nav` of site.json generate {{nav}}, {{footer_nav}} and {{legal_nav}}."""

    def built(self, rel='index.html'):
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / rel).read_text(encoding='utf-8')

    def nav_error(self, key='nav', value=None):
        fixtures.make_project(self.root, site={key: value})
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(self.root)
        return str(ctx.exception)

    def test_main_menu_with_submenu_and_action(self):
        home = self.built()
        self.assertIn('<li class="has-sub"><a href="/company/">Company</a><ul><li><a href="/company/team/">Team</a></li></ul></li>', home)
        self.assertIn('<li><a class="nav-action" href="/talk/">Talk to us</a></li>', home)
        self.assertIn('<nav aria-label="Main navigation"><ul>', home)

    def test_footer_menu_flattens_the_submenus(self):
        home = self.built()
        self.assertIn('<nav aria-label="Site"><ul><li><a href="/">Home</a></li><li><a href="/company/">Company</a></li>'
                      '<li><a href="/company/team/">Team</a></li><li><a href="/talk/">Talk to us</a></li></ul></nav>', home)

    def test_legal_menu(self):
        self.assertIn('<nav aria-label="Legal"><ul><li><a href="/legal/">Legal notice</a></li></ul></nav>', self.built())

    def test_no_nav_in_site_json_gives_empty_lists(self):
        fixtures.make_project(self.root, site={'nav': [], 'legal_nav': None})
        self.assertIn('<nav aria-label="Legal"><ul></ul></nav>', self.built())

    def test_labels_are_escaped(self):
        fixtures.make_project(self.root, site={'nav': [{'label': 'Q&A <b>"now"</b>', 'url': '/qa/'}]})
        home = self.built()
        self.assertIn('>Q&amp;A &lt;b&gt;"now"&lt;/b&gt;</a>', home)
        self.assertNotIn('<b>', home)

    def test_the_active_entry_follows_the_slug_of_the_page(self):
        fixtures.write(self.root, 'src/pages/company/index.html', fixtures.page('Company page for the fixture'))
        fixtures.write(self.root, 'src/pages/company/team/index.html', fixtures.page('Team page for the fixture'))
        fixtures.write(self.root, 'src/pages/other/index.html', fixtures.page('Other page for the fixture'))
        self.assertIn('<a href="/company/" class="active" aria-current="page">Company</a>', self.built('company/index.html'))
        self.assertIn('<a href="/company/team/" class="active" aria-current="page">Team</a>', self.built('company/team/index.html'))
        other = self.built('other/index.html')
        self.assertNotIn('class="active"', other)
        self.assertIn('<a href="/" class="active" aria-current="page">Home</a>', self.built())

    def test_a_page_below_an_entry_highlights_the_entry(self):
        fixtures.write(self.root, 'src/pages/talk/deeper/index.html', fixtures.page('Deeper page for the fixture'))
        page = self.built('talk/deeper/index.html')
        self.assertIn('<a class="nav-action active" href="/talk/" aria-current="true">Talk to us</a>', page)

    def test_errors_name_the_entry(self):
        cases = [
            ('nav', 'Home', 'nav must be a list'),
            ('nav', ['Home'], 'nav[0] must be an object'),
            ('nav', [{'url': '/a/'}], 'nav[0]: missing "label"'),
            ('nav', [{'label': 'A'}], 'nav[0]: missing "url"'),
            ('nav', [{'label': ' ', 'url': '/a/'}], 'missing "label"'),
            ('nav', [{'label': 'A', 'url': 'a/'}], "url 'a/' must be an internal address"),
            ('nav', [{'label': 'A', 'url': '/a'}], "url '/a' must be an internal address"),
            ('nav', [{'label': 'A', 'url': 'https://example.com/'}], 'must be an internal address'),
            ('nav', [{'label': 'A', 'url': '//example.com/'}], 'must be an internal address'),
            ('nav', [{'label': 'A', 'url': '/a/', 'action': 'yes'}], 'nav[0]: "action" must be true or false'),
            ('nav', [{'label': 'A', 'url': '/a/'}, {'label': 'B', 'url': '/a/'}], "nav[1]: url '/a/' is repeated"),
            ('nav', [{'label': 'A', 'url': '/a/', 'children': [{'label': 'B', 'url': '/a/'}]}], 'nav[0] › children[0]: url'),
            ('nav', [{'label': 'A', 'url': '/a/', 'children': 'x'}], '"children" must be a list'),
            ('nav', [{'label': 'A', 'url': '/a/', 'children': [{'label': 'B', 'url': '/b/', 'children': []}]}],
             'nav[0] › children[0]: "children" is only allowed in one level'),
            ('nav', [{'label': 'A', 'url': '/a/', 'children': [{'label': 'B', 'url': '/b/', 'action': True}]}],
             'nav[0] › children[0]: "action" is only allowed on a top-level'),
            ('legal_nav', [{'label': 'A', 'url': '/a/', 'children': []}], 'legal_nav[0]: "children" is only allowed'),
            ('legal_nav', [{'label': 'A', 'url': '/a/', 'action': True}], 'legal_nav[0]: "action" is only allowed'),
            ('legal_nav', [{'label': 'A', 'url': '/a/'}, {'label': 'B', 'url': '/a/'}], "legal_nav[1]: url '/a/' is repeated"),
        ]
        for key, value, needle in cases:
            with self.subTest(key=key, needle=needle):
                self.assertIn(needle, self.nav_error(key, value))

    def test_the_same_url_may_appear_in_nav_and_legal_nav(self):
        fixtures.make_project(self.root, site={'legal_nav': [{'label': 'Home again', 'url': '/'}]})
        build.load_site(self.root)

    def test_a_broken_nav_stops_before_touching_the_output(self):
        self.run_build()
        fixtures.make_project(self.root, site={'nav': [{'label': 'A'}]})
        with self.assertRaises(common.BuildError):
            self.run_build()
        self.assertTrue((self.root / 'dist' / 'index.html').exists())

    def test_no_slug_is_written_by_hand_in_the_template_partials(self):
        for name in ('header.html', 'footer.html'):
            text = (REPO / 'src' / 'partials' / name).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'href="/[a-z]', name)


class TestPageMarkers(Project):
    """{{page_url}} and {{page_updated}}: a page never writes its own URL or date."""

    LD = ('<script type="application/ld+json">{"@type": "WebPage", "@id": "{{page_url}}#webpage", '
          '"url": "{{page_url}}", "name": "{{page_title}}", "dateModified": "{{page_updated}}"}</script>')

    def built(self, rel='index.html'):
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / rel).read_text(encoding='utf-8')

    def jsonld(self, html_text, node_id):
        import json
        import re
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S).group(1))
        return next(n for n in data['@graph'] if n.get('@id') == node_id)

    def test_page_url_on_the_home_page_and_on_an_inner_page(self):
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Home page of the fixture', f'<p>{{{{page_url}}}}</p>{self.LD}'))
        fixtures.write(self.root, 'src/pages/company/team/index.html',
                       fixtures.page('Team page of the fixture', f'<a href="{{{{page_url}}}}">me</a>{self.LD}', updated='2026-02-03'))
        home, team = self.built(), self.built('company/team/index.html')
        self.assertIn('<p>https://fixture.test/</p>', home)
        self.assertEqual(self.jsonld(home, 'https://fixture.test/#webpage')['url'], 'https://fixture.test/')
        self.assertIn('<a href="https://fixture.test/company/team/">me</a>', team)
        node = self.jsonld(team, 'https://fixture.test/company/team/#webpage')
        self.assertEqual((node['url'], node['dateModified']), ('https://fixture.test/company/team/', '2026-02-03'))

    def test_page_updated_in_html_and_in_json_ld(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       fixtures.page('Talk page of the fixture', f'<p>Updated {{{{page_updated}}}}</p>{self.LD}', updated='2026-03-04'))
        talk = self.built('talk/index.html')
        self.assertIn('<p>Updated 2026-03-04</p>', talk)
        self.assertEqual(self.jsonld(talk, 'https://fixture.test/talk/#webpage')['dateModified'], '2026-03-04')

    def test_the_url_follows_the_site_url_override(self):
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', '<p>{{page_url}}</p>'))
        ok, stdout, _ = self.run_build(site_url_override='https://other.test')
        self.assertTrue(ok, stdout)
        self.assertIn('<p>https://other.test/talk/</p>', (self.root / 'dist' / 'talk' / 'index.html').read_text(encoding='utf-8'))

    def test_page_updated_without_updated_names_the_page(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       '---\ntitle: Talk page of the fixture\ndescription: Talk page description.\n---\n'
                       '<main id="main"><h1>Talk</h1><p>{{page_updated}}</p></main>\n')
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        self.assertIn('page /talk/', str(ctx.exception))
        self.assertIn('{{page_updated}}', str(ctx.exception))
        self.assertIn('updated', str(ctx.exception))

    def test_a_page_without_updated_may_skip_the_marker(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       '---\ntitle: Talk page of the fixture\ndescription: Talk page description.\nrobots: noindex, follow\n---\n'
                       '<main id="main"><h1>Talk</h1><p>{{page_url}}</p></main>\n')
        self.assertIn('<p>https://fixture.test/talk/</p>', self.built('talk/index.html'))

    def test_the_markers_are_reserved_values_not_expanded_twice(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       fixtures.page('Talk "page" of the fixture', '<p title="{{page_title}}">{{page_url}}</p>'))
        self.assertIn('<p title="Talk &quot;page&quot; of the fixture">', self.built('talk/index.html'))

    def test_renaming_a_page_needs_no_other_edit(self):
        """The rename test: a page that writes {{page_url}} survives moving its folder and its nav entry. (The strict
        validator needs a complete page, which the fixture is not; V1 validates the template build.)"""
        import shutil
        body = f'<p>{{{{page_url}}}}</p>{self.LD}'
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', body))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        self.assertIn('https://fixture.test/talk/', (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8'))

        shutil.move(str(self.root / 'src/pages/talk'), str(self.root / 'src/pages/hablemos'))
        site = {'nav': [{'label': 'Home', 'url': '/'}, {'label': 'Hablemos', 'url': '/hablemos/', 'action': True}]}
        fixtures.make_project(self.root, site=site)  # rewrites the data and the template, not the pages
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        page = (self.root / 'dist' / 'hablemos' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<p>https://fixture.test/hablemos/</p>', page)
        self.assertEqual(self.jsonld(page, 'https://fixture.test/hablemos/#webpage')['url'], 'https://fixture.test/hablemos/')
        self.assertNotIn('/talk/', page)
        self.assertIn('<a class="nav-action active" href="/hablemos/" aria-current="page">Hablemos</a>', page)
        self.assertIn('https://fixture.test/hablemos/', (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8'))


class TestSitemapOrder(Project):
    """The sitemap lists `/` first and then the indexable pages by URL; the menu order does not rule it."""

    def locs(self):
        import re
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        text = (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8')
        return re.findall(r'<loc>https://fixture.test(.*?)</loc>', text)

    def test_home_first_then_by_url_whatever_the_menu_says(self):
        for rel in ('zeta', 'alpha', 'company/team', 'company', 'talk'):
            fixtures.write(self.root, f'src/pages/{rel}/index.html', fixtures.page(f'Page {rel} of the fixture'))
        self.assertEqual(self.locs(), ['/', '/alpha/', '/company/', '/company/team/', '/talk/', '/zeta/'])

    def test_the_404_and_the_noindex_pages_are_left_out(self):
        fixtures.write(self.root, 'src/pages/hidden/index.html',
                       fixtures.page('Hidden page of the fixture', robots='noindex, follow'))
        self.assertEqual(self.locs(), ['/'])

    def test_a_removed_setting_is_an_error_that_names_it(self):
        for key in common.REMOVED_SETTINGS:
            with self.subTest(key=key):
                fixtures.make_project(self.root, site={key: ['/']})
                with self.assertRaises(common.BuildError) as ctx:
                    build.load_site(self.root)
                self.assertIn(f'"{key}" was removed', str(ctx.exception))
                self.assertIn('Delete it', str(ctx.exception))

    def test_there_is_no_fixed_order_left_in_the_engine(self):
        fixtures.write(self.root, 'src/pages/alpha/index.html', fixtures.page('Alpha page of the fixture'))
        self.assertEqual(self.locs(), ['/', '/alpha/'])
        self.assertFalse(hasattr(build, 'DEFAULT_SITEMAP_ORDER'))


class TestSiteTextMarkers(Project):
    """Texts of site.json used as markers in the layout, the pages and llms.txt (F4B)."""

    KEYS = {'site_description': 'A short & plain description.', 'theme_color': '#0E131A',
            'legal_name': 'Fixture Legal S.L.', 'legal_tax_id': 'B-0000', 'legal_address': '1 Fixture <Street>',
            'legal_jurisdiction': 'Fixtureland'}

    def built(self, rel, **site):
        fixtures.make_project(self.root, site={**self.KEYS, **site})
        fixtures.write(self.root, 'src/layout.html', fixtures.LAYOUT.replace(
            '<meta name="robots"', '<meta name="theme-color" content="{{theme_color}}">\n<meta name="robots"'))
        fixtures.write(self.root, 'src/pages/legal/index.html', fixtures.page(
            'Legal page of the fixture', '<p>{{legal_name}} | {{legal_tax_id}} | {{legal_address}} | {{legal_jurisdiction}}</p>',
            robots='noindex, follow'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / rel).read_text(encoding='utf-8')

    def test_legal_data_and_theme_color_reach_the_layout_and_the_pages_escaped(self):
        self.assertIn('<meta name="theme-color" content="#0E131A">', self.built('legal/index.html'))
        self.assertIn('<p>Fixture Legal S.L. | B-0000 | 1 Fixture &lt;Street&gt; | Fixtureland</p>', self.built('legal/index.html'))

    def test_a_missing_key_is_an_error_that_points_to_site_json(self):
        fixtures.make_project(self.root, site={k: v for k, v in self.KEYS.items() if k != 'legal_name'})
        fixtures.write(self.root, 'src/pages/legal/index.html', fixtures.page('Legal page of the fixture', '<p>{{legal_name}}</p>'))
        with self.assertRaises(common.BuildError) as ctx:
            build.build(self.root, no_validate=True)
        self.assertIn('{{legal_name}}', str(ctx.exception))
        self.assertIn('src/data/site.json', str(ctx.exception))


class TestLlmsPages(Project):
    """`{{llms_pages}}`: one `- [Title](URL): description` line per indexable page, the menu order first."""

    def test_the_menu_pages_come_first_then_the_rest_by_url(self):
        pages = {'/': ('Home', 'd'), '/alpha/': ('Alpha', 'd'), '/talk/': ('Talk', 'd'), '/zeta/': ('Zeta', 'd')}
        text = build.render_llms_pages(pages, ['/talk/', '/', '/missing/', '/talk/'], 'https://x.test')
        self.assertEqual([line.split('](')[0] for line in text.split('\n')], ['- [Talk', '- [Home', '- [Alpha', '- [Zeta'])
        self.assertIn('- [Talk](https://x.test/talk/): d', text)

    def build_llms(self, **site):
        fixtures.make_project(self.root, site=site or None)
        fixtures.write(self.root, 'src/static/llms.txt', '# {{site_name}}\n\n> {{site_description}}\n\n{{llms_pages}}\n')
        return None

    def llms(self):
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / 'llms.txt').read_text(encoding='utf-8').split('\n')

    def test_build_lists_indexable_pages_in_menu_order_and_skips_404_and_noindex(self):
        self.build_llms(site_description='What the site is.')
        for rel in ('zeta', 'alpha', 'talk', 'company'):
            fixtures.write(self.root, f'src/pages/{rel}/index.html', fixtures.page(f'Page {rel} of the fixture'))
        fixtures.write(self.root, 'src/pages/hidden/index.html', fixtures.page('Hidden page', robots='noindex, follow'))
        lines = self.llms()
        self.assertEqual(lines[:3], ['# Fixture Site', '', '> What the site is.'])
        urls = [line.split('](')[1].split(')')[0] for line in lines if line.startswith('- [')]
        self.assertEqual(urls, ['https://fixture.test/', 'https://fixture.test/company/', 'https://fixture.test/talk/',
                                'https://fixture.test/alpha/', 'https://fixture.test/zeta/'])

    def test_titles_and_descriptions_come_resolved_unescaped_and_with_spaces_collapsed(self):
        self.build_llms(site_description='x')
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page(
            'Fish & Chips [menu] | {{site_name}}', description='Fresh "daily" &   more.'))
        line = next(l for l in self.llms() if '/talk/' in l)
        self.assertEqual(line, '- [Fish & Chips (menu) | Fixture Site](https://fixture.test/talk/): Fresh "daily" & more.')

    def test_a_page_without_a_description_is_an_error_that_names_it(self):
        self.build_llms(site_description='x')
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', description=''))
        with self.assertRaises(common.BuildError) as ctx:
            build.build(self.root, no_validate=True)
        self.assertIn('/talk/', str(ctx.exception))
        self.assertIn('description', str(ctx.exception))


class TestMainsTranslateErrors(unittest.TestCase):
    def run_main(self, main, argv):
        out, err = io.StringIO(), io.StringIO()
        with env_without_site_url(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_build_with_an_unknown_argument(self):
        code, _, err = self.run_main(build.main, ['--bogus'])
        self.assertEqual(code, 1)
        self.assertIn('unknown argument: --bogus', err)
        self.assertIn('usage: build.py', err)

    def test_build_refuses_an_unsafe_output_folder(self):
        code, _, err = self.run_main(build.main, ['--out', str(REPO / 'src')])
        self.assertEqual(code, 1)
        self.assertIn('✗ BUILD ABORTED:', err)

    def test_check_site_with_an_invalid_url(self):
        code, out, err = self.run_main(check_site.main, ['--site-url', 'http://example.com'])
        self.assertEqual(code, 1)
        self.assertIn('SITE_URL must start with https://', err)
        self.assertEqual(out, '')


class TestSiteUrlPrecedence(unittest.TestCase):
    def resolve(self, config, override=None, env=None):
        base = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
        if env is not None:
            base['SITE_URL'] = env
        with mock.patch.dict(os.environ, base, clear=True):
            return common.resolve_site_url(config, override)

    def test_override_then_environment_then_site_json(self):
        config = {'site_url': 'https://config.example/'}
        self.assertEqual(self.resolve(config), 'https://config.example')
        self.assertEqual(self.resolve(config, env='https://env.example'), 'https://env.example')
        self.assertEqual(self.resolve(config, 'https://cli.example', 'https://env.example'), 'https://cli.example')

    def test_an_empty_value_counts_as_not_set(self):
        self.assertEqual(self.resolve({'site_url': 'https://config.example'}, env=''), 'https://config.example')

    def test_it_must_be_https(self):
        for value in ('http://example.org', 'example.org', ''):
            with self.assertRaises(common.BuildError) as ctx:
                self.resolve({'site_url': value})
            self.assertIn('SITE_URL must start with https://', str(ctx.exception))


class TestOutputIsLf(Project):
    def test_write_text_keeps_lf_and_utf8(self):
        path = self.root / 'a.txt'
        common.write_text(path, 'línea 1\nlínea 2\n')
        self.assertEqual(path.read_bytes(), 'línea 1\nlínea 2\n'.encode('utf-8'))

    def test_text_files_leave_with_lf_even_if_the_source_has_crlf(self):
        (self.root / 'src' / 'static' / 'extra.txt').write_bytes(b'one\r\ntwo\r\n')
        (self.root / 'src' / 'pages' / 'index.html').write_bytes(fixtures.HOME.replace('\n', '\r\n').encode('utf-8'))
        self.run_build()
        files = [f for f in (self.root / 'dist').rglob('*') if f.is_file()]
        self.assertEqual([f.name for f in files if b'\r' in f.read_bytes()], [])
        self.assertEqual((self.root / 'dist' / 'extra.txt').read_bytes(), b'one\ntwo\n')

    def test_no_file_of_dist_has_crlf_in_the_template(self):
        """Smoke test: builds the template (the only engine test that reads src/) and looks for CRLF."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'out'
            with env_without_site_url(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                ok = build.build(REPO, out_dir=out, minify=True, no_validate=False, strict=False)
            self.assertTrue(ok)
            text_files = [f for f in out.rglob('*') if f.is_file() and f.suffix in build.TEXT_STATIC_SUFFIXES]
            self.assertTrue(text_files)
            self.assertEqual([f.name for f in text_files if b'\r\n' in f.read_bytes()], [])


class TestMarkerRule(Project):
    """Plan 4.3: every text of site.json is a marker; one pass; reserved names and `{{` in a value are errors (F5A)."""

    def tables(self, **site):
        fixtures.make_project(self.root, site=site)
        site = build.load_site(self.root)
        return build._marker_tables(site, build._site_values(site).derived)

    def error(self, **site):
        with self.assertRaises(common.BuildError) as ctx:
            self.tables(**site)
        return str(ctx.exception)

    def test_a_new_text_is_a_marker_escaped_for_html_and_plain_for_json_ld(self):
        plain, escaped = self.tables(tagline='Cats & <dogs>')
        self.assertEqual(plain['{{tagline}}'], 'Cats & <dogs>')
        self.assertEqual(escaped['{{tagline}}'], 'Cats &amp; &lt;dogs&gt;')

    def test_lists_and_objects_are_not_markers(self):
        plain, escaped = self.tables(extra=['a', 'b'], more={'k': 'v'})
        for marker in ('{{extra}}', '{{more}}', '{{nav}}'):
            self.assertNotIn(marker, plain)
        self.assertIn('{{nav}}', escaped, 'the menus are generated HTML, not a text of site.json')

    def test_a_reserved_name_or_the_ui_prefix_is_an_error_that_names_the_key(self):
        for key in ('page_title', 'location', 'jsonld', 'ui_skip'):
            with self.subTest(key=key):
                message = self.error(**{key: 'x'})
                self.assertIn(f'"{key}"', message)
                self.assertIn('src/data/site.json', message)

    def test_a_marker_inside_a_value_is_an_error_that_names_the_key(self):
        message = self.error(tagline='Welcome to {{site_name}}')
        self.assertIn('"tagline"', message)
        self.assertIn('{{', message)

    def test_a_value_is_never_expanded_again(self):
        table = {'{{a}}': '{{b}}', '{{b}}': 'x'}
        self.assertEqual(build._apply_markers('{{a}} {{b}}', table), '{{b}} x')
        self.assertEqual(build._apply_markers('{{unknown}}', table), '{{unknown}}')

    def test_the_derived_value_wins_over_the_text_of_site_json(self):
        plain, _ = self.tables(site_url='https://other.test/')
        self.assertEqual(plain['{{site_url}}'], 'https://other.test')

    def test_location_has_only_the_parts_that_exist(self):
        self.assertEqual(self.tables(city='Leeds', region='')[0]['{{location}}'], 'Leeds')
        self.assertEqual(self.tables(city='', region='Yorkshire')[0]['{{location}}'], 'Yorkshire')
        self.assertEqual(self.tables(city='Leeds', region='Yorkshire')[0]['{{location}}'], 'Leeds, Yorkshire')
        self.assertEqual(self.tables(city='', region='')[0]['{{location}}'], '')


class TestMainNodeAndPruning(unittest.TestCase):
    """The main node is the one whose @id ends in /#business; empty data is not published (F5A)."""

    def test_the_main_node_is_found_by_its_id_whatever_its_type(self):
        nodes = [{'@type': 'WebSite', '@id': 'x/#website'}, {'@type': 'Dentist', '@id': 'x/#business'}]
        self.assertEqual(build._main_node(nodes)['@type'], 'Dentist')

    def test_without_the_id_the_build_stops_and_names_it_even_for_a_professional_service(self):
        with self.assertRaises(common.BuildError) as ctx:
            build._main_node([{'@type': 'ProfessionalService', '@id': 'x/#company'}])
        self.assertIn('/#business', str(ctx.exception))

    def test_blank_strings_empty_containers_and_a_node_with_only_its_type_are_dropped(self):
        node = {'@type': 'Organization', '@id': 'x', 'name': 'N', 'note': '  ', 'tags': [],
                'address': {'@type': 'PostalAddress', 'addressLocality': '', 'addressRegion': ' '},
                'contact': {'@type': 'ContactPoint', 'sub': {'@type': 'Thing'}}}
        self.assertEqual(build._prune_empty(node), {'@type': 'Organization', '@id': 'x', 'name': 'N'})

    def test_a_reference_and_a_node_with_data_are_kept_and_an_empty_node_is_none(self):
        self.assertEqual(build._prune_empty({'@id': 'x/#business'}), {'@id': 'x/#business'})
        self.assertEqual(build._prune_empty({'@type': 'PostalAddress', 'addressCountry': 'ES'}),
                         {'@type': 'PostalAddress', 'addressCountry': 'ES'})
        self.assertIsNone(build._prune_empty({'@type': 'PostalAddress', 'addressCountry': ''}))
        self.assertEqual(build._prune_empty([{'@type': 'Thing'}, {'@id': 'y'}]), [{'@id': 'y'}])


class TestEntityAddressCountry(Project):
    """entity.json has no code of its own for the business address (F5B): `addressCountry` is just another
    `{{country_code}}` marker of site.json, and an address left fully blank is dropped by `_prune_empty`."""

    ADDRESS_ENTITY = [{
        '@type': 'Organization', '@id': '{{site_url}}/#business', 'name': '{{site_name}}',
        'url': '{{site_url}}',
        'address': {'@type': 'PostalAddress', 'addressLocality': '{{city}}', 'addressRegion': '{{region}}',
                    'addressCountry': '{{country_code}}'},
    }]

    LD = '<script type="application/ld+json">{"@type": "WebPage", "@id": "{{page_url}}#webpage"}</script>'

    def jsonld_business(self, html_text):
        import json
        import re
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S).group(1))
        return next(n for n in data['@graph'] if str(n.get('@id', '')).endswith('/#business'))

    def _build_with(self, site):
        fixtures.make_project(self.root, site=site, entity=self.ADDRESS_ENTITY)
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Fixture home', self.LD))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / 'index.html').read_text(encoding='utf-8')

    def test_address_country_resolves_from_site_json(self):
        home = self._build_with({'country_code': 'ES'})
        self.assertEqual(self.jsonld_business(home)['address']['addressCountry'], 'ES')

    def test_an_address_left_fully_blank_is_not_published(self):
        home = self._build_with({'city': '', 'region': '', 'country_code': ''})
        self.assertNotIn('address', self.jsonld_business(home))


class TestInterfaceTexts(Project):
    """The fixed words of the interface (plan 4.4): the UI table, `language`, and `ui` of site.json."""

    BREADCRUMB = '<nav aria-label="{{ui_breadcrumb_label}}"><a href="/">{{ui_home}}</a></nav>'

    def built(self, **site):
        """Build the fixture (a page with a breadcrumb included) and return the text of everything it wrote."""
        fixtures.make_project(self.root, site=site)
        fixtures.write(self.root, 'src/pages/inner/index.html', fixtures.page('Inner page of the fixture', self.BREADCRUMB))
        fixtures.write(self.root, 'src/pages/contact/index.html', fixtures.page('Contact page of the fixture', '{{contact_methods}}'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return {f.relative_to(self.root / 'dist'): f.read_text(encoding='utf-8')
                for f in (self.root / 'dist').rglob('*.html')}

    def everything(self, **site):
        """The text of every page of two builds: one with email and phone, one with no contact data at all (so
        that every interface text, `contact_empty` included, has a place where it is published)."""
        with_contact = self.built(contact_email='hello@fixture.test', phone_e164='+34600111222', **site)
        without_contact = self.built(contact_email='', phone_e164='', **site)
        return '\n'.join(list(with_contact.values()) + list(without_contact.values()))

    def test_every_language_has_the_same_interface_keys(self):
        self.assertEqual(set(build.UI), set(build.LANGUAGES))
        for language, texts in build.UI.items():
            with self.subTest(language=language):
                self.assertEqual(set(texts), set(build.UI['en']))
                self.assertTrue(all(isinstance(t, str) and t.strip() for t in texts.values()))

    def test_english_is_the_default_and_publishes_every_text(self):
        everything = self.everything()
        for key, text in build.UI['en'].items():
            with self.subTest(key=key):
                self.assertIn(text, everything)

    def test_spanish_site_gets_the_language_attributes_and_every_text_in_spanish(self):
        pages = self.built(language='es')
        home = pages[Path('index.html')]
        self.assertIn('<html lang="es">', home)
        self.assertIn('content="es_ES"', home)
        everything = self.everything(language='es')
        for key, text in build.UI['es'].items():
            with self.subTest(key=key):
                self.assertIn(text, everything, 'every interface text must reach the pages')

    def test_spanish_site_publishes_no_english_interface_text(self):
        """The content of the fixture is made neutral (no word of the English table in it), so any English text
        left in the output of a Spanish site would come from the engine or the partials."""
        neutral = {'site_name': 'Fixture', 'language': 'es', 'phone_e164': '+34600111222',
                   'nav': [{'label': 'Start', 'url': '/'}], 'legal_nav': [{'label': 'Notice', 'url': '/legal/'}]}
        fixtures.make_project(self.root, site=neutral)
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Landing for the fixture', self.BREADCRUMB + '{{contact_methods}}'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        everything = '\n'.join(f.read_text(encoding='utf-8') for f in (self.root / 'dist').rglob('*.html'))
        for key, english in build.UI['en'].items():
            if english == build.UI['es'][key]:
                continue  # the same word in both languages (Legal)
            with self.subTest(key=key):
                self.assertIsNone(re.search(r'(?<!\w)' + re.escape(english) + r'(?!\w)', everything), english)

    def test_the_ui_of_site_json_rewords_one_text_and_leaves_the_rest(self):
        pages = self.built(language='es', ui={'open_menu': 'Menú de la casa'})
        home = pages[Path('index.html')]
        self.assertIn('aria-label="Menú de la casa"', home)
        self.assertIn(build.UI['es']['main_navigation'], home)

    def test_a_reworded_text_is_escaped(self):
        home = self.built(ui={'open_menu': 'Menu "<b>" & more'})[Path('index.html')]
        self.assertIn('aria-label="Menu &quot;&lt;b&gt;&quot; &amp; more"', home)

    def test_the_breadcrumb_text_reaches_the_json_ld_too(self):
        fixtures.make_project(self.root, site={'language': 'es'})
        ld = ('<script type="application/ld+json">{"@type": "BreadcrumbList", "itemListElement": '
              '[{"@type": "ListItem", "position": 1, "name": "{{ui_home}}", "item": "{{site_url}}/"}]}</script>')
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Fixture home', ld))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        self.assertIn('"name":"Inicio"', (self.root / 'dist' / 'index.html').read_text(encoding='utf-8').replace(' ', ''))

    def test_a_null_ui_is_the_same_as_none(self):
        absent = self.built()
        shutil.rmtree(self.root / 'dist')
        self.assertEqual(self.built(ui=None), absent)

    def test_an_unknown_key_fails_and_names_it_with_a_hint(self):
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(fixtures.make_project(self.root, site={'ui': {'skip_to_conten': 'x'}}))
        message = str(ctx.exception)
        self.assertIn('"skip_to_conten"', message)
        self.assertIn('did you mean "skip_to_content"', message)

    def test_every_problem_is_reported_at_once(self):
        fixtures.make_project(self.root, site={'ui': {'nope': 'x', 'open_menu': '  ', 'home': 'Hi {{site_name}}', 'footer_site': 3}})
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(self.root)
        message = str(ctx.exception)
        self.assertIn('4 problems', message)
        for key in ('"nope"', '"open_menu"', '"home"', '"footer_site"'):
            self.assertIn(key, message)

    def test_ui_must_be_an_object(self):
        for bad in (['home'], 'home', 5):
            with self.subTest(bad=bad):
                fixtures.make_project(self.root, site={'ui': bad})
                with self.assertRaises(common.BuildError) as ctx:
                    build.load_site(self.root)
                self.assertIn('must be an object', str(ctx.exception))

    def test_the_old_override_setting_is_removed_and_points_to_ui(self):
        key = next(k for k, why in common.REMOVED_SETTINGS.items() if '`ui`' in why)
        fixtures.make_project(self.root, site={key: {}})
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(self.root)
        self.assertIn(f'"{key}" was removed', str(ctx.exception))
        self.assertIn('`ui`', str(ctx.exception))

    def test_an_unsupported_language_still_fails_clearly(self):
        fixtures.make_project(self.root, site={'language': 'fr'})
        with self.assertRaises(common.BuildError) as ctx:
            build.load_site(self.root)
        self.assertIn("unsupported language 'fr'", str(ctx.exception))
        self.assertIn('supported: en, es', str(ctx.exception))




class TestRenderContactMarkers(unittest.TestCase):
    """`render_contact_markers`: pure function, the channels that exist and nothing else."""

    UI = build.UI['en']

    def test_no_channel_gives_the_empty_text_and_no_footer_or_button(self):
        markers = build.render_contact_markers('', '', '', self.UI)
        self.assertEqual(markers['{{contact_methods}}'], '<p>%s</p>' % self.UI['contact_empty'])
        self.assertEqual(markers['{{footer_contact}}'], '')
        self.assertEqual(markers['{{whatsapp_float}}'], '')

    def test_every_channel_gets_its_own_link_and_none_is_empty(self):
        markers = build.render_contact_markers('hi@x.test', '34600111222', 'https://wa.me/34600111222?text=Hi', self.UI)
        methods = markers['{{contact_methods}}']
        for href in ('mailto:hi@x.test', 'tel:+34600111222', 'https://wa.me/34600111222?text=Hi'):
            self.assertIn('href="%s"' % href, methods)
            self.assertIn('href="%s"' % href, markers['{{footer_contact}}'])
        self.assertIn('href="https://wa.me/34600111222?text=Hi"', markers['{{whatsapp_float}}'])
        self.assertIn('class="whatsapp-float"', markers['{{whatsapp_float}}'])
        self.assertNotIn('href=""', ''.join(markers.values()))

    def test_values_are_escaped_for_html(self):
        markers = build.render_contact_markers('a&b"@x.test', '', '', self.UI)
        self.assertIn('mailto:a&amp;b&quot;@x.test', markers['{{contact_methods}}'])
        self.assertNotIn('a&b"', markers['{{contact_methods}}'])


class TestContactOptional(Project):
    """Email, phone and WhatsApp are optional (plan F7): what is not given is not written, so no link is broken."""

    def everything(self, **site):
        fixtures.make_project(self.root, site=site)
        fixtures.write(self.root, 'src/pages/contact/index.html', fixtures.page('Contact page of the fixture', '{{contact_methods}}'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        pages = [f.read_text(encoding='utf-8') for f in sorted((self.root / 'dist').rglob('*.html'))]
        for text in pages:
            self.assertNotIn('href=""', text)
            self.assertNotIn('href="mailto:"', text)
        return '\n'.join(pages)

    def test_without_a_phone_there_is_no_wa_me_no_button_and_no_tel(self):
        for phone in ('', None):
            with self.subTest(phone=phone):
                text = self.everything(phone_e164=phone)
                for forbidden in ('wa.me', 'whatsapp-float', 'tel:'):
                    self.assertNotIn(forbidden, text)
                self.assertIn('mailto:hello@fixture.test', text)

    def test_without_an_email_there_is_no_mailto(self):
        for email in ('', None, '   '):
            with self.subTest(email=email):
                text = self.everything(contact_email=email, phone_e164='+34 600 11 22 33')
                self.assertNotIn('mailto:', text)
                self.assertIn('href="tel:+34600112233"', text)
                self.assertIn('https://wa.me/34600112233', text)
                self.assertIn('whatsapp-float', text)

    def test_without_either_the_page_says_so_and_the_footer_has_no_address(self):
        text = self.everything(contact_email='', phone_e164='')
        self.assertIn(build.UI['en']['contact_empty'], text)
        for forbidden in ('mailto:', 'wa.me', 'tel:', 'whatsapp-float', '<address', 'None'):
            self.assertNotIn(forbidden, text)

    def test_the_empty_text_follows_the_language(self):
        text = self.everything(contact_email='', phone_e164='', language='es')
        self.assertIn(build.UI['es']['contact_empty'], text)
        self.assertNotIn(build.UI['en']['contact_empty'], text)

    def test_a_phone_that_is_a_whatsapp_link_gives_whatsapp_but_no_tel(self):
        text = self.everything(contact_email='', phone_e164='https://wa.me/message/ABC123')
        self.assertIn('href="https://wa.me/message/ABC123"', text)
        self.assertIn('whatsapp-float', text)
        self.assertNotIn('tel:', text)


class TestReadPngSize(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_the_size_is_read_from_the_header(self):
        path = fixtures.write_bytes(self.dir, 'a.png', fixtures.png_header(1600, 840))
        self.assertEqual(build.read_png_size(path), (1600, 840, None))

    def test_a_missing_file_a_jpeg_and_a_truncated_file_give_a_clear_problem(self):
        cases = {'missing.png': None, 'photo.png': b'\xff\xd8\xff\xe0' + b'\x00' * 40, 'short.png': b'\x89PNG'}
        for name, data in cases.items():
            with self.subTest(name=name):
                path = self.dir / name
                if data is not None:
                    path.write_bytes(data)
                width, height, problem = build.read_png_size(path)
                self.assertIsNone(width)
                self.assertIsNone(height)
                self.assertIn('1200×630', problem)


class TestOgImageSize(Project):
    """`{{og_image_width}}` and `{{og_image_height}}` are the real size of src/static/images/og-image.png."""

    def meta(self):
        text = (self.root / 'dist' / 'index.html').read_text(encoding='utf-8')
        return (re.search(r'og:image:width" content="([^"]*)"', text).group(1),
                re.search(r'og:image:height" content="([^"]*)"', text).group(1))

    def test_the_markers_follow_the_png(self):
        for size in ((1200, 630), (1600, 840), (600, 600)):
            with self.subTest(size=size):
                fixtures.write_bytes(self.root, 'src/static/images/og-image.png', fixtures.png_header(*size))
                ok, stdout, _ = self.run_build()
                self.assertTrue(ok, stdout)
                self.assertEqual(self.meta(), tuple(str(n) for n in size))
                self.assertNotIn('og-image.png', stdout)  # a good PNG gives no warning

    def test_a_missing_or_wrong_image_is_a_warning_not_a_made_up_size(self):
        cases = {'missing': None, 'jpeg': b'\xff\xd8\xff\xe0' + b'\x00' * 40}
        for name, data in cases.items():
            with self.subTest(case=name):
                (self.root / 'src/static/images/og-image.png').unlink(missing_ok=True)
                if data is not None:
                    fixtures.write_bytes(self.root, 'src/static/images/og-image.png', data)
                ok, stdout, _ = self.run_build()
                self.assertTrue(ok, stdout)
                self.assertIn('og-image.png', stdout)
                self.assertEqual(self.meta(), ('', ''))


class TestErrorsNameTheFix(Project):
    """Every build error says what fails, where (the page or file) and how to fix it; none is a traceback."""

    LD = '<script type="application/ld+json">{ "@type": "WebPage", "dateModified": "%s" %s</script>'

    def fails_with(self, *needles):
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        for needle in needles:
            self.assertIn(needle, str(ctx.exception))

    def test_invalid_json_ld_names_the_page(self):
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', self.LD % ('2026-01-01', '')))
        self.fails_with('page /talk/', 'not valid JSON', 'Fix')

    def test_a_date_that_differs_from_updated_names_the_page_and_the_fix(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       fixtures.page('Talk page of the fixture', self.LD % ('2026-02-02', '}')))
        self.fails_with('page /talk/', '2026-02-02', '2026-01-01', 'page_updated')

    def test_an_unresolved_marker_in_llms_txt_names_the_file_and_the_key(self):
        fixtures.write(self.root, 'src/static/llms.txt', '# {{site_name}}\n\n{{no_such_marker}}\n')
        self.fails_with('src/static/llms.txt', 'no_such_marker', 'site.json')

    def test_compose_page_has_no_marker_shaped_defaults(self):
        import inspect
        defaults = {name: p.default for name, p in inspect.signature(build.compose_page).parameters.items()
                    if p.default is not inspect.Parameter.empty}
        self.assertEqual(defaults, {})


class TestCommandLineAll(unittest.TestCase):
    """`build.py --all` (plan F8B): the pipeline is chosen by the options and the variables, without bash."""

    def parse(self, *args, **environ):
        return build.parse_args(list(args), environ)

    def test_a_plain_build_does_not_minify_and_is_not_strict(self):
        self.assertEqual(self.parse(), dict(out_dir=None, minify=False, no_validate=False, strict=False, all=False))

    def test_all_minifies_validates_and_is_strict_by_default(self):
        options = self.parse('--all')
        self.assertEqual((options['all'], options['minify'], options['strict'], options['no_validate']),
                         (True, True, True, False))

    def test_the_variables_turn_minify_and_strict_off_in_any_case(self):
        for value in ('FALSE', 'false', ' False '):
            with self.subTest(value=value):
                options = self.parse('--all', CSS_MINIFY=value, CHECK_STRICT=value)
                self.assertEqual((options['minify'], options['strict']), (False, False))

    def test_any_other_value_keeps_them_on(self):
        for value in ('TRUE', 'true', '0', ''):
            with self.subTest(value=value):
                options = self.parse('--all', CSS_MINIFY=value, CHECK_STRICT=value)
                self.assertEqual((options['minify'], options['strict']), (True, True))

    def test_the_variables_do_not_change_a_plain_build(self):
        options = self.parse(CSS_MINIFY='TRUE', CHECK_STRICT='TRUE')
        self.assertEqual((options['minify'], options['strict']), (False, False))

    def test_an_explicit_option_wins_over_the_variable(self):
        options = self.parse('--all', '--minify', 'false', CSS_MINIFY='TRUE')
        self.assertFalse(options['minify'])
        self.assertTrue(self.parse('--all', '--strict', CHECK_STRICT='FALSE')['strict'])

    def test_all_with_no_validate_is_an_error_that_says_so(self):
        with self.assertRaises(build.BuildError) as ctx:
            self.parse('--all', '--no-validate')
        self.assertIn('--all always validates', str(ctx.exception))
        self.assertIn('usage: build.py [--all]', str(ctx.exception))


class TestRunAll(Project):
    """`build.run` on the fixture. The validator is replaced by a stub: what is tested here is the pipeline, not the
    SEO rules (the fixture is a minimal site that the real validator rightly rejects)."""

    CLEAN = ([], [])

    def setUp(self):
        super().setUp()
        fixtures.write_bytes(self.root, 'src/static/images/og-image.png', fixtures.png_header(1200, 630))  # no build warning

    def run_cli(self, *argv, checks=CLEAN, **environ):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(build.check_site, 'run_checks', return_value=checks) as run_checks, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = build.run(self.root, list(argv), environ)
        self.run_checks = run_checks
        return code, out.getvalue(), err.getvalue()

    def css(self):
        return (self.root / 'dist' / 'css' / 'site.css').read_text(encoding='utf-8')

    def test_all_is_a_build_plus_the_validation_of_the_output(self):
        code, _, _ = self.run_cli('--all')
        self.assertEqual(code, 0)
        self.run_checks.assert_called_once_with(self.root / 'dist', 'https://fixture.test')
        self.assertTrue((self.root / 'dist' / 'index.html').is_file())

    def test_all_produces_the_same_output_as_a_minified_build_followed_by_the_validation(self):
        self.run_cli('--all')
        all_files = {p.relative_to(self.root / 'dist'): p.read_bytes() for p in (self.root / 'dist').rglob('*') if p.is_file()}
        self.run_build(minify=True, no_validate=True)
        self.assertEqual(all_files, {p.relative_to(self.root / 'dist'): p.read_bytes()
                                     for p in (self.root / 'dist').rglob('*') if p.is_file()})

    def test_a_validator_error_makes_all_fail(self):
        code, out, _ = self.run_cli('--all', checks=([('x.html', 'broken thing')], []))
        self.assertEqual(code, 1)
        self.assertIn('x.html', out)
        self.assertIn('BUILD FAILED', out)

    def test_a_warning_fails_all_unless_check_strict_is_false(self):
        warning = ([], [('x.html', 'doubtful thing')])
        code, out, _ = self.run_cli('--all', checks=warning)
        self.assertEqual(code, 1)
        self.assertIn('treated as errors', out)
        code, out, _ = self.run_cli('--all', checks=warning, CHECK_STRICT='FALSE')
        self.assertEqual(code, 0)
        self.assertIn('doubtful thing', out)
        self.assertNotIn('treated as errors', out)

    def test_strict_in_a_plain_build_fails_on_a_warning_and_without_it_does_not(self):
        warning = ([], [('x.html', 'doubtful thing')])
        self.assertEqual(self.run_cli(checks=warning)[0], 0)
        self.assertEqual(self.run_cli('--strict', checks=warning)[0], 1)

    def test_css_minify_false_builds_without_minifying(self):
        source = (self.root / 'src' / 'css' / 'site.css').read_text(encoding='utf-8')
        self.run_cli('--all', CSS_MINIFY='FALSE')
        self.assertEqual(self.css(), source)
        self.run_cli('--all')
        self.assertNotEqual(self.css(), source)
        self.assertLess(len(self.css()), len(source))

    def test_site_url_reaches_the_output_and_the_validator(self):
        with mock.patch.dict(os.environ, {'SITE_URL': 'https://env.test'}):
            code, _, _ = self.run_cli('--all')
        self.assertEqual(code, 0)
        self.assertIn('https://env.test/sitemap.xml', (self.root / 'dist' / 'robots.txt').read_text(encoding='utf-8'))
        self.run_checks.assert_called_once_with(self.root / 'dist', 'https://env.test')

    def test_the_out_option_is_respected(self):
        out = self.root / 'elsewhere'
        code, _, _ = self.run_cli('--all', '--out', str(out))
        self.assertEqual(code, 0)
        self.assertTrue((out / 'index.html').is_file())
        self.run_checks.assert_called_once_with(out, 'https://fixture.test')

    def test_example_data_left_is_a_notice_on_stderr_and_never_a_failure(self):
        fixtures.make_project(self.root, site={'site_name': 'Your Business'})
        code, out, err = self.run_cli('--all')
        self.assertEqual(code, 0)
        self.assertIn('BUILD SUCCESS', out)
        self.assertIn('WARNING: not ready to publish', err)
        self.assertIn('check_site.py --prelaunch', err)

    def test_no_example_data_no_notice(self):
        code, _, err = self.run_cli('--all')
        self.assertEqual((code, err), (0, ''))

    def test_a_failed_build_gives_no_notice(self):
        fixtures.make_project(self.root, site={'site_name': 'Your Business'})
        code, _, err = self.run_cli('--all', checks=([('x.html', 'broken thing')], []))
        self.assertEqual(code, 1)
        self.assertNotIn('not ready to publish', err)

    def test_a_bad_option_is_an_error_message_not_a_traceback(self):
        code, _, err = self.run_cli('--all', '--no-validate')
        self.assertEqual(code, 1)
        self.assertIn('--all always validates', err)
        self.assertNotIn('Traceback', err)


class TestNoBashAndOldPython(unittest.TestCase):
    def test_run_all_builds_with_all_and_does_not_look_for_bash(self):
        import run_all
        calls = []
        done = mock.Mock(returncode=0)
        with mock.patch.object(run_all.subprocess, 'run', side_effect=lambda cmd, **kw: calls.append(cmd) or done), \
                mock.patch.object(sys, 'argv', ['run_all.py', '--skip-tests', '--no-dev']), \
                contextlib.redirect_stdout(io.StringIO()):
            run_all.main()
        self.assertEqual(calls, [[sys.executable, str(LEGIBLE / 'build.py'), '--all']])
        self.assertFalse(hasattr(run_all, 'shutil'))

    def test_build_sh_is_a_wrapper_of_build_py_all(self):
        lines = [l for l in (LEGIBLE / 'build.sh').read_text(encoding='utf-8').splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        self.assertLessEqual(len(lines), 8)
        self.assertTrue(any('build.py --all "$@"' in l for l in lines))

    def test_a_python_older_than_the_minimum_gets_the_clear_message(self):
        """No bash script checks the version any more: common.py does, and it must be reached by every entry point."""
        code = ('import sys, runpy; sys.path.insert(0, %r); sys.version_info = (3, 9, 18, "final", 0); '
                'runpy.run_path(%r, run_name="__main__")' % (str(LEGIBLE), str(LEGIBLE / 'build.py')))
        r = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, cwd=REPO)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Python %d.%d or newer is required (found 3.9.18)' % common.MIN_PYTHON, r.stderr)
        self.assertNotIn('Traceback', r.stderr)

    def test_every_script_still_parses_with_the_grammar_of_the_python_before_the_minimum(self):
        """Otherwise that Python would stop with a SyntaxError before reaching the message above."""
        older = (common.MIN_PYTHON[0], common.MIN_PYTHON[1] - 1)
        for path in sorted(LEGIBLE.glob('*.py')):
            with self.subTest(file=path.name):
                ast.parse(path.read_text(encoding='utf-8'), filename=path.name, feature_version=older)


class TestMinifyCss(unittest.TestCase):
    def m(self, css):
        return minify.minify_css(css)

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
        mini = minify.minify_css(css)
        without_comments = build.re.sub(r'/\*[\s\S]*?\*/', '', css)
        self.assertEqual(mini.count('{'), without_comments.count('{'))
        self.assertEqual(mini.count('}'), without_comments.count('}'))
        self.assertEqual(mini.count('{'), mini.count('}'))
        self.assertLess(len(mini), len(css))

    def test_real_css_has_no_internal_marker_leftovers(self):
        mini = minify.minify_css((REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8'))
        for leftover in ('__STR_', '__MATH_', '\x00'):
            self.assertNotIn(leftover, mini)


class TestMinifyHtml(unittest.TestCase):
    def m(self, html):
        return minify.minify_html(html)

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


class TestSafeOutput(unittest.TestCase):
    def rejected(self, path):
        """Run check_out_dir expecting an abort; capture the stderr message so it does not clutter the console."""
        with self.assertRaises(build.BuildError) as ctx:
            build.check_out_dir(path, REPO)
        self.assertEqual(ctx.exception.label, 'BUILD ABORTED')

    def test_rejects_the_root_and_protected_folders(self):
        for path in (REPO, REPO / 'src', REPO / 'legible', REPO / 'src' / 'nested-output'):
            with self.subTest(path=path):
                self.rejected(path)

    def test_rejects_a_folder_that_contains_the_project(self):
        self.rejected(REPO.parent)

    def test_accepts_a_temporary_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.check_out_dir(Path(tmp) / 'output', REPO)

    def test_a_rejected_attempt_does_not_delete_repository_files(self):
        marker = REPO / 'src' / 'layout.html'
        before = marker.read_bytes()
        self.rejected(REPO)
        self.assertEqual(marker.read_bytes(), before)


def read_dist(root):
    """{route: text} of every text file in the output of a fixture build."""
    dist = Path(root) / 'dist'
    return {p.relative_to(dist).as_posix(): p.read_text(encoding='utf-8') for p in dist.rglob('*')
            if p.is_file() and p.suffix in ('.html', '.txt', '.xml')}


class TestDomain(Project):
    """SITE_URL (the environment) and site.json decide the domain; no page writes it by hand."""

    def setUp(self):
        super().setUp()
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture'))

    def build_with(self, value):
        os.environ['SITE_URL'] = value  # restored by env_without_site_url() at cleanup
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return read_dist(self.root)

    def test_default_uses_the_domain_of_site_json(self):
        ok, _, _ = self.run_build()
        self.assertTrue(ok)
        everything = read_dist(self.root)
        self.assertIn('https://fixture.test/', everything['index.html'])
        self.assertIn('https://fixture.test/sitemap.xml', everything['robots.txt'])

    def test_site_url_changes_the_domain_across_the_output(self):
        everything = self.build_with('https://example.org')
        for route, text in everything.items():
            self.assertNotIn('https://fixture.test', text, f'{route} keeps the default domain')
        self.assertIn('<loc>https://example.org/talk/</loc>', everything['sitemap.xml'])
        self.assertIn('https://example.org/sitemap.xml', everything['robots.txt'])
        self.assertIn('<link rel="canonical" href="https://example.org/">', everything['index.html'].replace('"/>', '">'))
        self.assertIn('https://example.org/', everything['talk/index.html'])

    def test_two_domains_do_not_mix(self):
        self.assertFalse(any('two.example' in t for t in self.build_with('https://one.example').values()))
        everything = self.build_with('https://two.example')
        self.assertFalse(any('one.example' in t for t in everything.values()), 'the second build keeps leftovers of the first')
        self.assertTrue(any('two.example' in t for t in everything.values()))

    def test_trailing_slash_is_removed(self):
        self.assertNotIn('https://example.org//', ''.join(self.build_with('https://example.org/').values()))

    def test_empty_site_url_falls_back_to_site_json(self):
        """An empty SITE_URL (common in CI panels) must behave as if it were not set."""
        everything = self.build_with('')
        self.assertIn('https://fixture.test/', everything['index.html'])
        self.assertIn('https://fixture.test/sitemap.xml', everything['robots.txt'])

    def test_invalid_domain_aborts_with_a_clear_message(self):
        for value in ('http://example.org', 'example.org'):
            os.environ['SITE_URL'] = value
            with self.assertRaises(common.BuildError, msg=value) as ctx:
                self.run_build()
            self.assertIn('SITE_URL must start with https://', str(ctx.exception))

    def test_the_fixture_pages_never_write_the_domain(self):
        """Only {{site_url}} and {{page_url}} give the domain: a build under another one leaves no trace of the first."""
        for f in (self.root / 'src').rglob('*'):
            if f.is_file() and f.name != 'site.json':
                self.assertNotIn('fixture.test', f.read_text(encoding='utf-8'), f.relative_to(self.root).as_posix())


class TestMarkers(Project):
    """A marker without a value stops the build; none reaches the output (the page markers included)."""

    def test_stray_marker_in_a_page_stops_the_build(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       fixtures.page('Talk page of the fixture', '<p>{{made_up_marker}}</p>'))
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        message = str(ctx.exception)
        self.assertIn('{{made_up_marker}}', message)
        self.assertIn('src/data/site.json', message)
        self.assertIn('talk', message, 'must say which page it is on')

    def test_output_contains_no_markers(self):
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', '<p>{{site_name}}</p>'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        for route, text in read_dist(self.root).items():
            self.assertNotIn('{{', text, route)

    def test_the_page_markers_are_never_stray(self):
        body = '<p>{{page_url}} {{page_updated}} {{page_title}} {{page_description}}</p>'
        fixtures.write(self.root, 'src/pages/talk/index.html', fixtures.page('Talk page of the fixture', body, updated='2026-04-05'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        talk = read_dist(self.root)['talk/index.html']
        self.assertIn('<p>https://fixture.test/talk/ 2026-04-05 Talk page of the fixture Description of Talk page of the fixture.</p>', talk)
        self.assertNotIn('{{', talk)

    def test_a_stray_marker_next_to_page_markers_is_the_one_reported(self):
        fixtures.write(self.root, 'src/pages/talk/index.html',
                       fixtures.page('Talk page of the fixture', '<p>{{page_url}} {{page_updated}} {{made_up_marker}}</p>'))
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        self.assertIn('{{made_up_marker}}', str(ctx.exception))
        self.assertNotIn('{{page_url}}', str(ctx.exception))


class TestPageTitleMarkers(Project):
    """`{{page_title}}` and `{{page_description}}` are the page's own title and description, so the JSON-LD (whose
    `name` must equal the `<title>`) does not repeat them by hand. They work in the JSON-LD and in the content."""

    TITLE = 'Tom "the Cat" & Co: a page with careful quotes'
    DESCRIPTION = 'A description with "quotes", an ampersand & and an <angle> that must stay escaped in every place.'

    def _page(self):
        url = '{{site_url}}/zz-title-markers/'
        ld = json.dumps({'@context': 'https://schema.org', '@graph': [{
            '@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': self.TITLE,
            'description': self.DESCRIPTION, 'inLanguage': '{{in_language}}', 'dateModified': '2026-02-15',
            'isPartOf': {'@id': '{{site_url}}/#website'}, 'about': {'@id': '{{site_url}}/#business'}}]},
            ensure_ascii=False)
        text = (f'---\ntitle: {self.TITLE}\ndescription: {self.DESCRIPTION}\nrobots: index, follow\n'
                f'canonical: auto\nupdated: 2026-02-15\n---\n\n<script type="application/ld+json">{ld}</script>\n\n'
                '<main id="main"><section class="inner-hero page-width"><h1>Title markers</h1></section></main>\n')
        text = text.replace(json.dumps(self.TITLE, ensure_ascii=False), '"{{page_title}}"')
        text = text.replace(json.dumps(self.DESCRIPTION, ensure_ascii=False), '"{{page_description}}"')
        text = text.replace('<h1>', '<p class="m">{{page_title}} | {{page_description}}</p><h1>', 1)
        fixtures.write(self.root, 'src/pages/zz-title-markers/index.html', text)
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / 'zz-title-markers' / 'index.html').read_text(encoding='utf-8')

    def test_the_json_ld_name_and_description_equal_the_head(self):
        built = self._page()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', built, re.S)
        page = next(n for b in blocks for n in json.loads(b).get('@graph', []) if n.get('@type') == 'WebPage'
                    and n.get('name') == self.TITLE)
        self.assertEqual(page['description'], self.DESCRIPTION)
        self.assertIn('<title>' + html_escape(self.TITLE) + '</title>', built)

    def test_the_content_gets_the_escaped_text(self):
        built = self._page()
        self.assertIn(html_escape(self.TITLE) + ' | ' + html_escape(self.DESCRIPTION), built)
        self.assertNotIn('{{page_', built)


class TestSitemapDates(Project):
    """`updated` (front matter) and `dateModified` (JSON-LD) are the same date; a page that types both by hand
    and lets them differ is stopped. The pages are the test's own, not the template's."""

    HAND_DATED = ('<script type="application/ld+json">{{"@type": "WebPage", "@id": "{{{{site_url}}}}/hand-dated/#webpage", '
                  '"dateModified": "{}"}}</script>')

    def hand_dated_page(self, updated, modified):
        fixtures.write(self.root, 'src/pages/hand-dated/index.html',
                       fixtures.page('Page with a hand-typed date', self.HAND_DATED.format(modified), updated=updated))

    def test_updated_and_json_ld_date_mismatch_fails_the_build_and_names_both_dates(self):
        """Regression: changing only `updated` used to leave a stale sitemap lastmod and still pass."""
        self.hand_dated_page('2027-03-01', '2026-01-01')
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        msg = str(ctx.exception)
        for expected in ('/hand-dated/', '2027-03-01', '2026-01-01'):
            self.assertIn(expected, msg)

    def test_matching_dates_pass_and_reach_the_sitemap(self):
        self.hand_dated_page('2026-01-01', '2026-01-01')
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        sitemap = (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('<lastmod>2026-01-01</lastmod>', sitemap)

    def test_the_date_of_the_front_matter_is_the_lastmod_without_json_ld(self):
        fixtures.write(self.root, 'src/pages/plain/index.html', fixtures.page('Plain page of the fixture', updated='2027-05-06'))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        sitemap = (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('/plain/</loc><lastmod>2027-05-06</lastmod>', sitemap.replace('\n', '').replace('  ', ''))


class TestMainNodeType(Project):
    """The main entity node is the one with @id ".../#business", whatever its @type. A bar, a dentist or a
    restaurant uses its real Schema.org type; a missing main node stops the build and names the @id."""

    LD = '<script type="application/ld+json">{"@type": "WebPage", "@id": "{{page_url}}#webpage"}</script>'

    def build_with(self, main_type=None, entity=None):
        nodes = entity if entity is not None else [dict(fixtures.ENTITY[0])]
        if main_type is not None:
            nodes[0]['@type'] = main_type
        fixtures.make_project(self.root, entity=nodes)
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Fixture home page', self.LD))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        return (self.root / 'dist' / 'index.html').read_text(encoding='utf-8')

    @staticmethod
    def main_node(html_text):
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S).group(1))
        return next(n for n in data['@graph'] if str(n.get('@id', '')).endswith('/#business'))

    def validator_says_main_node_is_missing(self):
        errors, _ = check_site.run_checks(self.root / 'dist', 'https://fixture.test')
        return any('missing main node' in message for _, message in errors)

    def test_the_first_type_of_every_class_is_published_as_the_type_of_the_main_node(self):
        self.assertEqual(len(fixtures.MAIN_TYPES), 10)
        for main_type in fixtures.MAIN_TYPES:
            with self.subTest(type=main_type):
                self.assertEqual(self.main_node(self.build_with(main_type))['@type'], main_type)
                self.assertFalse(self.validator_says_main_node_is_missing())

    def test_a_list_of_types_is_published_as_a_list(self):
        for types in (['Restaurant', 'LocalBusiness'], ['VeterinaryCare', 'LocalBusiness']):
            with self.subTest(types=types):
                self.assertEqual(self.main_node(self.build_with(list(types)))['@type'], types)
                self.assertFalse(self.validator_says_main_node_is_missing())

    def test_without_a_main_node_the_build_fails_and_names_the_id(self):
        fixtures.make_project(self.root, entity=[{'@type': 'WebSite', '@id': '{{site_url}}/#website', 'url': '{{site_url}}'}])
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        self.assertIn('no main node', str(ctx.exception))
        self.assertIn('/#business', str(ctx.exception))

    def test_without_the_id_a_professional_service_is_not_a_fallback(self):
        fixtures.make_project(self.root, entity=[{'@type': 'ProfessionalService', '@id': '{{site_url}}/#company'}])
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        self.assertIn('/#business', str(ctx.exception))

    def test_the_validator_names_a_missing_main_node(self):
        self.build_with()
        self.assertFalse(self.validator_says_main_node_is_missing())
        page = self.root / 'dist' / 'index.html'
        page.write_text(page.read_text(encoding='utf-8').replace('/#business"', '/#other"'), encoding='utf-8')
        self.assertTrue(self.validator_says_main_node_is_missing())

    def test_null_phone_email_and_address_in_the_main_node_are_left_out_not_written_as_none(self):
        """Absorbs the entity cases of the old TestOptionalBusinessData: null is the same as missing, and the
        site-level markers ({{location}}, {{contact_email}}) do not depend on entity.json."""
        entity = [{**fixtures.ENTITY[0], 'telephone': None, 'email': None, 'address': None}]
        home = self.build_with(entity=entity)
        node = self.main_node(home)
        for key in ('telephone', 'email', 'address'):
            self.assertNotIn(key, node)
        self.assertNotIn('None', home)
        self.assertIn('Fixture City, Fixture Region', home)
        self.assertIn('hello@fixture.test', home)


class TestSpecialCharactersAndReports(Project):
    """Regressions (the old TestSpecialCharactersAndWarnings, on the fixture): values with quotes and &, an
    internal http link, a report that hid errors, truncated messages, a duplicate @id and a slug with index.html."""

    NAME = 'Café "Ana" & Sons \\ Ltd.'
    LD = '<script type="application/ld+json">{"@type": "WebPage", "@id": "{{page_url}}#webpage"}</script>'

    def build_ok(self, **site):
        fixtures.make_project(self.root, site=site)
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page('Fixture home page', self.LD))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)

    def dist(self, rel='index.html'):
        return (self.root / 'dist' / rel).read_text(encoding='utf-8')

    def errors(self):
        errors, _ = check_site.run_checks(self.root / 'dist', 'https://fixture.test')
        return [message for _, message in errors]

    def test_quotes_and_ampersand_in_the_name_are_escaped_in_html_and_intact_in_the_json_ld(self):
        self.build_ok(site_name=self.NAME)
        home = self.dist()
        self.assertIn('aria-label="Café &quot;Ana&quot; &amp; Sons', home)
        self.assertNotIn('"Ana"', home.split('<script', 1)[0])
        block = re.search(r'<script type="application/ld\+json">(.*?)</script>', home, re.S).group(1)
        self.assertIn(self.NAME, {n.get('name') for n in json.loads(block)['@graph']})

    def test_a_name_with_special_characters_adds_no_validator_error(self):
        self.build_ok()
        plain = self.errors()
        self.build_ok(site_name=self.NAME)
        self.assertEqual(self.errors(), plain)

    def test_the_report_shows_the_errors_even_when_there_are_warnings(self):
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page(
            'Short', '<a href="/path-that-does-not-exist-with-a-fairly-long-name/">x</a>' + self.LD, description='Short.'))
        ok, stdout, _ = self.run_build(no_validate=False)
        self.assertFalse(ok)
        self.assertIn('Errors', stdout)
        self.assertIn('broken internal link', stdout)
        self.assertIn('description too short', stdout)

    def test_the_report_messages_are_not_truncated(self):
        fixtures.write(self.root, 'src/pages/index.html', fixtures.page(
            'Fixture home page', '<a href="/path-that-does-not-exist-with-a-fairly-long-name/">x</a>' + self.LD))
        _, stdout, _ = self.run_build(no_validate=False)
        flat = ''.join(line.strip('║ ').strip() for line in stdout.splitlines())
        self.assertIn('/path-that-does-not-exist-with-a-fairly-long-name/', flat.replace('•', '').replace(' ', ''))

    def test_a_duplicate_json_ld_id_fails_the_build_and_names_the_id_and_the_page(self):
        """A page node that repeats an entity @id used to drop the whole JSON-LD silently."""
        fixtures.write(self.root, 'src/pages/dup/index.html', fixtures.page(
            'Page with a duplicate id', '<script type="application/ld+json">{"@graph": [{"@type": "WebPage", '
            '"@id": "{{site_url}}/#business", "name": "Duplicate"}]}</script>'))
        with self.assertRaises(common.BuildError) as ctx:
            self.run_build()
        for expected in ('duplicate JSON-LD @id', '/#business', 'dup'):
            self.assertIn(expected, str(ctx.exception))

    def test_a_slug_containing_index_html_keeps_its_url(self):
        """The page URL drops only the final index.html: my-index.html-page must not become my--page."""
        slug = 'my-index.html-page'
        fixtures.write(self.root, f'src/pages/{slug}/index.html', fixtures.page('Page with a tricky slug', self.LD))
        ok, stdout, _ = self.run_build()
        self.assertTrue(ok, stdout)
        text = self.dist(f'{slug}/index.html')
        self.assertIn(f'rel="canonical" href="https://fixture.test/{slug}/"', text)
        self.assertIn(f'property="og:url" content="https://fixture.test/{slug}/"', text)
        self.assertNotIn('my--page', text)

    def test_an_internal_http_link_is_an_error(self):
        self.build_ok()
        page = self.root / 'dist' / 'index.html'
        page.write_text(page.read_text(encoding='utf-8').replace(
            '</main>', '<p><a href="http://fixture.test/">c</a></p></main>', 1), encoding='utf-8')
        self.assertTrue(any('http instead of https' in m for m in self.errors()), self.errors())


class TestContactEmailMarker(Project):
    """Decision 6: a page that uses `{{contact_email}}` while the email is empty stops the build and names the page
    and the fix. There is no general "empty marker is an error" rule."""

    def build_page(self, body, **site):
        fixtures.make_project(self.root, site=site)
        fixtures.write(self.root, 'src/pages/legal/index.html', fixtures.page('Legal page of the fixture', body))
        return self.run_build()

    def test_an_empty_email_in_a_page_that_uses_the_marker_is_an_error_that_names_the_page_and_the_fix(self):
        for email in ('', None, '   '):
            with self.subTest(email=email):
                with self.assertRaises(common.BuildError) as ctx:
                    self.build_page('<p>Write to {{contact_email}}.</p>', contact_email=email)
                message = str(ctx.exception)
                for expected in ('legal', '{{contact_email}}', 'contact_email', 'site.json'):
                    self.assertIn(expected, message)

    def test_a_page_that_does_not_use_the_marker_builds_without_an_email(self):
        ok, stdout, _ = self.build_page('<p>No email here.</p>', contact_email='')
        self.assertTrue(ok, stdout)

    def test_with_an_email_the_marker_is_printed(self):
        ok, stdout, _ = self.build_page('<p>Write to {{contact_email}}.</p>')
        self.assertTrue(ok, stdout)
        self.assertIn('Write to hello@fixture.test.', (self.root / 'dist' / 'legal' / 'index.html').read_text(encoding='utf-8'))

    def test_another_empty_marker_is_not_an_error(self):
        ok, stdout, _ = self.build_page('<p>Based in {{location}}.</p>', city='', region='')
        self.assertTrue(ok, stdout)


if __name__ == '__main__':
    unittest.main()
