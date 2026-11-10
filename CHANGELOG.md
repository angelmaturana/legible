# Changelog

All notable changes to `legible` are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/): a change that makes a site which used to build stop building is a MAJOR change and is marked **Breaking**.

## [Unreleased]

### Tests no longer break once a real site lives in the folder

- Tests only, no engine change. `run_all.py` stopped at step 1 as soon as `src/data/site.json` held real data, because three tests assumed the folder is always the pristine base: `TestSampleValues` and `TestPrelaunchCommand` (they check the base *ships* with example values and that `--prelaunch` fails on it) and the contact-channels test (it asked for the English text whatever `language` was). The first two now skip themselves (`ONLY_ON_THE_BASE`) when `site_name` is no longer the example value; the third reads the text for the site's own `language`. On the base nothing changes: all 400 tests still run.

### Validator no longer crashes on malformed JSON-LD

- A page whose JSON-LD had an unexpected shape (root that is a list or `null`, a `@graph` item that is not an object, `FAQPage.mainEntity` that is an object or a list of texts, `dateModified` or `name` that is not text) made `run_checks`, and so the build, fail with a Python traceback. It now reports a validator message instead: an error `JSON-LD with an unexpected shape: <detail>` for the structural cases, and the warnings `dateModified is not text: <value>` / `name is not text: <value>`. No existing message changed.
- Same for the shapes found afterwards: a JSON-LD `@id` (of a node or of a reference) that is a list, object or number is now the error `JSON-LD with an unexpected shape: @id is not text: <value>`; a FAQ `Question.name` or `acceptedAnswer.text` that is not text is the warning `FAQPage Question name is not text: <value>` / `FAQPage Answer text is not text: <value>`; an `acceptedAnswer` that is text gets the existing warning `without acceptedAnswer @type="Answer"`; a `null` question name no longer crashes. A fuzz pass over every value of the sample JSON-LD (11 odd values per position, 275 cases) now produces no traceback.
- A JSON-LD `@type` that is neither text nor a list of texts (an object, a number, a list with a number) is now the warning `JSON-LD @type is not text or a list of texts: <value>`. A missing `@type` and a list of texts such as `["Restaurant", "LocalBusiness"]` stay valid and silent.

### Internal refactor of `build.py` (no change to output)

- `_nav_items`, `print_report` and `parse_args` are split into small pieces (`_NavChecker`, `_Box` with `_size_rows`, `_report_sizes` and `_report_findings`, `_read_options`, `_apply_all` and `_parse_minify`), so every function in `legible/` now has cyclomatic complexity ≤ 10. The files in `dist/`, the console report and the usage error texts are byte-for-byte identical (checked with a SHA-256 golden of `dist/` and a golden of the console report).

### Validator test net (refactor of `check_site.py`)

- Tests only, no engine change: `fixtures.make_clean_project` (a site with no findings) and `tests/test_validator_rules.py`, a rule table where each row changes one thing and expects exactly one message. Rule rows R01-R95, a golden file of the validator output, a public API test and a mutation check (every message-emitting statement is covered).
- Internal refactor of `check_site.py` (F5-F9b, no change to messages or their order; every function now has cyclomatic complexity ≤ 10 and ≤ 40 lines, and `run_checks` is not slower): `run_checks`, `prelaunch_findings` and the console report are split into small helpers (`_check_required_files`, `_load_pages`, `_check_one_page`, `_prelaunch_*`, `_Box`). How to add a rule is documented in `DOCUMENTATION.md`.
- (Details of the earlier steps, F5-F9a:) `Findings`/`PageCtx`, JSON-LD parsed once per page, and `check_page` split into eleven rule groups (the last one, `rules_jsonld`, built from small `_ld_*` pieces) listed in `PAGE_RULES` (the order of that tuple is the order of the messages); `check_links` and `check_sitemap` are split into small helpers (`_classify_href`, `_check_href`, `_check_resources`, `_orphans`, `_read_sitemap`, `_check_sitemap_entries`, …) and the dead code in `check_links` is gone. `PageParser` dispatches start and end tags through tables (one method per tag) and `find_broken_markup` is split into `_comment_end` and `_tag_end`.

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
