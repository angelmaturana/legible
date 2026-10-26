# Changelog

All notable changes to `legible` are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/): a change that makes a site which used to build stop building is a MAJOR change and is marked **Breaking**.

## [Unreleased]

## [1.0.0] - 2026-10-25

First release.

### Added

- `{{target_audience}}` is now a derived marker and is escaped for HTML and JSON-LD like the others; a zone name such as `Rock & Roll <City>` no longer breaks the footer.
- A text in `texts.json` can reference another text in any order (up to 5 passes); circular references still fail with a marker that has no value.
- A clear error when an `areaServed` entry is not an object, and an error message for unresolved derived markers that points to `entity.json` or `site.json`.
- The sitemap `lastmod` and the `updated` front matter can no longer disagree silently: when both exist they must match or the build fails. The sample service page now has `updated`.
- The validator's internal link keys now always use `/` (`as_posix()`), so on Windows pages should no longer be reported as orphans and anchors to other pages should be checked. Not yet run on Windows.
- The `legible/dev.py` file watcher now ignores files that disappear while it is scanning `src/`, instead of letting the watcher thread die silently.
- The pre-launch sweep (README and `DOCUMENTATION.md` section 7.4) is now the same single-quoted command in both places, so the price patterns match; it also flags sample hours, deadlines, currency and country.
- The sample bundle price is now lower than the two services it combines.
- The unresolved-marker error says "first found on page …" (the marker may appear on several pages), and the redundant `target_audience` parameter of `compose_page` was removed.
- An empty `SITE_URL` falls back to `site_url` in `src/data/site.json`, and `build.sh` warns (without failing) when the output still uses the sample domain `YOUR-DOMAIN.com`.
- Static-site generator (`legible/build.py`) written with the Python standard library only, with no client-side JavaScript and no third-party requests. Requires Python 3.8 or newer.
- Business facts kept in three data files (`src/data/site.json`, `entity.json`, `texts.json`) and propagated through `{{markers}}`; an unresolved marker stops the build and names the marker and the page.
- Generated output: HTML pages, one CSS file (optionally minified), a Schema.org JSON-LD `@graph` per page, `sitemap.xml`, `robots.txt` and `llms.txt`.
- Optional guides and blog collections with generated indexes and configurable folder paths (`collection_paths`).
- Strict validator (`legible/check_site.py`) for the compiled site: metadata, headings, links and assets, placeholders, JSON-LD references, sitemap and `robots.txt`. In strict mode warnings also fail the build.
- `legible/build.sh`, which builds and then validates, driven by `SITE_URL`, `CSS_MINIFY` and `CHECK_STRICT`.
- Local development server (`legible/dev.py`) that rebuilds when `src/` changes, and `legible/run_all.py`, which runs tests, build with validation and the server in order.
- English and Spanish engine-generated strings (`legible/locales/en.json` and `es.json`); other languages need a locale file and a row in the `LANGUAGES` table of `build.py`.
- Sample site of 11 pages (including the 404 page) with neutral, fictional content, to be replaced before publishing.
- Regression suite of 130 `unittest` tests.
- Documentation: `README.md`, `DOCUMENTATION.md` (reference, marker catalogue, validator rules and the guide and briefing template for AI-generated sites) and `AGENTS.md` (entry point for AI agents).

---

## How to add an entry

1. Write changes under `[Unreleased]` as you make them, grouped under `### Added`, `### Changed`, `### Fixed` or `### Removed`. Omit empty groups.
2. When you release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, then add a new empty `## [Unreleased]` above it.
3. Use the version rules from Semantic Versioning: **MAJOR** for a breaking change (prefix its entry with `**Breaking:**`), **MINOR** for compatible new functionality, **PATCH** for fixes that do not change behaviour.
4. Use the same number in the Git tag (`vX.Y.Z`) and the release branch (`release/X.Y.Z`).
