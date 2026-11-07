"""Fixtures for the engine tests: a minimal project in a temporary folder.

The tests that use it never read the template in `src/` (only the smoke, adaptation and CSS tests do), so a
site that renames or removes the sample pages keeps a working suite.
"""
import json
import struct
from pathlib import Path

SITE = {
    'site_url': 'https://fixture.test',
    'site_name': 'Fixture Site',
    'language': 'en',
    'contact_email': 'hello@fixture.test',
    'city': 'Fixture City',
    'region': 'Fixture Region',
    'nav': [
        {'label': 'Home', 'url': '/'},
        {'label': 'Company', 'url': '/company/', 'children': [{'label': 'Team', 'url': '/company/team/'}]},
        {'label': 'Talk to us', 'url': '/talk/', 'action': True},
    ],
    'legal_nav': [{'label': 'Legal notice', 'url': '/legal/'}],
}

ENTITY = [
    {
        '@type': 'Organization',
        '@id': '{{site_url}}/#business',
        'name': '{{site_name}}',
        'url': '{{site_url}}',
    },
]

# First Schema.org type of each class of local business the base supports. The tests use this list; they read no
# documentation.
MAIN_TYPES = ('Restaurant', 'Dentist', 'HairSalon', 'Plumber', 'AutoRepair', 'AccountingService', 'Store', 'Hotel',
              'ChildCare', 'DryCleaningOrLaundry')

LAYOUT = (
    '<!doctype html>\n<html lang="{{lang}}">\n<head>\n<meta charset="utf-8">\n'
    '<title>{{title}}</title>\n<meta name="description" content="{{description}}">\n'
    '<meta property="og:image:width" content="{{og_image_width}}">\n<meta property="og:image:height" content="{{og_image_height}}">\n'
    '<meta name="robots" content="{{robots}}">\n<meta property="og:locale" content="{{og_locale}}">\n{{canonical}}\n{{og_url}}\n{{jsonld}}\n'
    '</head>\n<body>\n<a href="#main">{{ui_skip_to_content}}</a>\n{{header}}\n{{content}}\n{{footer}}\n'
    '{{whatsapp_float}}\n</body>\n</html>\n'
)

HEADER = ('<header><a href="/" aria-label="{{site_name}}, {{ui_home_aria}}">logo</a>'
          '<input type="checkbox" aria-label="{{ui_open_menu}}"><nav aria-label="{{ui_main_navigation}}">{{nav}}</nav></header>')
FOOTER = ('<footer><p><strong>{{site_name}}</strong> {{ui_footer_based_in}} <strong>{{location}}</strong>.</p>'
          '{{footer_contact}}'
          '<nav aria-label="{{ui_footer_site}}">{{footer_nav}}</nav>'
          '<nav aria-label="{{ui_footer_legal}}">{{legal_nav}}</nav>'
          '<p>&copy; {{year}} {{site_name}}. {{ui_rights_reserved}}</p></footer>')

HOME = (
    '---\ntitle: {{site_name}} home page for the fixture\n'
    'description: Description of the fixture home page.\nupdated: 2026-01-01\n---\n'
    '<main id="main"><h1>{{site_name}}</h1><p>Visit {{site_url}}/.</p></main>\n'
)
NOT_FOUND = (
    '---\ntitle: Page not found in the fixture\ndescription: The fixture 404 page.\n'
    'robots: noindex, follow\ncanonical: none\nupdated: 2026-01-01\n---\n'
    '<main id="main"><h1>404</h1></main>\n'
)


def png_header(width, height):
    """The first 33 bytes of a PNG (signature and IHDR chunk): enough for the engine, which reads only the size."""
    return (b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', width, height)
            + b'\x08\x06\x00\x00\x00' + b'\x00\x00\x00\x00')


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')
    return path


