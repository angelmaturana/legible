# Changelog

All notable changes to `legible` are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/): a change that makes a site which used to build stop building is a MAJOR change and is marked **Breaking**.

## [Unreleased]

### Added

- AI workflow for building the base of a site. The AI first looks for `SITE_PLAN.md` in the zip. With a plan it continues it (on `continue` or any similar phrase in any language, or when nothing specific is asked); with no plan, a start command (`start site`, `new site`, `run legible`, or a translation) starts the work and the AI runs a twelve-question interview in three rounds (the site, the contact and offer, the design and gaps), proposes the pages, URLs and design direction for the user to confirm, and returns the zip with a short `SITE_PLAN.md` already inside; later sessions execute one phase each, update the plan and return the zip. Documented in `AGENTS.md`, `DOCUMENTATION.md` (sections 5.0, 5.4, 5.5, 6.1 and 6.2) and the README ("Build a site with an AI").
- `SITE_PLAN.md` format: briefing, URL map, at most ten phases sized for one free-plan session each (data; structure and URLs; brand tokens; component styles; layout and partials; brand assets; content in three phases; legal and close) with statuses (`pending`, `in_progress`, `done`, `blocked`), pending confirmations, engine notes, execution log, a **Later** list and a **Final state** section.
- Size limits so the plan stays a short base structure an AI can read in full each session: about 120 lines, at most two lines of detail per phase, a session budget of about three pages or three large files per phase, no per-page outlines or small-task checklists, Later items in one line, at most three log lines per session.
- `project_stage` in `src/data/site.json` (`template`, `in_progress`, `complete`): a coarse marker set by the AI when phase 1 starts and when the plan completes. The engine and the validator ignore it (the build, the strict validator and the 130 tests pass with it present), so no engine change is needed.
- Refinement mode: with `project_stage` `complete` and no `SITE_PLAN.md`, the AI does not run the flow (no interview, recovery, continuing or new plan); it works only on the part the user names. Starting over needs an explicit request and a confirmation.
- Recovery mode: when `project_stage` is `in_progress` (older zips without the field fall back to the sample values in `site.json`) but `SITE_PLAN.md` is missing, the AI audits the project, rebuilds a short plan from the evidence (phases `done` only when supported, nothing guessed) and asks the user to confirm it, instead of starting the interview from zero.
- Completion and maintenance: when the last phase is done the plan is marked `complete` and its **Final state** records the state of everything; attaching the zip later starts maintenance mode, which fixes or extends only the part the user names.
- With no plan, any request that is not a start command (and with a plan, any clear request other than continuing it) makes the AI first explain what `legible` is, what it fits, which checks it includes and how it is used; it warns about partial fits, things outside the base and engine changes, and waits for the user's decision (`AGENTS.md` section 1, `DOCUMENTATION.md` section 5.0).
- Built-in SEO checks are described as part of `legible` (`DOCUMENTATION.md` section 1.0, README "Validation"): generated metadata and JSON-LD, sitemap, `robots.txt`, `llms.txt`, strict validator and pre-launch sweep. The AI never asks the user whether to enable them.
- Verification rules for every phase except the last (`CHECK_STRICT=FALSE` only to review warnings from pending facts, never in the last phase) and for an AI that cannot run commands.
- `AGENTS.md` mode for one-session builds, and engine mode that also applies when a plan exists.
- Measurable plan checks: `wc -l SITE_PLAN.md` (120 lines or fewer) and a count of the phase rows (10 or fewer, 12 at most), run before delivering the plan and after every update; and `wc -c` on the files a phase will touch (about 50000 bytes at most) before it starts.
- A `Read:` line per phase, with a default table in `AGENTS.md` section 5, so a session reads only the sections and files it needs instead of the whole documentation.

### Changed

- The plan's phases are resized for a session of a free-plan chat. The old single "design and brand" phase becomes four (brand tokens, component styles, layout and partials, brand assets) and "content" becomes three (home, services index and pricing; service pages; featured action, about and contact); legal pages and the close are one phase. The limit moves from five to ten phases (twelve with more than three service pages), detail per phase drops from four lines to two, and each phase has a session budget of about three pages or three large files. A phase the site does not need (for example the brand tokens when the base look is kept) stays in the plan as `done` with "not needed". The AI never fabricates `og-image.png`, `apple-touch-icon.png` or `favicon.ico`: the sample files stay and are listed as pending until the user supplies the real ones.
- `AGENTS.md` is easier to follow as a prompt, with no change of rules: an "At a glance" summary at the top; section 1 is a single decision table (plan, `project_stage`, request, mode, first words) and section 3 only lists the modes; the longest paragraphs are split into short bullets; and the end of section 8 says what to do when a case is not covered (stop, name the gap, ask one question).
- One source of truth for the AI method: `AGENTS.md` holds the procedures, numbers, limits and commands, and `DOCUMENTATION.md` section 5.0 keeps the reasoning and the reference tables and points to `AGENTS.md` instead of repeating them (the phase catalogue, the plan size limits, the steps of each mode and the verification rules were written in both). New ground rule 7 in `DOCUMENTATION.md` section 0.1 says so, and `AGENTS.md` says that it wins if the two differ.
- `src/data/site.json` now carries `"project_stage": "template"`, as the documentation already stated; the engine and the validator ignore it.
- `DOCUMENTATION.md` section 2.2: alignment of the `SITE_PLAN.md` line.
- "Integrated tools" is now "interactive features" in `AGENTS.md`, the README and `DOCUMENTATION.md`: it means calculators, booking, forms with a backend and maps, which are outside the base. It was previously read as if `legible` lacked tools.
- `AGENTS.md` is rewritten: the default job is building a site by changing only `src/`; the engine, the tests and the architecture are not to be improved on the AI's own initiative, and deployment is outside the process. An engine change is a minimal exception that must be recorded in the plan.
- `AGENTS.md` rule 5 points to `DOCUMENTATION.md` section 7.4 explicitly, so it is not confused with the engine exception in `AGENTS.md` section 7.
- `DOCUMENTATION.md` section 6.1 (one-session prompt) is now 6.3 and is optional; the briefing template is an optional shortcut for the interview.

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
