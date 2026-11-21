#!/usr/bin/env python3
"""legible: create a page (article, guide, post...) from a JSON file.

Standard library only. Run it from the project root:

    python3 -B -I legible/new_page.py page.json [--section blog] [--dry-run]
    python3 -B -I legible/new_page.py --template      # print an example JSON

What it does, and only that:
  1. writes src/pages/[<section>/]<slug>/index.html with the classes the base already has;
  2. with a section, adds the page to that section's index, between the markers
     `<!-- legible:list -->` and `<!-- /legible:list -->`, newest first.

What it does not do: touch the engine or the tests, overwrite anything, or write a single file when
something is wrong (everything is checked before the first write). It invents nothing: what the JSON
says is what gets published, so the facts must come from whoever writes the JSON.
"""
import argparse
import difflib
import html
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

SLUG = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*')
TITLE_RANGE, DESC_RANGE, MIN_WORDS = (20, 60), (70, 160), 250   # same limits as check_site.py
LIST_OPEN, LIST_CLOSE = '<!-- legible:list -->', '<!-- /legible:list -->'
KINDS = ('article', 'page')
RESERVED_SLUGS = ('index', '404')
REQUIRED = ('title', 'slug', 'description', 'lead', 'blocks', 'related')
OPTIONAL = ('section', 'eyebrow', 'kind', 'published', 'short_title')
RELATED_LABEL = {'en': 'Keep reading', 'es': 'Sigue leyendo'}
HOME_ICON = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 '
             '2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>')

SAMPLE = {
    'title': 'Title of the page', 'short_title': 'Short title for the breadcrumb', 'slug': 'title-of-the-page',
    'section': 'blog', 'kind': 'article', 'published': '2026-01-31', 'eyebrow': 'Guide',
    'description': 'One sentence of 70 to 160 characters, unique on the site, saying what the reader will get from the page.',
    'lead': 'One or two sentences under the title.',
    'blocks': [
        {'type': 'h2', 'text': 'First section'},
        'A string is a paragraph. It accepts **bold** and [links](/contact/).',
        {'type': 'h3', 'text': 'A subsection'},
        {'type': 'ul', 'items': ['First item', 'Second item']},
        {'type': 'ol', 'items': ['First step', 'Second step']},
        {'type': 'cards', 'items': [{'title': 'Card one', 'text': 'Short text.'}, {'title': 'Card two', 'text': 'Short text.'}]},
        {'type': 'note', 'text': 'A muted note.'},
        {'type': 'button', 'text': 'Contact us', 'url': '/contact/'},
    ],
    'related': [{'text': 'Contact', 'url': '/contact/'}],
}


class Problem(Exception):
    """A condition that stops the run before anything is written."""


class Ctx:
    def __init__(self, root, today, site):
        self.root, self.today, self.site = Path(root), today, site
        self.errors, self.warnings = [], []
        self.pages = self.root / 'src' / 'pages'

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


# ---------------------------------------------------------------- text and links

def norm(text):
    text = unicodedata.normalize('NFD', str(text))
    return ''.join(c for c in text if not unicodedata.combining(c)).lower().strip()


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', norm(text)).strip('-')


def esc(text):
    return html.escape(str(text), quote=False)


def esc_attr(text):
    return html.escape(str(text), quote=True)


def is_text(value):
    return isinstance(value, str) and bool(value.strip())


def page_exists(ctx, path):
    rel = path.strip('/')
    if not rel:
        return (ctx.pages / 'index.html').is_file()
    return (ctx.pages / rel / 'index.html').is_file() or (ctx.pages / (rel + '.html')).is_file()


def check_url(ctx, url, where):
    """An internal link must exist and end in "/" (or be a static file); an external one must be https."""
    if not is_text(url):
        ctx.err(f'{where}: empty link')
    elif url.startswith(('https://', '#')):
        return
    elif not url.startswith('/') or url.startswith('//'):
        ctx.err(f'{where}: the link {url} must start with "/" (internal) or "https://" (external)')
    else:
        path = url.split('#', 1)[0].split('?', 1)[0]
        if (ctx.root / 'src' / 'static' / path.strip('/')).is_file() and not path.endswith('/'):
            return
        if not page_exists(ctx, path):
            ctx.err(f'{where}: the internal link {url} does not match any page in src/pages')
        elif not path.endswith('/'):
            ctx.err(f'{where}: the internal link {url} must end with "/"')


