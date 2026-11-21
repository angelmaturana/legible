"""`new_page.py`, everything it refuses: a clear message and not one file changed.

One table, one row per mistake. Each row changes one thing in a valid article and names a short, stable piece
of the message that must appear.

    python3 -B -m unittest tests.test_new_page_errors
"""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_page_kit as kit  # noqa: E402

REQUIRED = kit.new_page.REQUIRED


def edit(**changes):
    return lambda: kit.article(**changes)


def page_at_root(**changes):
    def make():
        data = kit.article(kind='page', section=None, **changes)
        del data['section'], data['published']
        return data
    return make


def with_blocks(*blocks):
    return edit(blocks=[{'type': 'h2', 'text': 'First'}, kit.words(300), *blocks])


def without(field):
    def make():
        data = kit.article()
        del data[field]
        return data
    return make


H2 = {'type': 'h2', 'text': 'First'}
ITEMS = [{'title': 'One', 'text': 'Text.'}, {'title': 'Two', 'text': 'Text.'}]
MARKER = 'build markers'

# (name, how to build the JSON, text that must appear in stderr, extra arguments)
ROWS = [
    # --- links
    ('broken internal link', with_blocks('See [this](/nope/).'), 'does not match any page', ()),
    ('internal link without the final slash', with_blocks('See [about](/about).'), 'must end with "/"', ()),
    ('http link', with_blocks('See [this](http://example.com/).'), 'must start with "/"', ()),
    ('link without a path', with_blocks('See [this](about/).'), 'must start with "/"', ()),
    ('button without url', with_blocks({'type': 'button', 'text': 'Go'}), 'empty link', ()),
    ('button without text', with_blocks({'type': 'button', 'url': '/about/'}), '"button" needs text', ()),
    ('related with a broken link', edit(related=[{'text': 'x', 'url': '/nope/'}]), 'does not match any page', ()),
    # --- structure
    ('first block is not an h2', edit(blocks=[kit.words(300)]), 'first block must be an "h2"', ()),
    ('unknown block type', with_blocks({'type': 'video', 'text': 'x'}), 'unknown type', ()),
    ('repeated heading', with_blocks(H2), 'repeated or reserved', ()),
    ('heading that would take the id of the related list', with_blocks({'type': 'h2', 'text': 'Related'}), 'repeated or reserved', ()),
    ('one card', with_blocks({'type': 'cards', 'items': ITEMS[:1]}), '"cards" takes 2 to 4 items', ()),
    ('five cards', with_blocks({'type': 'cards', 'items': ITEMS * 3}), '"cards" takes 2 to 4 items', ()),
    ('empty list', with_blocks({'type': 'ul', 'items': []}), 'at least one element', ()),
    ('no blocks', edit(blocks=[]), '"blocks" must be a list', ()),
    ('empty related', edit(related=[]), '"related" must be a list', ()),
    # --- lengths
    ('under 250 words', edit(blocks=[H2, kit.words(40)]), 'indexable pages need at least', ()),
    ('title too short', edit(title='Hi'), 'title (with the site name)', ()),
    ('title too long', edit(title='A title that is far too long for a search result ' * 2), 'title (with the site name)', ()),
    ('description too short', edit(description='Too short.'), 'description is', ()),
    ('description too long', edit(description='A description that never ends. ' * 8), 'description is', ()),
    # --- fields and dates
    ('unknown field', edit(colour='red'), 'unknown fields', ()),
    *[(f'missing "{f}"', without(f), f'missing required fields: {f}', ()) for f in REQUIRED],
    ('empty lead', edit(lead=' '), '"lead" must be a non-empty text', ()),
    ('line break in the title', edit(title='Two\nlines in one title'), 'cannot contain line breaks', ()),
    ('unknown kind', edit(kind='post'), '"kind" must be one of', ()),
    ('published with kind page', edit(kind='page'), 'only applies to "kind": "article"', ()),
    ('published in the future', edit(published='2026-12-01'), 'later than the update date', ()),
    ('published is not a date', edit(published='tomorrow'), 'YYYY-MM-DD', ()),
    ('published has an impossible date', edit(published='2026-02-30'), 'YYYY-MM-DD', ()),
    ('the page already exists', page_at_root(slug='about'), 'already exists', ()),
    # --- build markers (no text may carry one)
    ('"{{" in the title', edit(title='Guide {{site_name}} to pipes'), MARKER, ()),
    ('"}}" in the lead', edit(lead='A lead with }} in it'), MARKER, ()),
    ('"{{" in a paragraph', with_blocks('A paragraph with {{page_url}} inside.'), MARKER, ()),
    ('"{{" in a card', with_blocks({'type': 'cards', 'items': [{'title': '{{x}}', 'text': 'a'}, ITEMS[1]]}), MARKER, ()),
    ('"{{" in a list item', with_blocks({'type': 'ul', 'items': ['{{x}}']}), MARKER, ()),
    ('"{{" in a related link', edit(related=[{'text': '{{x}}', 'url': '/about/'}]), MARKER, ()),
    # --- paths (a slug or a section can never leave src/pages)
    ('slug with ../', edit(slug='../x'), '"slug"', ()),
    ('slug with a slash', edit(slug='a/b'), '"slug"', ()),
    ('slug in capitals', edit(slug='Index'), '"slug"', ()),
    ('slug "index"', edit(slug='index'), '"slug"', ()),
    ('slug "404"', edit(slug='404'), '"slug"', ()),
    ('empty slug', edit(slug=''), '"slug"', ()),
    ('slug with an accent', edit(slug='guía'), '"slug"', ()),
    ('section with a slash', edit(section='a/b'), '"section"', ()),
    ('section ".."', edit(section='..'), '"section"', ()),
    ('section in capitals', edit(section='Blog'), '"section"', ()),
    ('--section with a slash', edit(), '"--section" must be one folder name', ('--section', 'a/b')),
    ('--section with ..', edit(), '"--section" must be one folder name', ('--section', '..')),
    ('--section that has no index', edit(), 'has no index page', ('--section', 'news')),
    # --- the JSON itself
    ('JSON that is not an object', lambda: '[]', 'must be an object', ()),
    ('JSON that is not valid', lambda: '{"title": ', 'Cannot read the JSON', ()),
    ('empty file', lambda: '', 'Cannot read the JSON', ()),
]


