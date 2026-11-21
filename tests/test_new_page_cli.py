"""`new_page.py`, language, options, warnings and the command line.

    python3 -B -m unittest tests.test_new_page_cli
"""
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_page_kit as kit  # noqa: E402

SCRIPT = kit.REPO / 'legible' / 'new_page.py'


class _Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = kit.project(self.tmp)

    def site(self, **changes):
        path = self.root / 'src/data/site.json'
        data = {**json.loads(path.read_text(encoding='utf-8')), **changes}
        path.write_text(json.dumps(data), encoding='utf-8')

    def page(self, rel='blog/choose-a-plumber'):
        return (self.root / 'src/pages' / rel / 'index.html').read_text(encoding='utf-8')

    def unlink_from_home(self, url):
        home = self.root / 'src/pages/index.html'
        text = home.read_text(encoding='utf-8')
        home.write_text(re.sub(rf'<p><a href="{url}">[^<]*</a></p>', '', text), encoding='utf-8')

    def plain_page(self):
        data = kit.article(kind='page', section=None, slug='prices-and-booking',
                           title='Prices and booking at Fixture Site',
                           description='How booking works at Fixture Site, which prices apply and what to prepare before the '
                                       'visit, in plain words.')
        del data['section'], data['published']
        return data


class TestLanguage(_Base):
    def test_a_spanish_site_gets_spanish_texts(self):
        self.site(language='es')
        self.assertEqual(kit.run(self.root, kit.article())[0], 0)
        self.assertIn('Sigue leyendo', self.page())
        self.assertNotIn('Keep reading', self.page())
        self.assertEqual(kit.strict_findings(self.root), ([], []))
        html = (self.root / 'dist/blog/choose-a-plumber/index.html').read_text(encoding='utf-8')
        self.assertIn('<html lang="es"', html)
        self.assertIn('Inicio', html)
        self.assertIn('aria-label="Ruta de navegación"', html)

    def test_an_english_site_gets_english_texts(self):
        kit.run(self.root, kit.article())
        self.assertIn('Keep reading', self.page())

    def test_a_language_without_its_own_label_falls_back_to_english(self):
        self.site(language='de')
        self.assertEqual(kit.run(self.root, kit.article())[0], 0)
        self.assertIn('Keep reading', self.page())
        self.assertNotIn('Sigue leyendo', self.page())