_INLINE = re.compile(r'\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)')


def inline(ctx, text, where):
    """**bold** and [label](url) become HTML; everything else is escaped as written."""
    if not is_text(text):
        ctx.err(f'{where}: empty text, or not a text')
        return ''
    out, pos = [], 0
    for m in _INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(f'<strong>{esc(m.group(1))}</strong>')
        else:
            url = m.group(3)
            check_url(ctx, url, where)
            extra = ' target="_blank" rel="noopener"' if url.startswith('https://') else ''
            out.append(f'<a href="{esc_attr(url)}"{extra}>{esc(m.group(2))}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return ''.join(out)


# ---------------------------------------------------------------- blocks

def _items(ctx, block, where, fields=()):
    items = block.get('items')
    if not isinstance(items, list) or not items:
        ctx.err(f'{where}: "items" must be a list with at least one element')
        return []
    for i, it in enumerate(items, 1):
        if fields and not (isinstance(it, dict) and all(is_text(it.get(f)) for f in fields)):
            ctx.err(f'{where}: item {i} needs {", ".join(fields)}')
            return []
    return items


def b_text(tag, css=''):
    def render(ctx, b, where):
        return f'<{tag}{css}>{inline(ctx, b.get("text"), where)}</{tag}>'
    return render


def b_list(tag):
    def render(ctx, b, where):
        lis = ''.join(f'<li>{inline(ctx, t, where)}</li>' for t in _items(ctx, b, where))
        return f'<{tag}>{lis}</{tag}>'
    return render


def b_cards(ctx, b, where):
    items = _items(ctx, b, where, ('title', 'text'))
    if items and not 2 <= len(items) <= 4:
        ctx.err(f'{where}: "cards" takes 2 to 4 items')
    cards = ''.join(f'<article class="card"><h3>{inline(ctx, i["title"], where)}</h3><p>{inline(ctx, i["text"], where)}</p></article>'
                    for i in items)
    return f'<div class="card-grid">{cards}</div>'


def b_button(ctx, b, where):
    url = b.get('url')
    check_url(ctx, url, where)
    extra = ' target="_blank" rel="noopener"' if is_text(url) and url.startswith('https://') else ''
    if not is_text(b.get('text')):
        ctx.err(f'{where}: "button" needs text')
    return (f'<div class="actions"><a class="button primary" href="{esc_attr(url or "")}"{extra}>'
            f'{esc(b.get("text") or "")}</a></div>')


BLOCKS = {'p': b_text('p'), 'h3': b_text('h3'), 'note': b_text('p', ' class="page-note"'),
          'ul': b_list('ul'), 'ol': b_list('ol'), 'cards': b_cards, 'button': b_button}


def render_body(ctx, blocks):
    """Group the blocks under their h2: one <section> each. Returns the list of sections."""
    if not isinstance(blocks, list) or not blocks:
        ctx.err('"blocks" must be a list with at least one block')
        return []
    sections, seen = [], {'related'}
    for n, block in enumerate(blocks, 1):
        where = f'block {n}'
        block = {'type': 'p', 'text': block} if isinstance(block, str) else block
        kind = block.get('type') if isinstance(block, dict) else None
        if kind == 'h2':
            sid = slugify(block.get('text', '')) or f'section-{n}'
            if sid in seen:
                ctx.err(f'{where}: the heading id "{sid}" is repeated or reserved; change the heading')
            seen.add(sid)
            sections.append([sid, f'<h2 id="{esc_attr(sid)}">{inline(ctx, block.get("text"), where)}</h2>'])
        elif kind not in BLOCKS:
            ctx.err(f'{where}: unknown type (valid: h2, {", ".join(BLOCKS)})')
        elif not sections:
            ctx.err(f'{where}: the first block must be an "h2" (headings may not skip a level)')
        else:
            sections[-1].append(BLOCKS[kind](ctx, block, where))
    return [f'<section class="section page-width" aria-labelledby="{sid}">\n  ' + '\n  '.join(parts) + '\n </section>'
            for sid, *parts in sections]


# ---------------------------------------------------------------- JSON and checks

def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _check_fields(ctx, data):
    for k in ('title', 'slug', 'description', 'lead'):
        if not is_text(data[k]):
            ctx.err(f'"{k}" must be a non-empty text')
    for k in ('title', 'slug', 'description', 'lead', 'eyebrow', 'short_title', 'section', 'kind', 'published'):
        if isinstance(data.get(k), str) and ('\n' in data[k] or '\r' in data[k]):
            ctx.err(f'"{k}" cannot contain line breaks')
    if any('{{' in s or '}}' in s for s in _strings(data)):
        ctx.err('no text may contain "{{" or "}}" (they are build markers)')
    if not isinstance(data['related'], list) or not data['related']:
        ctx.err('"related" must be a list with at least one internal link')


def _check_values(ctx, data):
    slug, section = data['slug'], data.get('section')
    if is_text(slug) and (not SLUG.fullmatch(slug) or slug in RESERVED_SLUGS):
        ctx.err('"slug": lowercase letters without accents, digits and hyphens only; not "index" or "404"')
    if section is not None and not (isinstance(section, str) and SLUG.fullmatch(section)):
        ctx.err('"section": one folder name in lowercase letters, digits and hyphens (for example "blog")')
    if data.get('kind', 'page') not in KINDS:
        ctx.err('"kind" must be one of: ' + ', '.join(KINDS))
    if 'published' in data and data.get('kind') != 'article':
        ctx.err('"published" only applies to "kind": "article"')


def validate(ctx, data):
    if not isinstance(data, dict):
        raise Problem('the JSON must be an object')
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise Problem('missing required fields: ' + ', '.join(missing))
    unknown = [k for k in data if k not in REQUIRED and k not in OPTIONAL]
    if unknown:
        ctx.err('unknown fields (typo?): ' + ', '.join(unknown))
    _check_fields(ctx, data)
    _check_values(ctx, data)
    if ctx.errors:
        raise Problem('the JSON has errors')


def parse_date(ctx, text, name):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        ctx.err(f'{name} must be a date written YYYY-MM-DD')
        return ctx.today


def check_length(ctx, data):
    title = f'{data["title"]} | {ctx.site["site_name"]}'
    desc = data['description']
    for what, n, (lo, hi) in (('title (with the site name)', len(title), TITLE_RANGE), ('description', len(desc), DESC_RANGE)):
        if not lo <= n <= hi:
            ctx.err(f'the {what} is {n} characters long; it must be {lo}-{hi}')


def _squash(text):
    return re.sub(r'[^a-z0-9]+', ' ', norm(text)).strip()


def _front(path):
    out = {}
    for line in path.read_text(encoding='utf-8')[:3000].splitlines()[1:12]:
        key, _, val = line.partition(':')
        if key in ('title', 'description'):
            out[key] = _squash(val)
        if line.strip() == '---':
            break
    return out


def check_duplicates(ctx, data):
    mine = {'title': _squash(data['title']) + ' site name', 'description': _squash(data['description'])}
    for path in sorted(ctx.pages.rglob('*.html')):
        where = path.relative_to(ctx.root).as_posix()
        for key, other in _front(path).items():
            ratio = difflib.SequenceMatcher(None, mine[key], other).ratio()
            if ratio == 1:
                ctx.err(f'the {key} is the same as the one in {where}: every page needs its own')
            elif ratio >= 0.9:
                ctx.warn(f'the {key} is almost the same as the one in {where}: one page per real topic')


# ---------------------------------------------------------------- page and index

def section_label(ctx, section):
    """Name of the section for the breadcrumb: the h1 of its index page."""
    path = ctx.pages / section / 'index.html'
    if not path.is_file():
        raise Problem(f'the section "{section}" has no index page. Create src/pages/{section}/index.html (copy src/pages/example/) '
                      f'and put {LIST_OPEN} and {LIST_CLOSE} inside a <div class="card-grid"> in its <main>')
    text = path.read_text(encoding='utf-8')
    if LIST_OPEN not in text or text.find(LIST_CLOSE) < text.find(LIST_OPEN):
        raise Problem(f'src/pages/{section}/index.html lacks the markers {LIST_OPEN} ... {LIST_CLOSE}')
    m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S)
    return html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else section


