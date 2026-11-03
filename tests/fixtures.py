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
