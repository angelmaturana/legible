# legible: technical reference

`legible` turns the files in `src/` into a static site in `dist/`. This file is the reference for the engine and the data model. The procedure for an AI is in [`AGENTS.md`](AGENTS.md); how to use the project is in [`README.md`](README.md). The standard expected for audits, design and engine changes is in [`SKILLS.md`](SKILLS.md), which links here instead of copying this reference.

## What it is and what it is not

- **Is:** a generator for small sites with one main entity (a business, a project or a person): a few pages, SEO and structured data checked by a validator, no tooling to install.
- **Is not:** a CMS, a framework, or a site with a database, forms, search, editorial feeds or a shopping cart. It does not deploy: it produces a folder you publish wherever you like.

## Principles

1. Python standard library only (Python 3.10 or newer, `MIN_PYTHON` in `legible/common.py`). No dependencies to install.
2. No client-side JavaScript and no external resources: one stylesheet, system fonts, images from the same site.
3. One source of truth: facts live in `src/data/`, and a page writes them as markers, never by hand.
4. Honest output: nothing is published for data that does not exist (no empty phone link, no empty address). Example values are found by `check_site.py --prelaunch`.
5. A build that would publish something broken fails with a message that names the file and the fix.

## Architecture and flow

```text
legible/
  common.py      MIN_PYTHON, BuildError, site.json loading, read/write (LF), report
  build.py       src/ -> dist/ ; --all = build + validation + pre-launch notice
  check_site.py  validates dist/ (--strict, --prelaunch)
  minify.py      CSS and HTML minifiers      dev.py  local server that rebuilds      run_all.py  tests, build, server
```

`build.py` does the following, in this order. Nothing is read when a module is imported.

1. `load_site(root)` reads and validates `site.json`, the language and `entity.json` into a `Site` object.
2. Builds the table of markers (below) and the generated HTML (`nav`, contact, `llms_pages`).
3. Composes every page: front matter with defaults, JSON-LD merged with `entity.json`, canonical URL, active menu entry.
4. Writes the pages, the CSS, the static files, `sitemap.xml` (home page first, then by URL; only indexable pages) and `llms.txt`.
5. Minifies if asked, then validates `dist/`.

Commands (run from the project root):

| Command | Does |
|---|---|
| `python3 legible/build.py --all` | Build, validate and print a notice while example data is left (never a failure for that) |
| `python3 legible/build.py [--out FOLDER] [--minify true\|false] [--no-validate] [--strict]` | Build with those options |
| `python3 legible/check_site.py [--dir DIR] [--site-url URL] [--strict]` | Validate a built folder; `--strict` makes warnings fail |
| `python3 legible/check_site.py --prelaunch` | List every example value still left; exit 1 while there is any |
| `python3 legible/dev.py` | Build into `.dev-dist/` and serve it on `http://localhost:3001/`, rebuilding on changes |
| `python3 -B -m unittest discover tests` | The test suite |

Environment: `SITE_URL` overrides `site_url`. Under `--all`, minifying and strict validation are on unless `CSS_MINIFY=FALSE` or `CHECK_STRICT=FALSE` say otherwise.

## Structure

```text
src/
  data/site.json    facts and settings          data/entity.json   JSON-LD of the main node and the site
  layout.html       shared shell                partials/          header.html, footer.html
  pages/            one folder per page (index.html inside), plus 404.html
  css/site.css      one stylesheet; every colour is a token in :root
  static/           copied as they are: favicon.ico, robots.txt, llms.txt, images/
tests/              fixtures.py, test_engine.py, test_validator.py, test_site.py
```

A page's URL is its folder: `src/pages/contact/index.html` is `/contact/`, `src/pages/index.html` is `/`, `404.html` is `/404.html`. A new page is a new folder (copy `example/`); a new slug is a renamed folder plus its `nav`/`legal_nav` entry and links.

## Data model

### `site.json`

| Key | Meaning |
|---|---|
| `site_url`, `site_name`, `site_description`, `language`, `theme_color` | Identity. `site_url` is `https://` with no trailing slash; `theme_color` equals `--bg` in `:root` |
| `contact_email`, `phone_e164`, `whatsapp_message` | Contact. All optional: an empty one removes everything that uses it |
| `city`, `region`, `country_code` | Place. `country_code` is ISO 3166-1 alpha-2 (the base ships `XX` on purpose) |
| `legal_name`, `legal_tax_id`, `legal_address`, `legal_jurisdiction` | Used by the legal pages |
| `nav`, `legal_nav` | Menus (see below) |
| `ui` | Rewording of interface texts (see below) |

A setting the engine used to read under an earlier name is now a build error that names the current one.

### `entity.json`