def json_ld(d, m):
    me, site = {'@id': '{{site_url}}/#business'}, {'@id': '{{site_url}}/#website'}
    graph = [{'@type': 'WebPage', '@id': '{{page_url}}#webpage', 'url': '{{page_url}}', 'name': '{{page_title}}',
              'description': '{{page_description}}', 'inLanguage': '{{in_language}}', 'isPartOf': site, 'about': me,
              'dateModified': '{{page_updated}}', 'breadcrumb': {'@id': '{{page_url}}#breadcrumb'}}]
    if d.get('kind') == 'article':
        graph.append({'@type': 'Article', '@id': '{{page_url}}#article', 'headline': d['title'], 'description': d['description'],
                      'inLanguage': '{{in_language}}', 'datePublished': m['published'], 'dateModified': '{{page_updated}}',
                      'mainEntityOfPage': {'@id': '{{page_url}}#webpage'}, 'author': me, 'publisher': me})
    crumbs = [('{{ui_home}}', '{{site_url}}/')] + ([(m['label'], '{{site_url}}/' + m['section'] + '/')] if m['section'] else [])
    items = [{'@type': 'ListItem', 'position': n, 'name': name, 'item': item} for n, (name, item) in enumerate(crumbs, 1)]
    items.append({'@type': 'ListItem', 'position': len(items) + 1, 'name': d.get('short_title') or d['title']})
    graph.append({'@type': 'BreadcrumbList', '@id': '{{page_url}}#breadcrumb', 'itemListElement': items})
    text = json.dumps({'@context': 'https://schema.org', '@graph': graph}, indent=4, ensure_ascii=False)
    return '<script type="application/ld+json">\n' + text.replace('<', '\\u003c') + '\n</script>'


