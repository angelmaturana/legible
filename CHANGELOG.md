# Changelog

All notable changes to `legible` are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/): a change that makes a site which used to build stop building is a MAJOR change and is marked **Breaking**.

## [Unreleased]

### Stylesheet architecture

- `--header-h` token: the header height, the anchor offset (`scroll-margin-top`) and the mobile menu panel height derive from it. This also fixes two stale values (anchors were offset 120 px and the panel 110 px for a 131 px header).
- Breakpoints reduced to four documented values (640 / 768 / 960 / 1100). The footer grid now switches at 960 px instead of 901 px; the 1101 px tier is now 1100 px; the redundant `--breadcrumb-gap` media query is gone.
- Menu styled with flat classes (`.site-nav`, `.nav-list`, `.nav-sub`, `.nav-link`, `.nav-sublink`, `.nav-action`) instead of `.site-header nav li ul a`. **The engine now writes these classes in `{{nav}}`** (and `header.html` gives the `<nav>` the class `site-nav`); a project with its own header partial must add `class="site-nav"`.
- Radius scale `--r-sm` / `--r-md` / `--r-lg` (replaces `--r`; cards and the submenu use 12 px) and z-index tokens `--z-header` / `--z-float` / `--z-skip`.

### V4 restructuring

`legible` is now a small, general base for a site with one main entity (a business, a project or a person). The work was done in sub-phases F0 to F12; each one kept the tests green and, when it touched the engine, left `dist/` identical unless noted.

**Removed**

- Guides, blog, collections, the closing strip of the indexes (`lead_strip`) and the home resources section (F1).
- The "services business" machinery: offers, categories, served cities, `geo` tags, `texts.json`, `target_audience`, `price_range`, sample-value warnings and the fallback `entity.json` → `site.json` (F5A, F5B). Every text of `site.json` is now a marker (one pass; reserved names and `{{` in a value are errors).
- `generated_content`, `locale_overrides`, `DEFAULT_TEXTS`, `months` and `long_date` (F6): a site that still has `generated_content` gets an error that points to `ui`. The same happens with `sitemap_base_order` (F3B).
- Sample pages `services/`, `pricing/`, `about/` and `featured-action/`; the sample site is Home, Example page, Contact, Legal notice, Privacy policy, Cookie policy and 404 (F4A).
- `project_stage`, `FLOW_OFF.lock`, `SITE_PLAN.md` and the `legible flow on/off` commands (F11A, F11B).
- 27 CSS classes no page uses (71 → 42) and the unused tokens (F9A, F9B).
- `tests/test_legible.py` and `golden_dist.json` (F10D).

**Added**

- `legible/common.py` (`MIN_PYTHON` 3.10, `BuildError`, config, LF file I/O) and the `Site` object (`build.load_site(root)`) instead of module globals; functions raise `BuildError` instead of exiting (F2A, F2B).
- Menus from `nav` and `legal_nav` in `site.json` (`{{nav}}`, `{{footer_nav}}`, `{{legal_nav}}`) with clear errors (F3A).
- Markers `{{page_url}}`, `{{page_updated}}` (an error that names the page if `updated` is missing), `{{page_title}}` and `{{page_description}}`; the sitemap lists `/` first and then the pages by URL (F3B).
- `site.json` keys `site_description`, `theme_color`, `legal_*` and `country_code`; `llms.txt` is a short template with `{{llms_pages}}` (F4B, F5B).
- Interface texts in one `UI` table (`en`, `es`) published as `{{ui_*}}` and rewordable with `ui` in `site.json` (F6).
- Optional contact: `{{contact_methods}}`, `{{footer_contact}}`, `{{whatsapp_float}}`; `og:image` size read from the PNG header; `check_site.py --prelaunch` lists the example data left (exit 1 on the base) and honours `SITE_URL`/`--site-url` (F7, F10D).
- `python3 legible/build.py --all` is the whole pipeline (build, validation, prelaunch notice; honours `SITE_URL`, `CSS_MINIFY`, `CHECK_STRICT`); `build.sh` is a wrapper and `run_all.py` no longer needs bash. `--strict` makes any warning fail the build (F8B).
- `legible/minify.py`; `build.py` grouped in 8 headed blocks; JSON-LD, sitemap and `llms.txt` errors name the page or file and the fix (F8A).
- Card component (`.card-grid`, `.card`, `.card-number`), `--logo-ratio`, 44 px touch targets, a `forced-colors` rule for the menu button and template tests for contrast, `theme_color`, colours outside `:root`, motion and focus (F9B).
- Four test files that run in process (`fixtures.py`, `test_engine.py`, `test_validator.py`, `test_site.py`; 280 tests, about 5 s) (F10).

