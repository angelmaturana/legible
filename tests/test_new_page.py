"""`new_page.py`, happy path: what it writes passes the strict build and the validator.

    python3 -B -m unittest tests.test_new_page
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_page_kit as kit  # noqa: E402

PLAIN = {
    'title': 'Prices and booking at Fixture Site', 'slug': 'prices-and-booking', 'short_title': 'Prices',
    'description': 'How booking works at Fixture Site, which prices apply and what to prepare before the visit, '
                   'in plain words.',
}


class _Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = kit.project(tmp.name)

    def make(self, data, *args):
        code, out, err = kit.run(self.root, data, *args)
        self.assertEqual(code, 0, err)
        return out

    def page_text(self, rel):
        return (self.root / 'src' / 'pages' / rel / 'index.html').read_text(encoding='utf-8')


class TestPageWithoutSection(_Base):
    def make_plain(self):
        data = kit.article(kind='page', section=None, **PLAIN)
        del data['section'], data['published']
        self.make(data)
        kit.link_from_home(self.root, '/prices-and-booking/', 'Prices')
        return data

    def test_passes_the_strict_validation_and_is_in_the_sitemap(self):
        self.make_plain()
        self.assertEqual(kit.strict_findings(self.root), ([], []))
        sitemap = (self.root / 'dist' / 'sitemap.xml').read_text(encoding='utf-8')
        self.assertIn('https://fixture.test/prices-and-booking/', sitemap)

    def test_a_page_has_no_article_data_and_the_date_is_the_run_date(self):
        self.make_plain()
        text = self.page_text('prices-and-booking')
        self.assertIn('updated: 2026-11-19', text)
        self.assertIn('"WebPage"', text)
        self.assertNotIn('"Article"', text)
        self.assertNotIn('<time', text)


class TestArticleInASection(_Base):
    def test_passes_the_strict_validation_with_the_three_json_ld_types(self):
        self.make(kit.article())
        self.assertEqual(kit.strict_findings(self.root), ([], []))
        graph = self.page_text('blog/choose-a-plumber').split('<script type="application/ld+json">')[1].split('</script>')[0]
        types = [node['@type'] for node in json.loads(graph)['@graph']]
        for kind in ('WebPage', 'Article', 'BreadcrumbList'):
            self.assertIn(kind, types)

    def test_the_title_is_the_title_plus_the_site_name_and_fits_the_range(self):
        self.make(kit.article())
        self.assertEqual(kit.strict_findings(self.root), ([], []))
        html = (self.root / 'dist' / 'blog' / 'choose-a-plumber' / 'index.html').read_text(encoding='utf-8')
        title = re.search(r'<title>(.*?)</title>', html).group(1)
        self.assertEqual(title, 'How to choose a plumber for your home | Fixture Site')
        self.assertTrue(kit.new_page.TITLE_RANGE[0] <= len(title) <= kit.new_page.TITLE_RANGE[1])

    def test_it_uses_only_css_classes_that_exist_in_the_base_stylesheet(self):
        self.make(kit.article())
        used = set()
        for value in re.findall(r'class="([^"]+)"', self.page_text('blog/choose-a-plumber')):
            used.update(value.split())
        css = (kit.REPO / 'src' / 'css' / 'site.css').read_text(encoding='utf-8')
        known = set(re.findall(r'\.([A-Za-z_][\w-]*)', css))
        self.assertTrue(used)
        self.assertEqual(sorted(used - known), [])


class TestFilesWritten(_Base):
    def test_a_second_run_with_the_same_slug_is_refused_and_changes_nothing(self):
        self.make(kit.article())
        before = kit.tree(self.root)
        code, _, err = kit.run(self.root, kit.article())
        self.assertEqual(code, 1)
        self.assertIn('already exists', err)
        self.assertIn('Nothing was written', err)
        self.assertEqual(kit.tree(self.root), before)

    def test_files_end_with_one_line_feed_have_no_carriage_return_and_leave_no_temp_file(self):
        self.make(kit.article())
        written = [self.root / 'src/pages/blog/choose-a-plumber/index.html', self.root / 'src/pages/blog/index.html']
        for path in written:
            data = path.read_bytes()
            self.assertTrue(data.endswith(b'\n') and not data.endswith(b'\n\n'), path.name)
            self.assertNotIn(b'\r', data)
        self.assertEqual(list((self.root / 'src').rglob('*.tmp')), [])

    def test_only_the_new_page_and_the_index_change(self):
        before = kit.tree(self.root)
        self.make(kit.article())
        after = kit.tree(self.root)
        changed = sorted(k for k in after if before.get(k) != after[k])
        self.assertEqual(changed, ['pages/blog/choose-a-plumber/index.html', 'pages/blog/index.html'])


if __name__ == '__main__':
    unittest.main()