def render_related(ctx, items):
    lis = []
    for i, r in enumerate(items, 1):
        where = f'related {i}'
        if not (isinstance(r, dict) and is_text(r.get('text')) and is_text(r.get('url'))):
            ctx.err(f'{where}: needs "text" and "url"')
            continue
        if r['url'].startswith('/'):
            check_url(ctx, r['url'], where)
        else:
            ctx.err(f'{where}: {r["url"]} must be an internal link (start with "/")')
        lis.append(f'<li><a href="{esc_attr(r["url"])}">{esc(r["text"])}</a></li>')
    return lis


def render_main(ctx, d, m, sections):
    crumbs = ['<li><a href="/">' + HOME_ICON + '{{ui_home}}</a></li>']
    if m['section']:
        crumbs.append(f'<li><a href="/{m["section"]}/">{esc(m["label"])}</a></li>')
    crumbs.append(f'<li><span>{esc(d.get("short_title") or d["title"])}</span></li>')
    eyebrow = d.get('eyebrow') or m['label']
    when = f'\n  <p class="page-note"><time datetime="{m["published"]}">{m["published"]}</time></p>' if d.get('kind') == 'article' else ''
    related = render_related(ctx, d['related'])
    label = RELATED_LABEL.get(ctx.site.get('language'), RELATED_LABEL['en'])
    head = ('<section class="inner-hero page-width">\n  <nav class="breadcrumb" aria-label="{{ui_breadcrumb_label}}"><ol>'
            + ''.join(crumbs) + '</ol></nav>\n  ' + (f'<p class="eyebrow">{esc(eyebrow)}</p>\n  ' if eyebrow else '')
            + f'<h1>{esc(d["title"])}</h1>\n  <p class="lead">{inline(ctx, d["lead"], "lead")}</p>{when}\n </section>')
    tail = (f'<section class="section page-width" aria-labelledby="related">\n  <h2 id="related">{esc(label)}</h2>\n  <ul>'
            + ''.join(related) + '</ul>\n </section>')
    return '<main id="main">\n ' + '\n '.join([head] + sections + [tail]) + '\n</main>\n'