A list of JSON-LD nodes added to the graph of every page: the main node (`@id` `{{site_url}}/#business`, any Schema.org `@type`: `Organization`, `Restaurant`, `Dentist`, `SoftwareApplication`, `Person`, or a list of types) and `WebSite`. Empty values are dropped. A page that defines a node with an `@id` already in `entity.json` is an error.

### Markers

Write `{{name}}` in a page, a partial, `layout.html`, `entity.json` or a static text file and the build replaces it, once.

- **Site texts:** every top-level key of `site.json` whose value is text is a marker. A value that contains `{{` is an error; a key that takes a reserved name or starts with `ui_` is an error.
- **Derived from the site:** `lang`, `og_locale`, `in_language`, `location` (city and region, only the parts that exist), `whatsapp_link`, `whatsapp_base`, `phone_digits`, `year`, `og_image_width`, `og_image_height`.
- **Derived from the page:** `page_title`, `page_description`, `page_url` (`site_url` plus the path), `page_updated` (its `updated`; an error naming the page if used and missing).
- **Generated HTML:** `nav`, `footer_nav`, `legal_nav`, `contact_methods`, `footer_contact`, `whatsapp_float`, `llms_pages`.
- **Layout:** `title`, `description`, `robots`, `canonical`, `og_url`, `jsonld`, `header`, `content`, `footer`.
- **Interface:** `ui_<key>` (below).

Escaping follows the place: HTML-escaped in a page, a JSON string inside JSON-LD. A marker with no value is a build error. A page that uses `{{contact_email}}` while `contact_email` is empty is also an error.

## Pages and front matter

A page starts with a block between `---` lines of `key: value` pairs, then its HTML and, if it wants, its own `<script type="application/ld+json">`.

| Key | Required | Default | Effect |
|---|---|---|---|
| `title`, `description` | yes | | `<title>`, meta description, `{{page_title}}`, `{{page_description}}` |
| `updated` | no | | `YYYY-MM-DD`; feeds `{{page_updated}}`, `dateModified` and the sitemap |
| `robots` | no | `index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1` | A `noindex` page stays out of the sitemap and `llms.txt` |
| `canonical` | no | `auto` | `none` omits the canonical and `og:url` (used by `404.html`) |
| `active` | no | the page's own menu entry, or its closest parent | Menu link to highlight |

The `updated` date and the JSON-LD `dateModified` must agree; writing `{{page_updated}}` in both makes that automatic.

## Menus

`nav` and `legal_nav` are lists of `{"label", "url"}`; the URL is internal (starts and ends with `/`). `nav` takes one level of `children` and `"action": true` on one top-level entry for the highlighted button. A URL repeated inside one list, a second level of `children` or an external URL is an error that names the path in `site.json`. `nav` becomes the header menu and, flattened, the footer's Site column; `legal_nav` the Legal column.

## Interface texts and languages

The fixed words of the layout, the partials and the breadcrumb live in the `UI` table of `legible/build.py` (`en` and `es`) and are published as `{{ui_<key>}}`. Reword any of them for one site with `ui` in `site.json`, for example `{"ui": {"skip_to_content": "Go to the content"}}`; an unknown key is an error. The text of the **pages** is content: when `language` changes, translate the pages.

To add a language: add a row to `LANGUAGES` (html lang, `og:locale`, `inLanguage`) and one complete entry to `UI` with the same keys as `en`, then set `language` and translate the pages and the legal texts. Slugs may be localized.

## Sitemap, robots.txt and llms.txt

`sitemap.xml` lists every indexable page (no `noindex`, not the 404), home page first and the rest by URL, with `lastmod` equal to its `dateModified`. `robots.txt` is a static file in `src/static/`: `Allow: /` and `Sitemap: {{site_url}}/sitemap.xml`. `llms.txt` is a plain-text summary for AI assistants: name, description, contact, the pages in menu order and then the rest, and the machine-readable files. It is optional and costs almost nothing to keep honest, so the base ships it, but no major crawler has confirmed it reads these files yet; do not promise otherwise in its text.

## SEO and HTML contract

Every page the base ships, and every page an adapted site adds by copying `example/`, must meet this:

| Area | Rule |
|---|---|
| `<head>` | `charset`, viewport, a unique `title` (20–60 characters), a unique `description` (70–160), an absolute `https://` canonical, `robots` (`noindex` only on the legal pages and `404.html` if a page needs it), `theme-color` = `--bg`, `color-scheme`, complete `og:*`/`twitter:*`, `og:image` with `alt` and its real width/height |
| Language | `<html lang>` = `language`; `og:locale` and `inLanguage` agree with it |
| JSON-LD | One `@graph` per page: the main node (`/#business`), `WebSite`, and a `WebPage` or `ContactPage` plus a `BreadcrumbList` for the page itself. URLs and dates come from `{{page_url}}`/`{{page_updated}}`. `@id`s are unique. No `FAQPage` in the base (the validator still checks one if a site adds it: its visible text must match the JSON-LD). No empty field is published |
| Structure | One `h1`, no skipped heading levels, `<main id="main">`, a skip-to-content link, `alt` and `width`/`height` on every `<img>` |
| Links | Internal links are absolute with a trailing slash; every page outside the menu/footer gets at least one contextual inbound link from another page's `<main>`; Home, `example/` and `contact/` carry at least 250 words |
| Crawling | `sitemap.xml` with `loc` and `lastmod`; `robots.txt` declares the sitemap; `404.html` is `noindex, follow` with no canonical |
| Facts | No invented number, price, hour or address published as real |