**Changed**

- `AGENTS.md` (about 100 lines: `legible start`, `legible continue`, `legible help`, a two-round interview), `DOCUMENTATION.md` and `README.md` are rewritten from scratch (F11A to F12B).
- **Breaking:** a page that uses `{{contact_email}}` while `contact_email` is empty is a build error that names the page; the template's legal pages need the email (F10D).
- Python 3.10 or newer is required (F2A).
- CSS helper classes named by function: `.page-note` (muted note under a page intro) and `.lead-follow` (paragraph after a lead) replace `.text-muted-lg`, `.mt-15` and `.mt-18` (F13A).

### Fixed

- A copy of the template with no main node stopped with an unrelated marker error; it now says `no main node` and names the expected `@id` (`{{site_url}}/#business`).
- An explicit `null` in `site.json` or in a FAQ JSON-LD no longer crashes the build or the validator.
- Unclosed attribute quotes or `<script>`/`<style>` tags are diagnosed with the tag and line instead of symptoms such as "0 h1".

## [1.1.0] - 2026-10-30

Summary of the version that introduced the AI workflow, kept for history (most of it was removed in V4).

- **Added:** `legible start` / `continue` / `help` commands, `SITE_PLAN.md` phase plans with size limits, `project_stage`, `FLOW_OFF.lock`, refinement, recovery and maintenance modes, a fast start from a URL or images, Engine mode announced in the AI's messages.
- **Added:** `generated_content.locale_overrides`, a validator warning for sample-domain URLs, the `{{page_title}}`/`{{page_description}}` markers, `find_broken_markup` and a main node of any Schema.org `@type`.
- **Changed:** `AGENTS.md` and `DOCUMENTATION.md` reorganised several times (one source of truth, phases sized for a free-plan session); `build()` split into small steps with no behaviour change; the golden test of `dist/` was removed.
- **Breaking:** `legible/locales/*.json` were replaced by `DEFAULT_TEXTS` in `build.py`.
- **Fixed:** safer escaping of card labels, optional contact data, sample values no longer published silently, and a test suite that no longer depends on the template's sample pages.

## [1.0.0] - 2026-10-25

First release: a static-site generator in the Python standard library with no client-side JavaScript; business facts in `site.json`, `entity.json` and `texts.json` propagated through `{{markers}}`; HTML, CSS, JSON-LD, `sitemap.xml`, `robots.txt` and `llms.txt`; a strict validator (`check_site.py`); `build.sh`, `dev.py` and `run_all.py`; English and Spanish texts; an 11-page sample site and 130 tests.

---

## How to add an entry

1. Write changes under `[Unreleased]` as you make them, grouped under `### Added`, `### Changed`, `### Fixed` or `### Removed`. Omit empty groups.
2. When you release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, then add a new empty `## [Unreleased]` above it.
3. Use the version rules from Semantic Versioning: **MAJOR** for a breaking change (prefix its entry with `**Breaking:**`), **MINOR** for compatible new functionality, **PATCH** for fixes that do not change behaviour.
4. Use the same number in the Git tag (`vX.Y.Z`) and the release branch (`release/X.Y.Z`).