def build_page(ctx, d, m):
    sections = render_body(ctx, d['blocks'])
    main = render_main(ctx, d, m, sections)
    words = len(re.sub(r'<[^>]+>', ' ', main).split())
    if words < MIN_WORDS:
        ctx.err(f'the page has about {words} words in <main>; indexable pages need at least {MIN_WORDS}')
    front = ('---\ntitle: ' + d['title'] + ' | {{site_name}}\ndescription: ' + d['description']
             + f'\nupdated: {ctx.today.isoformat()}\n---\n\n')
    return front + json_ld(d, m) + '\n\n' + main, words


def update_index(ctx, d, m, url):
    """Insert the page in the index of its section, newest first. Returns (path, new text)."""
    path = ctx.pages / m['section'] / 'index.html'
    text = path.read_text(encoding='utf-8')
    start = text.find(LIST_OPEN) + len(LIST_OPEN)
    end = text.find(LIST_CLOSE)
    lines = [ln for ln in text[start:end].split('\n') if ln.strip()]
    if any(f'href="{url}"' in ln for ln in lines):
        ctx.warn(f'the index of "{m["section"]}" already lists {url}; it is left as it was')
        return path, text
    entry = (f'<article class="card"><h3><a href="{esc_attr(url)}">{esc(d["title"])}</a></h3><p>{esc(d["description"])}</p>'
             f'<p class="page-note"><time datetime="{m["date"]}">{m["date"]}</time></p></article>')
    pos = len(lines)
    for n, ln in enumerate(lines):
        found = re.search(r'datetime="([0-9-]*)"', ln)
        if (found.group(1) if found else '') <= m['date']:
            pos = n
            break
    lines.insert(pos, entry)
    new = text[:start] + '\n' + '\n'.join(lines) + '\n' + text[end:]
    return path, re.sub(r'(?m)^updated: .*$', f'updated: {ctx.today.isoformat()}', new, count=1)


def _nav_urls(nav):
    for entry in nav if isinstance(nav, list) else []:
        if isinstance(entry, dict):
            yield entry.get('url')
            yield from _nav_urls(entry.get('children'))


def linked_from_a_page(ctx, url):
    needle = f'href="{url}"'
    return any(needle in p.read_text(encoding='utf-8') for p in ctx.pages.rglob('*.html'))


def reminders(ctx, url, section):
    """What is left to do by hand, so that the strict validator does not warn about orphan pages."""
    todo = []
    if section:
        index = f'/{section}/'
        if index not in set(_nav_urls(ctx.site.get('nav'))) and not linked_from_a_page(ctx, index):
            todo.append(f'{index} is not in the menu and no page links to it: add it to "nav" in src/data/site.json or link it from a page')
    elif not linked_from_a_page(ctx, url):
        todo.append(f'no page links to {url} yet: link it from the <main> of another page')
    return todo


# ---------------------------------------------------------------- program