def write_bytes(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def page(title, body='', **front):
    """Text of a page of the fixture: front matter (title, description, updated) and a <main>."""
    meta = {'title': title, 'description': f'Description of {title}.', 'updated': '2026-01-01', **front}
    head = ''.join(f'{k}: {v}\n' for k, v in meta.items())
    return f'---\n{head}---\n<main id="main"><h1>{title}</h1>{body}</main>\n'


def make_project(root, site=None, entity=None):
    """Write a minimal project in `root` and return it. `site` / `entity` replace the default data
    (a dict is merged into SITE; pass a str to write it as is, for example invalid JSON)."""
    root = Path(root)
    if isinstance(site, str):
        write(root, 'src/data/site.json', site)
    else:
        write(root, 'src/data/site.json', json.dumps({**SITE, **(site or {})}, indent=2) + '\n')
    entity_text = entity if isinstance(entity, str) else json.dumps(ENTITY if entity is None else entity, indent=2) + '\n'
    write(root, 'src/data/entity.json', entity_text)
    write(root, 'src/layout.html', LAYOUT)
    write(root, 'src/partials/header.html', HEADER)
    write(root, 'src/partials/footer.html', FOOTER)
    write(root, 'src/css/site.css', ':root { --bg: #080d17; }\nbody { margin: 0; }\n')
    write(root, 'src/pages/index.html', HOME)
    write(root, 'src/pages/404.html', NOT_FOUND)
    write(root, 'src/static/robots.txt', 'User-agent: *\nAllow: /\nSitemap: {{site_url}}/sitemap.xml\n')
    return root


# --------------------------------------------------------------------------- clean project
# A complete project for which `run_checks` reports NOTHING: the base of the rule table in
# `test_validator_rules.py`. Independent of `src/` (a site adapted by a client does not change it).

CLEAN_SITE_URL = 'https://fixture.test'

CLEAN_LAYOUT = (
    '<!doctype html>\n<html lang="{{lang}}" dir="ltr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<meta name="color-scheme" content="dark">\n<meta name="theme-color" content="{{theme_color}}">\n'
    '<meta name="author" content="{{site_name}}">\n'
    '<meta name="description" content="{{description}}">\n<meta name="robots" content="{{robots}}">\n'
    '{{canonical}}\n'
    '<link rel="icon" href="/favicon.ico" sizes="48x48">\n'
    '<link rel="icon" href="/images/favicon.svg" type="image/svg+xml" sizes="any">\n'
    '<link rel="apple-touch-icon" href="/images/apple-touch-icon.png">\n'
    '<meta property="og:locale" content="{{og_locale}}">\n<meta property="og:type" content="website">\n'
    '<meta property="og:site_name" content="{{site_name}}">\n<meta property="og:title" content="{{title}}">\n'
    '<meta property="og:description" content="{{description}}">\n{{og_url}}\n'
    '<meta property="og:image" content="{{site_url}}/images/og-image.png">\n'
    '<meta property="og:image:type" content="image/png">\n'
    '<meta property="og:image:width" content="{{og_image_width}}">\n'
    '<meta property="og:image:height" content="{{og_image_height}}">\n'
    '<meta property="og:image:alt" content="{{site_name}}">\n'
    '<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{{title}}">\n'
    '<meta name="twitter:description" content="{{description}}">\n'
    '<meta name="twitter:image" content="{{site_url}}/images/og-image.png">\n'
    '<title>{{title}}</title>\n<link rel="sitemap" type="application/xml" href="/sitemap.xml">\n{{jsonld}}\n'
    '<link rel="stylesheet" href="/css/site.css">\n</head>\n'
    '<body>\n<a class="skip-link" href="#main">{{ui_skip_to_content}}</a>\n{{header}}\n{{content}}\n{{footer}}\n'
    '{{whatsapp_float}}\n</body>\n</html>\n'
)

CLEAN_ENTITY = [
    {'@type': 'Organization', '@id': '{{site_url}}/#business', 'name': '{{site_name}}', 'url': '{{site_url}}'},
    {'@type': 'WebSite', '@id': '{{site_url}}/#website', 'url': '{{site_url}}/', 'name': '{{site_name}}',
     'inLanguage': '{{in_language}}', 'publisher': {'@id': '{{site_url}}/#business'}},
]

CLEAN_WEBPAGE_JSONLD = (
    '<script type="application/ld+json">\n'
    '{"@context": "https://schema.org", "@graph": [{"@type": "WebPage", "@id": "{{page_url}}#webpage", '
    '"url": "{{page_url}}", "name": "{{page_title}}", "description": "{{page_description}}", '
    '"inLanguage": "{{in_language}}", "isPartOf": {"@id": "{{site_url}}/#website"}, '
    '"about": {"@id": "{{site_url}}/#business"}, "dateModified": "{{page_updated}}"}]}\n</script>\n'
)

# title / description of each indexable page of the clean project (length inside the validator thresholds)
CLEAN_PAGES = {
    'index': ('Fixture Site | Clear information for visitors',
              'Fixture Site explains what it does, how it works and how to get in touch, in plain words and with '
              'every fact written down.'),
    'about': ('About Fixture Site and the people behind it',
              'Who runs Fixture Site, since when and how to reach the team, written for visitors who want '
              'the facts before they get in touch.'),
    'legal': ('Legal notice of Fixture Site for visitors',
              'The legal notice of Fixture Site: who is responsible for the website, how to contact them and '
              'which rules apply to the content.'),
}
_FILLER = ('This sentence is plain filler text with no claim in it. It only exists so that the page has enough '
           'words in the main area to count as real content for the validator. ')


def clean_body(links, h2='More information'):
    """Body of a clean page: JSON-LD, a <main> with a heading, over 250 words and contextual links."""
    paragraphs = ''.join(f'<p>{_FILLER * 3}</p>' for _ in range(4))
    nav = ' '.join(f'<a href="{href}">{label}</a>' for href, label in links)
    return (f'{CLEAN_WEBPAGE_JSONLD}<main id="main"><h1>{{{{page_title}}}}</h1>{paragraphs}'
            f'<h2>{h2}</h2><p>{nav}</p></main>\n')


def make_clean_project(root):
    """Write a project whose build gives a site with no errors and no warnings. Pages: /, /about/, /legal/ (all
    indexable, all linked from the <main> of another one) and the 404 page. Returns `root`."""
    root = Path(root)
    site = {**SITE, 'site_url': CLEAN_SITE_URL, 'theme_color': '#080d17', 'site_description': 'A fixture site used only by the tests.', 'nav': [{'label': 'Home', 'url': '/'}, {'label': 'About', 'url': '/about/'}],
            'legal_nav': [{'label': 'Legal notice', 'url': '/legal/'}]}
    write(root, 'src/data/site.json', json.dumps(site, indent=2) + '\n')
    write(root, 'src/data/entity.json', json.dumps(CLEAN_ENTITY, indent=2) + '\n')
    write(root, 'src/layout.html', CLEAN_LAYOUT)
    write(root, 'src/partials/header.html', HEADER)
    write(root, 'src/partials/footer.html', FOOTER)
    write(root, 'src/css/site.css', ':root { --bg: #080d17; }\nbody { margin: 0; }\n')
    links = {'index': [('/about/', 'About us'), ('/legal/', 'Legal notice')],
             'about': [('/', 'Back to the home page')], 'legal': [('/', 'Back to the home page')]}
    for name, (title, desc) in CLEAN_PAGES.items():
        rel = 'src/pages/index.html' if name == 'index' else f'src/pages/{name}/index.html'
        write(root, rel, f'---\ntitle: {title}\ndescription: {desc}\nupdated: 2026-01-01\n---\n' + clean_body(links[name]))
    write(root, 'src/pages/404.html', NOT_FOUND)
    write(root, 'src/static/robots.txt', 'User-agent: *\nAllow: /\n\nSitemap: {{site_url}}/sitemap.xml\n')
    write(root, 'src/static/llms.txt', '# {{site_name}}\n\n> {{site_description}}\n\n## Pages\n\n{{llms_pages}}\n')
    write_bytes(root, 'src/static/favicon.ico', b'\x00\x00\x01\x00')
    write(root, 'src/static/images/favicon.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>\n')
    write_bytes(root, 'src/static/images/apple-touch-icon.png', png_header(180, 180))
    write_bytes(root, 'src/static/images/og-image.png', png_header(1200, 630))
    return root