## Validator rules

`check_site.py` reads `dist/` and reports errors (always fail the build under `--strict`, which `--all` uses) and warnings (fail only under `--strict`).

| Area | Errors | Warnings |
|---|---|---|
| Metadata | missing `lang`, viewport, `title`, description or `robots`; non-HTTPS or mismatched canonical; `og:url` ≠ canonical; missing `og:image` file; the 404 with a canonical or `og:url` | title/description out of range; missing `og:*`/`twitter:*`; `og:title` ≠ `<title>`; missing `og:image:alt`; `og:image` under 1200 px wide or off the 1.91:1 ratio; unusual `lang`/`og:locale`/`twitter:card` |
| Structure | not exactly one `h1`; empty heading | first heading not `h1`; skipped level; fewer than 250 words in `<main>` of an indexable page |
| Images | `<img>` without `alt` | `alt` over 125 characters; missing `width`/`height`; `<img>` without `src`/`srcset` |
| Links | broken internal link, anchor or resource; missing trailing slash; malformed `mailto:`/`tel:`; empty `href`; internal link using `http://` | external `http://` link; relative link; `target="_blank"` without `rel="noopener"`/`"noreferrer"`; no contextual inbound link |
| Leftovers | unresolved `{{marker}}` | `TODO` or `[CONFIRM` in visible text; a URL on `example.com`/`.org`/`.net` |
| Broken markup | one extra error naming the unclosed tag, only on a page that already has another error | — |
| Structured data | indexable page with no JSON-LD or invalid JSON; wrong `@context`; duplicate or undefined `@id`; missing main node or `WebSite` | `name` ≠ `<title>`; `dateModified` not ISO |
| Duplicates | same title or description on two indexable pages | — |
| Site files | missing `index.html`, `404.html`, `sitemap.xml` or `robots.txt`; invalid or off-domain sitemap URL; indexable page missing from the sitemap, or a `noindex` page in it; `Disallow: /` for all crawlers | missing `llms.txt`; `lastmod` not ISO or ≠ `dateModified`; `robots.txt` without `Sitemap:` |

These checks are not a substitute for a browser, an accessibility review or a search engine's own tools.

## Pre-launch sweep

```bash
python3 legible/check_site.py --prelaunch
```

Lists what still looks like the template, grouped by finding: a `site.json` key that still holds its sample value (`SAMPLE_VALUES` in `check_site.py`), a page with `<!-- SAMPLE COPY -->`, `YOUR-DOMAIN`/`Your Business` left in `dist/`, or `TODO`/`[CONFIRM` in visible text. Exit code is 1 while anything is left; empty output means ready to publish. `site_url` does not count as example data when `SITE_URL` or `--site-url` is set, because a host usually injects the real domain that way. `build.py --all` prints the same count on success without failing the build.

## Commands

| Action | Command |
|---|---|
| Tests, build and local server | `python3 legible/run_all.py [--skip-tests] [--no-dev] [--port N]` |
| Strict build, wrapper | `./legible/build.sh` (same as `python3 legible/build.py --all`) |
| Validate an existing build | `python3 legible/check_site.py --dir dist --strict --site-url https://your-domain.com` |

`run_all.py` runs the tests, then `build.py --all`, then `dev.py`, in that order; `--skip-tests` or `--no-dev` drop a step. `build.sh` is a three-line wrapper so a host with no Python-first build step can still call a shell script; it reads the same `SITE_URL`, `CSS_MINIFY` and `CHECK_STRICT` variables as `build.py --all` (unset or anything other than `FALSE` keeps minifying and strict validation on).

## Schema.org type by kind of site

The main node's `@type` in `entity.json` is the real type of the site, as text or as a list (`["Restaurant", "LocalBusiness"]`); everything else about the node (`@id`, fields) stays as the base has it. Use the most specific type that fits; fall back to `LocalBusiness` for a business with no better match, or `Organization` for anything else. Check the type exists on schema.org before writing it.

