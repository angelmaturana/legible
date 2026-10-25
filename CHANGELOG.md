# Changelog

All notable changes to `legible` are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/): a change that makes a site which used to build stop building is a MAJOR change and is marked **Breaking**.

## [Unreleased]

## [1.0.0] - 2026-10-25

First release.

### Added

- Static-site generator (`legible/build.py`) written with the Python standard library only, with no client-side JavaScript and no third-party requests. Requires Python 3.8 or newer.
- Business facts kept in three data files (`src/data/site.json`, `entity.json`, `texts.json`) and propagated through `{{markers}}`; an unresolved marker stops the build and names the marker and the page.
- Generated output: HTML pages, one CSS file (optionally minified), a Schema.org JSON-LD `@graph` per page, `sitemap.xml`, `robots.txt` and `llms.txt`.
- Optional guides and blog collections with generated indexes and configurable folder paths (`collection_paths`).
- Strict validator (`legible/check_site.py`) for the compiled site: metadata, headings, links and assets, placeholders, JSON-LD references, sitemap and `robots.txt`. In strict mode warnings also fail the build.
- `legible/build.sh`, which builds and then validates, driven by `SITE_URL`, `CSS_MINIFY` and `CHECK_STRICT`.
- Local development server (`legible/dev.py`) that rebuilds when `src/` changes, and `legible/run_all.py`, which runs tests, build with validation and the server in order.
- English and Spanish engine-generated strings (`legible/locales/en.json` and `es.json`); other languages need a locale file and a row in the `LANGUAGES` table of `build.py`.
- Sample site of 11 pages (including the 404 page) with neutral, fictional content, to be replaced before publishing.
- Regression suite of 119 `unittest` tests.
- Documentation: `README.md`, `DOCUMENTATION.md` (reference, marker catalogue, validator rules and the guide and briefing template for AI-generated sites) and `AGENTS.md` (entry point for AI agents).

---

## How to add an entry

1. Write changes under `[Unreleased]` as you make them, grouped under `### Added`, `### Changed`, `### Fixed` or `### Removed`. Omit empty groups.
2. When you release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, then add a new empty `## [Unreleased]` above it.
3. Use the version rules from Semantic Versioning: **MAJOR** for a breaking change (prefix its entry with `**Breaking:**`), **MINOR** for compatible new functionality, **PATCH** for fixes that do not change behaviour.
4. Use the same number in the Git tag (`vX.Y.Z`) and the release branch (`release/X.Y.Z`).