class TestRefusals(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = kit.project(tmp.name)
        self.before = kit.tree(self.root)

    def test_every_row_stops_with_its_message_and_writes_nothing(self):
        for name, build, fragment, args in ROWS:
            with self.subTest(name):
                code, out, err = kit.run(self.root, build(), *args)
                self.assertEqual(code, 1, out + err)
                self.assertIn(fragment, err)
                if 'Cannot read' not in fragment:  # a file that cannot be read stops before any plan exists
                    self.assertIn('Nothing was written', err)
                self.assertNotIn('Traceback', err)
                self.assertEqual(kit.tree(self.root), self.before)
                self.assertEqual(list((self.root / 'src').rglob('*.tmp')), [])

    def test_the_table_does_not_lean_on_the_generic_message(self):
        for name, _, fragment, _ in ROWS:
            self.assertNotIn(fragment, ('the content has errors', 'the JSON has errors'), name)

    def test_a_json_file_that_does_not_exist_is_a_clear_message(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = kit.new_page.main([str(self.root / 'nothing.json'), '--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn('Cannot read the JSON', err.getvalue())
        self.assertNotIn('Traceback', err.getvalue())
        self.assertEqual(kit.tree(self.root), self.before)

    def test_an_identical_description_or_title_in_another_page_is_an_error_and_a_close_one_a_warning(self):
        self.assertEqual(kit.run(self.root, kit.numbered(0, '2026-11-10'))[0], 0)
        self.before = kit.tree(self.root)
        same = kit.numbered(1, '2026-11-11', description=kit.numbered(0, '2026-11-10')['description'])
        code, _, err = kit.run(self.root, same)
        self.assertEqual((code, 'the description is the same as the one in' in err), (1, True))
        self.assertEqual(kit.tree(self.root), self.before)
        close = kit.numbered(1, '2026-11-11', description=kit.numbered(0, '2026-11-10')['description'][:-1] + 's.')
        code, out, err = kit.run(self.root, close, '--dry-run')
        self.assertEqual(code, 0, err)
        self.assertIn('almost the same', out)
        self.assertEqual(kit.tree(self.root), self.before)


class TestEscaping(unittest.TestCase):
    TITLE = 'Pipes <b> & "taps" guide'

    def test_markup_characters_come_out_escaped_and_the_json_ld_stays_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = kit.project(tmp)
            data = kit.article(
                title=self.TITLE, short_title='Pipes <i> & "taps"', lead='A <lead> & "quote".',
                description='Why <i>pipes</i> & "taps" matter at home: the signs of trouble, what you can check yourself and '
                            'when to call.',
                blocks=[{'type': 'h2', 'text': 'A <h> & "q"'}, kit.words(300), {'type': 'cards', 'items': [
                    {'title': '<t1> & "x"', 'text': '<p>'}, {'title': 'Two', 'text': 'Text.'}]}])
            self.assertEqual(kit.run(root, data)[0], 0)
            self.assertEqual(kit.strict_findings(root), ([], []))
            html = (root / 'dist/blog/choose-a-plumber/index.html').read_text(encoding='utf-8')
            head, body = html.split('</title>')[0], html.split('<main')[1]
            self.assertNotIn('<b>', head)
            for raw in ('<b>', '<i>', '<lead>', '<h>', '<t1>'):
                self.assertNotIn(raw, body)
            self.assertIn('<h2 id="a-h-q">A &lt;h&gt; &amp; "q"</h2>', body)
            self.assertIn('<h3>&lt;t1&gt; &amp; "x"</h3>', body)
            self.assertIn('<p class="lead">A &lt;lead&gt; &amp; "quote".</p>', body)
            self.assertIn('content="Why &lt;i&gt;pipes&lt;/i&gt; &amp; &quot;taps&quot;', html)  # quotes matter inside attributes
            nodes = []
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
                nodes += json.loads(block)['@graph']
            self.assertEqual([n['headline'] for n in nodes if n['@type'] == 'Article'], [self.TITLE])
            crumbs = next(n for n in nodes if n['@type'] == 'BreadcrumbList')['itemListElement']
            self.assertEqual(crumbs[-1]['name'], 'Pipes <i> & "taps"')


if __name__ == '__main__':
    unittest.main()