def read_site(root):
    try:
        site = json.loads((Path(root) / 'src' / 'data' / 'site.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise Problem(f'cannot read src/data/site.json: {exc}') from None
    if not isinstance(site, dict) or not is_text(site.get('site_name')):
        raise Problem('src/data/site.json has no "site_name"')
    return site


def page_meta(ctx, data):
    """Section name, breadcrumb label and dates of the page. Raises Problem if the section is unusable."""
    section = data.get('section')
    published = None
    if data.get('kind') == 'article':
        published = parse_date(ctx, data.get('published', ctx.today.isoformat()), '"published"')
        if published > ctx.today:
            ctx.err('"published" is later than the update date')
    day = (published or ctx.today).isoformat()
    return {'section': section, 'label': section_label(ctx, section) if section else '',
            'published': day if published else '', 'date': day}


def plan(ctx, data, section_arg):
    """Check everything and return [(path, text)], the words and the URL. Writes nothing."""
    validate(ctx, data)
    if section_arg:
        if not SLUG.fullmatch(section_arg):
            raise Problem('"--section" must be one folder name in lowercase letters, digits and hyphens')
        data['section'] = section_arg
    section = data.get('section')
    rel = f'{section}/{data["slug"]}' if section else data['slug']
    url, target = f'/{rel}/', ctx.pages / rel / 'index.html'
    if target.parent.exists():
        raise Problem(f'{url} already exists ({target.relative_to(ctx.root).as_posix()}): nothing is overwritten. Choose another slug')
    meta = page_meta(ctx, data)
    check_length(ctx, data)
    check_duplicates(ctx, data)
    page, words = build_page(ctx, data, meta)
    writes = [(target, page)] + ([update_index(ctx, data, meta, url)] if section else [])
    if ctx.errors:
        raise Problem('the content has errors')
    return writes, words, url


class Incomplete(OSError):
    """A write failed and some change could not be undone."""


def undo(done, temps, made):
    """Restore the renamed files, drop the temporary ones and the folders commit created. Returns what failed."""
    stuck = []
    for path, old in reversed(done):
        try:
            path.unlink(missing_ok=True) if old is None else path.write_bytes(old)
        except OSError:
            stuck.append(str(path))
    for tmp, _ in temps:
        tmp.unlink(missing_ok=True)
    for folder in reversed(made):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    return stuck


def commit(writes):
    """Write every file next to its place first, then rename them all; a failure undoes what was done."""
    temps, made, done = [], [], []
    try:
        for path, text in writes:
            if not path.parent.exists():
                made.append(path.parent)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + '.tmp')
            tmp.write_text(text, encoding='utf-8', newline='\n')
            temps.append((tmp, path))
        for tmp, path in temps:
            old = path.read_bytes() if path.exists() else None
            os.replace(tmp, path)
            done.append((path, old))
    except OSError as exc:
        stuck = undo(done, temps, made)
        if stuck:
            raise Incomplete(f'{exc}; could not restore {", ".join(stuck)}') from exc
        raise


def parse_args(argv):
    p = argparse.ArgumentParser(prog='new_page.py', description='Create a page from a JSON file.')
    p.add_argument('json', nargs='?', help='path of the JSON file')
    p.add_argument('--section', help='section folder under src/pages (overrides "section" in the JSON)')
    p.add_argument('--dry-run', action='store_true', help='check and count words without writing anything')
    p.add_argument('--template', action='store_true', help='print an example JSON')
    p.add_argument('--date', help='update date YYYY-MM-DD (default: today)')
    p.add_argument('--root', help='project root (default: the folder that holds legible/)')
    return p.parse_args(argv)


def execute(args, today):
    """Plan, report and (unless --dry-run) write. Returns the exit code."""
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    ctx = Ctx(root, today, {})
    try:
        ctx.site = read_site(root)
        data = json.loads(Path(args.json).read_text(encoding='utf-8'))
        writes, words, url = plan(ctx, data, args.section.strip() if args.section else None)
    except (OSError, ValueError) as exc:
        print(f'✗ Cannot read the JSON: {exc}', file=sys.stderr)
        return 1
    except Problem as exc:
        print(f'✗ {str(exc).rstrip(".")}. Nothing was written.', file=sys.stderr)
        for e in ctx.errors:
            print(f'  - {e}', file=sys.stderr)
        return 1
    for w in ctx.warnings + reminders(ctx, url, data.get('section')):
        print(f'⚠ {w}')
    if args.dry_run:
        print(f'✓ {url} checks out (~{words} words). Nothing was written (--dry-run).')
        return 0
    try:
        commit(writes)
    except OSError as exc:
        left = 'Check the files named above' if isinstance(exc, Incomplete) else 'Nothing was left behind'
        print(f'✗ Could not write the files ({exc}). {left}.', file=sys.stderr)
        return 1
    for path, _ in writes:
        print(f'  wrote {path.relative_to(ctx.root).as_posix()}')
    print(f'✓ Page created: {url} (~{words} words). Now run: python3 legible/build.py --all')
    return 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.template:
        print(json.dumps(SAMPLE, indent=2, ensure_ascii=False))
        return 0
    if not args.json:
        print('Missing the JSON file. Usage: python3 -B -I legible/new_page.py page.json', file=sys.stderr)
        return 2
    try:
        today = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        print('--date must be written YYYY-MM-DD', file=sys.stderr)
        return 2
    return execute(args, today)


if __name__ == '__main__':
    sys.exit(main())
