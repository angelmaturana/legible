"""Helpers shared by the tests of `legible/new_page.py` (no tests here).

They build on `fixtures.make_clean_project` and add what it lacks: a section index with the list markers.
"""
import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'legible'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import check_site  # noqa: E402
import fixtures  # noqa: E402
import new_page  # noqa: E402

TODAY = '2026-11-19'
_SENTENCE = ('This sentence is plain filler text with no claim in it, and it only exists so that the page has '
             'enough words in the main area to count as real content. ')


def words(count):
    """About `count` words of harmless filler, as one paragraph."""
    return (_SENTENCE * (count // 24 + 1)).strip()


def _write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def project(tmp):
    """A clean project plus `src/pages/blog/index.html` linked from the home. The index needs what any indexable page
    needs: JSON-LD, over 250 words and an h2 before the cards (they are h3)."""
    root = fixtures.make_clean_project(Path(tmp) / 'site')
    index = (f'---\ntitle: Blog of Fixture Site with guides and news\ndescription: {words(14)[:90]} Guides and news of '
             f'Fixture Site.\nupdated: 2026-01-01\n---\n{fixtures.CLEAN_WEBPAGE_JSONLD}<main id="main"><h1>Blog</h1>'
             f'<p>{words(300)}</p>\n<h2>Latest articles</h2>\n{new_page.LIST_OPEN}\n{new_page.LIST_CLOSE}\n</main>\n')
    _write(root, 'src/pages/blog/index.html', index)
    link_from_home(root, '/blog/', 'Blog')
    return root


def link_from_home(root, url, label):
    """Add a contextual link to the <main> of the home page (a page nobody links to is an orphan)."""
    home = Path(root) / 'src' / 'pages' / 'index.html'
    text = home.read_text(encoding='utf-8')
    home.write_text(text.replace('</main>', f'<p><a href="{url}">{label}</a></p></main>', 1), encoding='utf-8', newline='\n')


def article(**changes):
    """A valid article for the `blog` section (about 300 words); `changes` replace fields."""
    data = copy.deepcopy(new_page.SAMPLE)
    data.update(
        title='How to choose a plumber for your home', slug='choose-a-plumber', section='blog', kind='article',
        published='2026-11-10', eyebrow='Guide', lead='What to ask before you hire someone to fix the pipes.',
        description='A plain guide to choosing a plumber: what to ask, what to compare and what to check before '
                    'you agree to any work.',
        blocks=[{'type': 'h2', 'text': 'Before you call'}, words(150), {'type': 'ul', 'items': ['Ask', 'Compare']},
                {'type': 'h2', 'text': 'After the visit'}, words(150)],
        related=[{'text': 'About us', 'url': '/about/'}])
    data.update(changes)
    return data


def run(root, data, *args):
    """Run `new_page.main` on `data` (a dict, or a ready string) inside `root`. Returns (code, stdout, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'page.json'
        source.write_text(data if isinstance(data, str) else json.dumps(data), encoding='utf-8')
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = new_page.main([str(source), '--root', str(root), '--date', TODAY, *args])
    return code, out.getvalue(), err.getvalue()


def tree(root):
    """{relative path: md5} of every file under `src/`, to compare before and after a run."""
    src = Path(root) / 'src'
    return {p.relative_to(src).as_posix(): hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(src.rglob('*')) if p.is_file()}


def strict_findings(root):
    """Strict build, then the validator on `dist/`. Returns (errors, warnings); both empty = clean."""
    with contextlib.redirect_stdout(io.StringIO()):
        ok = build.build(Path(root), strict=True)
    if not ok:
        return [('build', 'the strict build failed')], []
    return check_site.run_checks(Path(root) / 'dist', fixtures.CLEAN_SITE_URL)


def numbered(n, published, **changes):
    """Article number `n` of a series: its own slug, title, description and text, so none counts as a duplicate."""
    topic = ('pipes', 'boilers', 'taps', 'drains', 'valves')[n]
    body = ' '.join(f'{topic}{j} and {topic[::-1]}{j * 7}' for j in range(70))
    fields = {
        'slug': f'{topic}-guide', 'title': f'A short guide to {topic} at home', 'published': published,
        'description': f'What to know about {topic} at home: the signs of trouble, what you can check yourself and when '
                       f'to call a professional.',
        'blocks': [{'type': 'h2', 'text': f'About {topic}'}, body, {'type': 'h2', 'text': 'Next steps'}, body[::-1]]}
    fields.update(changes)
    return article(**fields)
