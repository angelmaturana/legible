"""`new_page.py`, section index and atomic writing.

    python3 -B -m unittest tests.test_new_page_index
"""
import datetime
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_page_kit as kit  # noqa: E402

new_page = kit.new_page
INDEX = 'src/pages/blog/index.html'


class _Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = kit.project(tmp.name)
        self.before = kit.tree(self.root)

    def index_text(self):
        return (self.root / INDEX).read_text(encoding='utf-8')

    def listed(self):
        return re.findall(r'<a href="(/blog/[^"]+)"', self.index_text())

    def refused(self, data, *fragments):
        code, _, err = kit.run(self.root, data)
        self.assertEqual(code, 1, err)
        for fragment in fragments:
            self.assertIn(fragment, err)
        self.assertNotIn('Traceback', err)
        self.assertEqual(kit.tree(self.root), self.before)


class TestIndexContent(_Base):
    def test_the_cards_are_listed_from_the_newest_to_the_oldest_whatever_the_creation_order(self):
        for n, published in ((0, '2026-11-10'), (1, '2026-11-15'), (2, '2026-10-01')):
            self.assertEqual(kit.run(self.root, kit.numbered(n, published))[0], 0)
        self.assertEqual(self.listed(), ['/blog/boilers-guide/', '/blog/pipes-guide/', '/blog/taps-guide/'])
        self.assertEqual(kit.strict_findings(self.root), ([], []))

    def test_a_link_already_in_the_list_is_not_added_again(self):
        ctx = new_page.Ctx(self.root, datetime.date(2026, 11, 19), new_page.read_site(self.root))
        data, meta = kit.numbered(0, '2026-11-10'), {'section': 'blog', 'date': '2026-11-10'}
        _, first = new_page.update_index(ctx, data, meta, '/blog/pipes-guide/')
        (self.root / INDEX).write_text(first, encoding='utf-8')
        _, second = new_page.update_index(ctx, data, meta, '/blog/pipes-guide/')
        self.assertEqual(second, first)
        self.assertEqual(first.count('href="/blog/pipes-guide/"'), 1)
        self.assertTrue(any('already lists' in w for w in ctx.warnings))

    def test_updated_of_the_index_becomes_the_run_date_and_the_rest_of_the_index_is_kept(self):
        old = self.index_text()
        self.assertIn('updated: 2026-01-01', old)
        kit.run(self.root, kit.numbered(0, '2026-11-10'))
        new = self.index_text()
        self.assertIn('updated: 2026-11-19', new)
        self.assertNotIn('2026-01-01', new)
        self.assertEqual(new.split(new_page.LIST_OPEN)[0].replace('2026-11-19', '2026-01-01'), old.split(new_page.LIST_OPEN)[0])


class TestIndexProblems(_Base):
    def test_a_section_without_an_index_page_says_what_to_create(self):
        (self.root / INDEX).unlink()
        self.before = kit.tree(self.root)
        self.refused(kit.numbered(0, '2026-11-10'), 'has no index page', 'src/pages/blog/index.html', new_page.LIST_OPEN)

    def test_an_index_without_the_markers_is_refused(self):
        text = self.index_text()
        cases = {'none': text.replace(new_page.LIST_OPEN, '').replace(new_page.LIST_CLOSE, ''),
                 'only the opening one': text.replace(new_page.LIST_CLOSE, ''),
                 'only the closing one': text.replace(new_page.LIST_OPEN, '')}
        for name, broken in cases.items():
            with self.subTest(name):
                (self.root / INDEX).write_text(broken, encoding='utf-8')
                self.before = kit.tree(self.root)
                self.refused(kit.numbered(0, '2026-11-10'), 'lacks the markers')

    def test_markers_in_the_wrong_order_are_refused(self):
        swapped = self.index_text().replace(new_page.LIST_OPEN, '@@').replace(new_page.LIST_CLOSE, new_page.LIST_OPEN)
        (self.root / INDEX).write_text(swapped.replace('@@', new_page.LIST_CLOSE), encoding='utf-8')
        self.before = kit.tree(self.root)
        self.refused(kit.numbered(0, '2026-11-10'), 'lacks the markers')

    def test_repeated_markers_use_only_the_first_pair(self):
        extra = f'{new_page.LIST_OPEN}\n{new_page.LIST_CLOSE}\n'
        (self.root / INDEX).write_text(self.index_text().replace('</main>', extra + '</main>'), encoding='utf-8')
        self.assertEqual(kit.run(self.root, kit.numbered(0, '2026-11-10'))[0], 0)
        first, second = self.index_text().split(new_page.LIST_CLOSE)[:2]
        self.assertIn('/blog/pipes-guide/', first)
        self.assertNotIn('/blog/pipes-guide/', second)


class TestAtomicWriting(_Base):
    def fail_rename(self, number):
        """`os.replace` really works except the `number`-th call, which raises."""
        real, calls = os.replace, []

        def replace(source, target):
            calls.append(target)
            if len(calls) == number:
                raise OSError('simulated failure')
            return real(source, target)
        return mock.patch.object(new_page.os, 'replace', replace)

    def leftovers(self):
        return sorted(set(kit.tree(self.root)) - set(self.before)), list((self.root / 'src').rglob('*.tmp'))

    def test_a_failure_on_the_first_rename_leaves_nothing_behind(self):
        with self.fail_rename(1):
            code, _, err = kit.run(self.root, kit.numbered(0, '2026-11-10'))
        self.assertEqual(code, 1)
        self.assertIn('Could not write', err)
        self.assertEqual(self.leftovers(), ([], []))
        self.assertEqual(kit.tree(self.root), self.before)
        self.assertFalse((self.root / 'src/pages/blog/pipes-guide').exists())

    def test_a_failure_on_the_second_rename_leaves_nothing_behind(self):
        """Found in phase 2B, fixed in phase 4: the first rename is undone, so no page is left without its card."""
        with self.fail_rename(2):
            code, _, _ = kit.run(self.root, kit.numbered(0, '2026-11-10'))
        self.assertEqual(code, 1)
        self.assertEqual(self.leftovers(), ([], []))
        self.assertEqual(kit.tree(self.root), self.before)

    def test_an_undo_that_fails_is_reported_instead_of_claiming_a_clean_state(self):
        real = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == 'index.html' and path.parent.name == 'pipes-guide':
                raise OSError('locked')
            return real(path, *args, **kwargs)
        with self.fail_rename(2), mock.patch.object(Path, 'unlink', unlink):
            code, _, err = kit.run(self.root, kit.numbered(0, '2026-11-10'))
        self.assertEqual(code, 1)
        self.assertIn('could not restore', err)
        self.assertNotIn('Nothing was left behind', err)

    def test_a_failure_while_writing_the_temporary_file_of_the_index_leaves_nothing_behind(self):
        real, calls = Path.write_text, []

        def write_text(path, *args, **kwargs):
            if path.name.endswith('.tmp'):
                calls.append(path)
                if len(calls) == 2:
                    raise OSError('simulated disk full')
            return real(path, *args, **kwargs)
        with mock.patch.object(Path, 'write_text', write_text):
            code, _, err = kit.run(self.root, kit.numbered(0, '2026-11-10'))
        self.assertEqual(code, 1)
        self.assertIn('Could not write', err)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.leftovers(), ([], []))
        self.assertEqual(kit.tree(self.root), self.before)


if __name__ == '__main__':
    unittest.main()