class TestOptions(_Base):
    def test_dry_run_writes_nothing_and_reports_the_words(self):
        before = kit.tree(self.root)
        code, out, err = kit.run(self.root, kit.article(), '--dry-run')
        self.assertEqual((code, err), (0, ''))
        self.assertRegex(out, r'checks out \(~\d{3} words\)\. Nothing was written \(--dry-run\)')
        self.assertEqual(kit.tree(self.root), before)

    def test_dry_run_still_refuses_what_a_real_run_refuses(self):
        code, _, err = kit.run(self.root, kit.article(title='Hi'), '--dry-run')
        self.assertEqual(code, 1)
        self.assertIn('title (with the site name)', err)

    def test_date_sets_updated_in_the_page_and_in_the_index(self):
        self.assertEqual(kit.run(self.root, kit.article(), '--date', '2026-12-05')[0], 0)
        self.assertIn('updated: 2026-12-05', self.page())
        self.assertIn('updated: 2026-12-05', (self.root / 'src/pages/blog/index.html').read_text(encoding='utf-8'))
        self.assertIn('dateModified', self.page())

    def test_a_date_that_is_not_a_date_stops_with_code_2(self):
        before = kit.tree(self.root)
        for bad in ('2026-13-40', 'today', '19/11/2026'):
            with self.subTest(bad):
                code, _, err = kit.run(self.root, kit.article(), '--date', bad)
                self.assertEqual(code, 2)
                self.assertIn('--date must be written YYYY-MM-DD', err)
                self.assertEqual(kit.tree(self.root), before)

    def test_an_older_run_date_makes_an_already_published_article_a_future_one(self):
        code, _, err = kit.run(self.root, kit.article(), '--date', '2026-11-01')
        self.assertEqual(code, 1)
        self.assertIn('later than the update date', err)

    def test_root_chooses_the_project_and_touches_no_other(self):
        other = kit.project(self.tmp / 'other')
        before_other = kit.tree(other)
        self.assertEqual(kit.run(self.root, kit.article())[0], 0)
        self.assertEqual(kit.tree(other), before_other)
        self.assertTrue((self.root / 'src/pages/blog/choose-a-plumber/index.html').is_file())
        self.assertFalse((other / 'src/pages/blog/choose-a-plumber').exists())

    def test_the_template_is_a_json_that_loads_and_can_be_adjusted_into_a_valid_page(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(kit.new_page.main(['--template']), 0)
        data = json.loads(out.getvalue())
        for field in kit.new_page.REQUIRED:
            self.assertIn(field, data)
        data.update(blocks=[{'type': 'h2', 'text': 'First section'}, kit.words(300)],
                    related=[{'text': 'About us', 'url': '/about/'}])
        code, out, err = kit.run(self.root, data, '--dry-run')
        self.assertEqual(code, 0, err)
        self.assertIn('checks out', out)

    def test_without_the_json_file_it_says_how_to_run_it(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = kit.new_page.main(['--root', str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn('Missing the JSON file', err.getvalue())
        self.assertIn('Usage', err.getvalue())


class TestWarnings(_Base):
    def test_a_section_that_nobody_links_and_the_menu_lacks_is_reminded_but_not_blocked(self):
        self.unlink_from_home('/blog/')
        code, out, _ = kit.run(self.root, kit.article())
        self.assertEqual(code, 0)
        self.assertIn('⚠ /blog/ is not in the menu and no page links to it', out)
        self.assertTrue((self.root / 'src/pages/blog/choose-a-plumber/index.html').is_file())

    def test_no_reminder_when_the_menu_has_the_section(self):
        self.unlink_from_home('/blog/')
        nav = json.loads((self.root / 'src/data/site.json').read_text(encoding='utf-8'))['nav']
        self.site(nav=[*nav, {'label': 'Blog', 'url': '/blog/'}])
        code, out, _ = kit.run(self.root, kit.article())
        self.assertEqual(code, 0)
        self.assertNotIn('⚠', out)

    def test_no_reminder_when_a_page_links_to_the_section(self):
        code, out, _ = kit.run(self.root, kit.article())
        self.assertEqual(code, 0)
        self.assertNotIn('⚠', out)

    def test_a_loose_page_without_an_incoming_link_is_reminded(self):
        code, out, _ = kit.run(self.root, self.plain_page())
        self.assertEqual(code, 0)
        self.assertIn('⚠ no page links to /prices-and-booking/ yet', out)

    def test_a_loose_page_that_is_already_linked_is_not_reminded(self):
        kit.link_from_home(self.root, '/prices-and-booking/', 'Prices')
        code, out, _ = kit.run(self.root, self.plain_page())
        self.assertEqual(code, 0)
        self.assertNotIn('⚠', out)


class TestSiteData(_Base):
    def test_a_project_without_site_json_is_refused_with_a_clear_message(self):
        (self.root / 'src/data/site.json').unlink()
        before = kit.tree(self.root)
        code, _, err = kit.run(self.root, kit.article())
        self.assertEqual(code, 1)
        self.assertIn('cannot read src/data/site.json', err)
        self.assertNotIn('Traceback', err)
        self.assertEqual(kit.tree(self.root), before)

    def test_a_site_json_without_a_site_name_is_refused(self):
        (self.root / 'src/data/site.json').write_text('{"language": "en"}', encoding='utf-8')
        before = kit.tree(self.root)
        code, _, err = kit.run(self.root, kit.article())
        self.assertEqual(code, 1)
        self.assertIn('has no "site_name"', err)
        self.assertEqual(kit.tree(self.root), before)


class TestAsAScript(_Base):
    """The documented way to run it: `python3 -B -I legible/new_page.py ...`."""

    def run_script(self, *args):
        return subprocess.run([sys.executable, '-B', '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
                              check=False)

    def test_template_from_the_command_line(self):
        result = self.run_script('--template')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertIn('title', json.loads(result.stdout))

    def test_a_dry_run_from_the_command_line_on_another_project(self):
        source = self.tmp / 'page.json'
        source.write_text(json.dumps(kit.article()), encoding='utf-8')
        before = kit.tree(self.root)
        result = self.run_script(str(source), '--root', str(self.root), '--dry-run', '--date', kit.TODAY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Nothing was written', result.stdout)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(kit.tree(self.root), before)

    def test_an_error_from_the_command_line_is_a_message_and_not_a_traceback(self):
        source = self.tmp / 'page.json'
        source.write_text('[]', encoding='utf-8')
        result = self.run_script(str(source), '--root', str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn('must be an object', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