| Kind | Typical `@type` |
|---|---|
| Food and drink | `Restaurant`, `CafeOrCoffeeShop`, `Bakery`, `BarOrPub` |
| Health | `Dentist`, `Physician`, `MedicalClinic`, `VeterinaryCare` (as a list with `LocalBusiness`) |
| Beauty and wellness | `HairSalon`, `BeautySalon`, `DaySpa` |
| Trades and home services | `Plumber`, `Electrician`, `HVACBusiness`, `GeneralContractor` |
| Professional services | `AccountingService`, `LegalService`, `RealEstateAgent`, `ProfessionalService` |
| Retail | `Store`, `ClothingStore`, `BookStore`, `Florist` |
| Lodging | `Hotel`, `BedAndBreakfast`, `LodgingBusiness` |
| Software project | `SoftwareApplication` or `SoftwareSourceCode` |
| Portfolio or person | `Person` |
| Directory or catalogue | `Organization`, plus an `ItemList` added by the site on the pages that list entries |

## Deployment

Reference for people; an AI building a site does not handle this (`AGENTS.md`).

Publish `dist/` on any static host (Cloudflare Pages, GitHub Pages, Netlify, Render, S3 behind a CDN, Nginx):

```text
Build command:      ./legible/build.sh
Publish directory:  dist
Environment:        SITE_URL=https://your-domain.com
```

A failed validation exits non-zero, so the host will not publish a broken build.

## Brand and design notes

- **Logo:** an SVG with its text converted to paths, so it renders without the font installed. `--logo-ratio` in `:root` is the logo's own width/height (its `viewBox`); `.brand-logo` and `.footer-logo img` read it, so a new logo of a different proportion only needs that one token changed.
- **`og-image.png`** is 1200×630 (the 1.91:1 ratio social networks crop to); **`apple-touch-icon.png`** is 180×180; **`favicon.ico`** carries 16, 32 and 48 px. `read_png_size` in `build.py` reads a PNG's own header with the standard library; if a PNG is missing or unreadable, the build warns and leaves `{{og_image_width}}`/`{{og_image_height}}` empty instead of guessing a size. Where no image editor or renderer is available, generate the PNGs and the ICO from the SVGs with any script that writes valid headers; the suite does not care how they were made, only what they measure.
- **Light theme:** not shipped, but reachable by overriding only the tokens in `:root` (no selector elsewhere sets a colour). The CSS suite checks the WCAG contrast of six pairs (`text`/`bg`, `text-muted`/`bg`, `text-muted`/`surface-2`, `accent`/`bg`, `accent-text`/`accent`, `edge`/`bg`) against whatever those tokens hold, so a new palette that keeps those ratios keeps the tests green.

## Recipes

- **A site in Spanish:** set `language: "es"` in `site.json`; the interface texts switch automatically (`ui_*`, see "Interface texts and languages"). Translate the page content and the legal text by hand; slugs may be localized (rename the folder and update `nav`/`legal_nav` and every link).
- **A directory with no prices:** use `Organization` for the publisher and add an `ItemList` node in `entity.json` or on the listing page's own JSON-LD; one page per entry, each a plain page copied from `example/`.
- **Changing the `@type`:** edit the main node's `@type` in `entity.json` (text or list); nothing else in the engine reads it.
- **Adding hours or social profiles:** add `openingHoursSpecification` or `sameAs` directly to the main node in `entity.json`; they are plain JSON-LD, not markers, so no engine change is needed.
- **Changing the palette:** edit the colour tokens in `:root` only; re-run the test suite, which fails if a contrast pair in the table above drops below its minimum.
- **Blocking a specific bot in `robots.txt`:** add its own block before the general one, for example:
  ```text
  User-agent: GPTBot
  Disallow: /

  User-agent: *
  Allow: /
  ```
- **Real local SEO:** `legible` has no `geo.*` meta tags or coordinates; what actually affects local search is a consistent NAP (name, address, phone — the same across `site.json`, directories and any other listing) and a claimed, complete Google Business Profile. Keep both in step with the site by hand.

## Glossary

| Term | Meaning |
|---|---|
| Marker | `{{key}}`, replaced once at build time |
| Front matter | The `---`-delimited block at the top of a page |
| JSON-LD / `@graph` | Schema.org structured data; one per page, merging the business nodes with the page's own |
| Indexable | A page without `noindex` that is not the 404; it belongs in the sitemap |
| Strict mode | Validator warnings also fail the build (`--strict`, or `--all` unless `CHECK_STRICT=FALSE`) |
| `llms.txt` | Plain-text summary of the site for AI assistants; optional |
| Sample copy | Short descriptive text written where the user gave no wording; marked `<!-- SAMPLE COPY -->` and found by `--prelaunch` |
| Pre-launch sweep | `check_site.py --prelaunch`: what still looks like the template |
| Engine mode | The session in which an AI may change `legible/` or `tests/`, only after the user confirms (`AGENTS.md`) |
