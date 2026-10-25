# STATUS — legible cleanup control document

> Single source of truth for **where the cleanup is**. The plan and the rules live in [`DOCUMENTATION.md`](DOCUMENTATION.md) (§6 phases, §0.1 ground rules). This file records what has actually been done.
>
> **For an AI agent:** read this file first, run only the phase marked **▶ Next** (or the one the user names), and update this file before you report (see `DOCUMENTATION.md` §6.1). Never mark a phase done unless its checks were actually run.

| | |
|---|---|
| **Current phase** | **All planned phases complete — P39 done; wait for user direction before adding a new phase** |
| **Last completed** | P39 — Final documentation sync and release check (2026-10-25) |
| **Last updated** | 2026-10-25 (P39 compatibility documentation update) |
| **Tests (latest)** | 119/119 pass across 13 independently run test classes; combined discovery timed out in this environment |
| **Strict build (latest)** | default and `CSS_MINIFY=FALSE` both pass, 11 pages, 0 errors, 0 warnings |
| **Python compatibility (owner-confirmed)** | 3.8.20, 3.9.25, 3.10.22, 3.11.17, 3.12.3, 3.13.17 and 3.14.9; the 119-test suite was not separately rerun on every version |
| **Phases done** | 40 of 40 |

---

## 1. Phase tracker

Status: ✅ Done · ▶ Next · 🔄 In progress · ⏳ Pending · ⏭ Skipped (say why in the log) · ⚠ Blocked (say why in the log)

| ID | Track | Title | Size | Status | Date | Tests | Notes |
|---|---|---|---|---|---|---|---|
| P00 | A | Baseline and backup | none | ✅ Done | 2026-10-25 | 108 | Baseline recorded; Git initialised |
| P01 | A | Single English README | XS | ✅ Done | 2026-10-25 | 108 | `README.es.md` removed; language line removed |
| P02 | B | Comments/docstrings — `build.py` | S | ✅ Done | 2026-10-25 | 108 | 59 comments + 20 docstrings translated; V2 identical code |
| P03 | B | Comments/docstrings — `check_site.py`, `dev.py`, `run_all.py`, `build.sh` | S | ✅ Done | 2026-10-25 | 108 | V2 identical code on 3 `.py`; `bash -n` OK |
| P04 | B | Console messages — `build.py` | S | ✅ Done | 2026-10-25 | 108 | 31 messages translated; 17 test assertions updated |
| P05 | B | Console messages — `check_site.py` | S | ✅ Done | 2026-10-25 | 108 | ~85 messages + banner + argparse help translated; regex `\[CONFIRM` |
| P06 | B | Console messages — `dev.py`, `run_all.py`, `build.sh` | XS | ✅ Done | 2026-10-25 | 108 | `run_all.py` and `build.sh` translated; `dev.py` was already English |
| P07 | B | Python identifiers — `build.py` (internal names only) | M | ✅ Done | 2026-10-25 | 108 | 6 names in `build.py` + 2 in `run_all.py` |
| P08 | B | Collections naming: `guias`→`guides`, `articulo`→`article` | M | ✅ Done | 2026-10-25 | 108 | folders, keys, types, functions, markers, `/guides/` paths |
| P09 | B | Data/marker names: `textos.json`→`texts.json` and non-English markers | S | ✅ Done | 2026-10-25 | 108 | file renamed; marker audit: no Spanish marker left |
| P10 | B | Tests in English — part 1 | M | ✅ Done | 2026-10-25 | 108 | helpers, constants, `TestSmoke`, `TestMinifyCss`, `TestMinifyHtml` in English |
| P11 | B | Tests in English — part 2 | M | ✅ Done | 2026-10-25 | 108 | collections, domain, markers, geo, safe output, CLI in English |
| P12 | C | `language` setting and derived markers | S | ✅ Done | 2026-10-25 | 108 | `LANGUAGES` table; `{{lang}}`, `{{og_locale}}`, `{{in_language}}` |
| P13 | C | Locale files, loader, dates and shared labels | M | ✅ Done | 2026-10-25 | 109 | `locales/en.json`, `es.json`; `load_locale`, `t()`; +1 test |
| P14 | C | Move generated page copy into locale files | M | ✅ Done | 2026-10-25 | 109 | 30 more locale keys; generic English defaults |
| P15 | C | Configurable collection URL paths | S | ✅ Done | 2026-10-25 | 111 | `collection_paths`; +2 tests |
| P16 | C | Language regression tests | S | ✅ Done | 2026-10-25 | 115 | 4 new tests in `TestLanguageRegression` |
| P17 | D | `site.json`, `entity.json` and engine sample defaults | M | ✅ Done | 2026-10-25 | 115 | English sample values; `language: en`; USD/US |
| P18 | D | `layout.html`, header, footer | S | ✅ Done | 2026-10-25 | 115 | English labels; `{{footer_about}}` neutral text |
| P19 | D | Home page | M | ✅ Done | 2026-10-25 | 115 | English home; GEO section → "Why choose us" |
| P20 | D | Services index | S | ✅ Done | 2026-10-25 | 115 | `servicios/` → `services/`; English copy |
| P21 | D | Sample service page | S | ✅ Done | 2026-10-25 | 115 | `servicio-generico/` → `sample-service/`; English copy |
| P22 | D | Pricing | S | ✅ Done | 2026-10-25 | 115 | `precios/` → `pricing/`; English copy; `$`; one price-0 entry |
| P23 | D | Featured action | S | ✅ Done | 2026-10-25 | 115 | `accion-destacada/` → `featured-action/`; English copy; sample offer `Free Consultation` |
| P24 | D | About | S | ✅ Done | 2026-10-25 | 115 | `sobre-nosotros/` → `about/`; English copy; neutral zone text |
| P25 | D | Contact | S | ✅ Done | 2026-10-25 | 115 | `contacto/` → `contact/`; English copy; generic first-message list |
| P26 | D | Legal notice | S | ✅ Done | 2026-10-25 | 115 | `aviso-legal/` → `legal-notice/`; neutral English template, no statutes |
| P27 | D | Privacy policy | S | ✅ Done | 2026-10-25 | 115 | `politica-de-privacidad/` → `privacy-policy/`; neutral English template |
| P28 | D | Cookie policy | S | ✅ Done | 2026-10-25 | 115 | `politica-de-cookies/` → `cookie-policy/`; neutral English template: no cookies, no storage, no client scripts |
| P29 | D | 404, `llms.txt`, `robots.txt` | M | ✅ Done | 2026-10-25 | 115 | English 404; short generic English `llms.txt` (no GEO text, no JSON block); `robots.txt` policy comment; 10 dead keys removed |
| P30 | D | CSS comments and `.toc` | XS | ✅ Done | 2026-10-25 | 115 | All CSS comments in English; clear 4-line header; unused `.toc` rules removed; compiled CSS 20,384 → 20,338 bytes |
| P31 | E | Dead key and import tidy | XS | ✅ Done | 2026-10-25 | 115 | `lead_strip.lead` already absent; `last_error` removed; imports moved to the top and split one per line |
| P32 | E | Duplicate `@id` error with test | S | ✅ Done | 2026-10-25 | 116 | Duplicate `@id` now fails the build naming the id and the page; +1 test |
| P33 | E | Robust page URL computation with test | S | ✅ Done | 2026-10-25 | 117 | Page URL built from path parts; slug containing `index.html` keeps its URL; +1 test; `dist/` byte-identical |
| P34 | E | Narrow broad `except` clauses, explain fallbacks | S | ✅ Done | 2026-10-25 | 117 | Six JSON parse catches narrowed; page-read errors narrowed; Git fallbacks documented |
| P35 | E | `build.sh` Python check and standalone validator behaviour | S | ✅ Done | 2026-10-25 | 119 | Python 3.8 guard; `--site-url` override precedes import-time validation; +2 tests; output unchanged |
| P36 | E | Technical audit re-run | S | ✅ Done | 2026-10-25 | 119 | V7 rerun; pyflakes unavailable, logged as T-12 |
| P37 | F | Residue sweeps and dead texts | S | ✅ Done | 2026-10-25 | 119 | Removed 33 unused text keys; V4/V5/V6 residues classified; V7 now reports no unused keys |
| P38 | F | Final README | M | ✅ Done | 2026-10-25 | 119 | 170-line README; figures verified; pre-launch sweep corrected |
| P39 | F | Final documentation sync and release check | S | ✅ Done | 2026-10-25 | 119 | Docs synced; both strict build modes pass; owner-confirmed Python compatibility: 3.8.20, 3.9.25, 3.10.22, 3.11.17, 3.12.3, 3.13.17, 3.14.9; T-12 remains blocked by missing pyflakes |

---

## 2. Baseline record (P00)

Recorded before any change to the project, on a clean extraction of the archive.

| Item | Value |
|---|---|
| Source archive | `legible.zip` (sha256 starts `85359964b663bc7a`); original kept untouched |
| Python | 3.13.17 (baseline environment recorded at P00; subsequent owner-confirmed compatible versions are listed in the current summary above) |
| Tests | `python3 -B -m unittest discover tests` → **108 tests, OK** (~8.7 s) |
| Build | `SITE_URL=https://example.com ./legible/build.sh` → success, exit 0 |
| Validator | strict mode: `CHECK PASSED`, `No issues`, `No warnings` |
| Pages generated | 11 |
| HTML after minify | 175,298 bytes |
| CSS after minify | 20,384 bytes |
| Total after minify | 195,682 bytes |
| Files in repository | 36 (excluding `dist/`) |
| Git | initialised locally; baseline commit `P00: baseline` |

Reference numbers to compare against in later phases (they change on purpose in Track D when content is rewritten, but must never silently grow without a reason): pages = 11, tests = 108.

---

## 3. Decisions (DOCUMENTATION.md §5.4)

The plan was handed over for execution as written, so the decisions below are **accepted as proposed** unless the user changes them. Change a row here (and the plan) before the phase it affects.

| # | Decision | Status |
|---|---|---|
| D-1 | Everything in English: code, identifiers, data-file names, sample URLs, README, docs | Accepted |
| D-2 | Default `language: en`; Spanish via `legible/locales/es.json` (engine strings only); site content translated per project | Accepted |
| D-3 | Sample currency USD, country `US`, phone `+15550100`, email `hello@example.com` | Accepted |
| D-4 | Keep `featured_action_*` marker names; URL `/featured-action/` | Accepted |
| D-5 | `type` values `guide` / `article` stay English for all languages | Accepted |
| D-6 | Legal pages become jurisdiction-neutral templates (sample uses neutral placeholders; real sites use `[CONFIRM …]`) | Accepted |
| D-7 | Sample brand assets (legible logo / og-image) stay as placeholders | Accepted |
| D-8 | `DOCUMENTACION.md` replaced by `DOCUMENTATION.md` | Done |

---

## 4. Phase log

Newest first. One entry per executed phase, using this template:

```text
### Pxx — Title  (YYYY-MM-DD)
Result: Done | Partially done | Blocked
Changed: <files and what changed>
Checks run: <commands with real result; test count before → after>
Extra fixes (rule 9): <none | list>
Found, not fixed (→ backlog): <none | list>
Notes / questions for the user: <none | list>
Commit: <hash> "Pxx: title"
```

### P39 documentation update — Python compatibility confirmation (2026-10-25)
Result: Done (documentation-only update based on the project owner’s manual verification).
Changed: `README.md` and `DOCUMENTATION.md` now list the seven confirmed interpreter versions: Python 3.8.20, 3.9.25, 3.10.22, 3.11.17, 3.12.3, 3.13.17 and 3.14.9. `STATUS.md` records the same list in the current summary and phase tracker. The notes explicitly distinguish successful operation reported by the owner from running the complete 119-test suite and both strict builds on each interpreter. No application code or tests changed.
Checks run: documentation text and status consistency checked; ZIP integrity and forbidden build/cache artifact checks run before delivery. No Python tests/builds were rerun for this documentation-only update, and no Git commands were run.
Found, not fixed (→ backlog): T-12 remains open because `pyflakes` is not installed; F-15 remains documented design debt.
Commit: n/a (the user commits)

### P39 — Final documentation sync and release check (2026-10-25)
Result: Done with one tooling limitation documented as T-12. `STATUS.md` is retained in the release as the phase/control log required by §0.1; it records the exact phase state and open work.
Changed: `DOCUMENTATION.md`: release header refreshed for P39 and 119 tests; final review verdict updated; findings F-01–F-14 explicitly marked closed with their resolution phases; F-15 retained as intentional debt; technical findings T-02, T-04, T-06, T-09 and T-10 closed, and T-11 labelled as documented; technical audit summary aligned with the actual release checks. `STATUS.md`: P39 marked complete, all 40 planned phases marked done, latest test/build results refreshed, and the remaining static-analysis limitation kept in the backlog. No application code, site content or tests were changed.
Checks run: all 13 test classes invoked separately → **119 tests passed** (5 + 1 + 29 + 20 + 15 + 12 + 4 + 7 + 5 + 4 + 4 + 8 + 5 = 119). `python3 -B -m unittest discover tests` and verbose discovery did not terminate reliably here, so combined discovery is not claimed as passing. Default `SITE_URL=https://example.com ./legible/build.sh` (with `RENDER_GIT_BRANCH=unknown RENDER_GIT_COMMIT=unknown` to avoid invoking Git) → strict validator passed, 11 pages, zero issues/warnings. The same command with `CSS_MINIFY=FALSE` → strict validator passed, 11 pages, zero issues/warnings. `python3 -m pyflakes legible tests` → could not run (`No module named pyflakes`); T-12 remains open. Documentation link/anchor audit, Python AST parsing, JSON parsing, `bash -n legible/build.sh`, source-tree sweeps and archive-artifact checks completed before packaging. No Git repository state was changed and no commit was created; the release builds supplied fallback metadata values to avoid Git metadata probes. No application code changed.
Extra fixes (rule 9): none.
Found, not fixed (→ backlog): T-12 — `pyflakes` is unavailable in this environment; rerun in an environment where the package is already installed or can be installed. F-15 remains documented design debt.
Notes / questions for the user: the 40 phases specified in `DOCUMENTATION.md` are complete; a further phase needs a new scope.
Commit: n/a (the user commits)

### P38 — Final README (2026-10-25)
Result: Done. README reduced to the requested 150–220-line range and reorganized in the specified order.
Changed: `README.md`: 170 lines; removed the old detailed section sprawl in favour of the required Overview → Features/At a glance → Requirements → Quick start → Configure → Language support → Project layout → How it works → Validation → Deployment → Scope → Contributing → License → Author order. Corrected stale claims that the template was Spanish and that Python 3.8–3.14 had all been tested; now records the actually observed Python 3.13.5 environment and verified 119-test / 11-page figures. Removed unsupported validator-count and page-size ranges. Replaced the pre-launch sweep with the pattern in `DOCUMENTATION.md` §9.4, excluding the word `legible` that caused false positives. Long-form configuration, collection, validator, command, marker and AI-agent details remain in `DOCUMENTATION.md`. `STATUS.md`: advanced tracker to P39.
Checks run: V1 strict build with `SITE_URL=https://example.com` → exit 0, 11 pages, `CHECK PASSED`, zero issues/warnings; `./legible/build.sh` with the sample URL from `site.json` → same result. The 119 tests passed across all 13 classes when run independently; `python3 -B -m unittest discover tests` did not terminate reliably within the environment's 120-second command limit, so no green result is claimed for that single invocation. The test-class counts sum to 119. `python3 legible/dev.py --port 3001` served `/` with HTTP 200 and a title, then was stopped. Pre-launch sweep executed: 130 matches, all sample content in the generic starter to review before a real launch; pattern does not include `legible`. All 14 README markdown links and their local anchors resolve. README length: 170 lines. No application code or site content changed.
Extra fixes (rule 9): none.
Found, not fixed (→ backlog): T-12 — `pyflakes` remains unavailable in this offline environment; retained for P39.
Notes / questions for the user: none.
Commit: n/a (the user commits)

### P37 — Residue sweeps and dead texts (2026-10-25)
Result: Done; all three residue sweeps now return only documented allowed exceptions.
Changed: `src/data/texts.json`: removed all 33 keys that V7 found unused (old guide/sample copy, action include/not-include/after steps, and several service detail keys). The file now contains 119 keys and the exact V7 marker scan reports `no unused keys`. `README.md`: replaced a stale quoted Spanish description of the sample copy with its current English wording. `DOCUMENTATION.md`: documented why historical migration references, the Spanish localization example, the Spanish locale/test fixtures and the expected engine `geo`/AI-crawler tokens are valid sweep exceptions; marked T-01 closed.
Checks run: V1 baseline after the edits → 119 tests passed; strict build and validator pass, 11 pages, zero errors/warnings. `dist/` compared with a fresh P36 build → byte-identical. V4 accent and Spanish-word scans show only the documented locale/test/example/history hits; V5 shows only the 11 `geo:` front-matter flags, `{{geo}}` engine marker and `PerplexityBot` robots entry; V6 shows only historical references in `STATUS.md`/`DOCUMENTATION.md` and the valid custom Spanish `collection_paths` examples in `README.md`. V7 unused-key scan → `no unused keys`; `bash -n legible/build.sh` and Python compile checks → OK. `pyflakes` remains unavailable due to the P36 environment limitation; T-12 stays open for P39.
Extra fixes (rule 9): one stale Spanish phrase in README translated to accurately describe the English starter content.
Found, not fixed (→ backlog): T-12 — rerun `pyflakes` on a network-enabled development environment in P39.
Notes / questions for the user: none.
Commit: n/a (the user commits)

### P36 — Technical audit re-run (2026-10-25)
Result: Done with one tooling limitation logged as T-12.
Changed: `STATUS.md` and `DOCUMENTATION.md` only. No application code changes were justified by the audit. Refreshed finding T-01 from 34 historical unused `texts.json` keys to 33 keys confirmed by the current scan; clarified P37's starting count. Added T-12 for the unavailable `pyflakes` static-analysis check.
Checks run: Strict V1 build with `SITE_URL=https://example.com` → exit 0, 11 pages, `CHECK PASSED`, no issues/warnings. `dist/` compared with the P35 output → byte-identical. All 119 tests passed when the 13 test classes were run separately (class counts sum to 119); a single consolidated `unittest discover` invocation did not terminate reliably in this container, so the test classes were rerun individually. `python3 -B -m py_compile legible/build.py legible/dev.py legible/check_site.py legible/run_all.py tests/test_legible.py` → OK; `bash -n legible/build.sh` → OK. No unsafe `target="_blank"` links; all `<img>` tags have explicit `width` and `height`; CSS class comparison clean except intentional `band-cta` and `footer-brand` hooks; no source CSS classes are unused once generated `active` and `post-meta` classes are included. No inline `style=` or `!important`; no bare `except:`. The two remaining `except Exception` clauses are the documented non-fatal Git metadata fallbacks in `build.py`. Invalid `SITE_URL`, invalid `--minify`, and a missing validator directory each exit 1 with a useful message. The unused-text scan reports 33 keys, deferred to P37 as planned. `python3 -m pyflakes legible tests` could not run: module absent, and pip installation failed because DNS/network access is unavailable.
Extra fixes (rule 9): none.
Found, not fixed (→ backlog): T-12 — pyflakes could not be installed, so undefined names/unused variables are not fully ruled out by the fallback checks.
Notes / questions for the user: none.
Commit: n/a (the user commits)

### P35 — Script robustness: `build.sh` and standalone validator behaviour  (2026-10-25)
Result: Done
Changed: `legible/build.sh`: added an early Python ≥3.8 guard using `python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))'`; on failure, the script prints a clear minimum-version message and exits before building. `legible/check_site.py`: reads `--site-url VALUE` and `--site-url=VALUE` from the standalone CLI and sets `SITE_URL` before importing `build.py`, so the explicit CLI override takes effect before the latter's import-time config validation. The missing/invalid URL without an override still fails early with the existing clear error. Added comments in `check_site.py` and at `build.py`'s lazy import documenting the intentional circular import. `tests/test_legible.py`: added 2 regressions (reject simulated Python 3.7; override invalid `site.json` URL using both `--site-url` forms). `README.md`: automated test count updated 117 → 119.
Checks run: baseline V1 → **117 tests OK** (53.36 s); after → **119 tests OK** (58.23 s). `SITE_URL=https://example.com ./legible/build.sh` → strict build and validation passed, 11 pages, no errors/warnings. `python3 legible/check_site.py --site-url https://example.com --strict` after the build → exit 0, `Site checks passed`. Regression test confirms that, after changing `site.json` to an invalid `http://` URL, invoking the validator without an override fails clearly and both explicit CLI override forms pass. `bash -n legible/build.sh` and `python3 -B -m py_compile legible/build.py legible/check_site.py tests/test_legible.py` → OK. `diff -r` between the P34 and P35 `dist/` folders built with `SITE_URL=https://example.com` → identical, byte for byte. No Git commands were executed, and no Git metadata was created or altered, per user instruction.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none new. `pyflakes` is not installed in this environment; no dependency was added.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P34 — Narrow broad `except` clauses, explain fallbacks  (2026-10-25)
Result: Done
Changed: `legible/build.py`: changed the page JSON-LD parse catch, HTML minifier JSON-LD fallback and `page_date_modified` JSON parse catch from `Exception` to `ValueError`; the minifier fallback now has a comment explaining that malformed JSON-LD is preserved unchanged. In `get_git_info`, retained the two broad `Exception` catches because Git metadata is optional and any Git failure must remain non-fatal; added one-line comments documenting those fallbacks. `legible/check_site.py`: changed the JSON-LD parsing catches in `check_jsonld`, `check_faq_matches_schema` and sitemap date consistency to `ValueError`; narrowed page read/parse reporting from `Exception` to `(OSError, UnicodeError, ValueError)`. No tests or README changes were needed; the suite remains at 117 tests.
Checks run: V1 → **117 tests OK** (55.12 s). Strict build → **BUILD SUCCESS**, 11 pages, no warnings. Built once from the original P33 archive and once from the P34 source with `SITE_URL=https://example.com`; `diff -qr` of the two output directories returned no differences. `python3 -B -m py_compile legible/build.py legible/check_site.py` OK; `bash -n legible/build.sh` OK. V7 review: only the two documented Git-info broad catches remain; no `target="_blank"` links lack `noopener`; validator on `/nonexistent` returns exit 1 as expected. `python3 -m pyflakes legible tests` could not run because `pyflakes` is not installed in this environment; no dependency was added.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none
Notes / questions for the user: the optional page-specific `JSON-LD parse error` message proposed in P33 was not added; it is outside this phase card and remains untouched. No Git commands or repository changes were performed.
Commit: n/a (the user commits)

### P33 — Robust page URL computation with test  (2026-10-25)
Result: Done
Changed: `legible/build.py`, in `build()` (page loop): the page URL was `'/' + str(path).replace('index.html', '')…`, which also removed `index.html` from inside a folder name. It is now built from the path parts: `404.html` keeps its special case (`/404.html`); otherwise only a final `index.html` component is dropped, the rest is joined with `/` and a trailing `/` is added (the home stays `/`). The old `.replace('\\', '/')` for Windows separators is no longer needed because `Path.parts` is already split. `tests/test_legible.py`: +1 test, `test_slug_containing_index_html_keeps_its_url` (in `TestSpecialCharactersAndWarnings`): a temp project with a copy of the About page in `src/pages/my-index.html-guide/index.html`; it asserts that the built page has `canonical` and `og:url` ending in `/my-index.html-guide/` and no `my--guide`. `README.md`: test count 116 → 117.
Checks run: V1 before → 116 tests OK, strict build `CHECK PASSED`; after → **117 tests OK**, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Reproduced the bug by hand before the change on a copy of the project: the file was written to the right folder (`out_path` uses the real path) but `canonical` and `og:url` said `https://example.com/my--guide/`. The new test was run against the previous code and failed there (`'/my-index.html-guide/' not found` in the page) and passes with the fix. **`diff -r` of `dist/` taken just before the change and `dist/` after it: no differences** (the template output is byte-identical). `grep "replace('index.html'" legible/*.py` now returns nothing; `check_site.py` has no similar computation.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none. Note for whoever reads the test failure output: when the assertion fails, `unittest` prints the whole page in the message (long but harmless).
Notes / questions for the user: P34 is next. It is also where I proposed (in P32) adding the page name to the `JSON-LD parse error` message (about 3 lines plus a test, which would make 118 tests); say yes or no before I start it, otherwise I leave it out and P34 stays strictly as in its card.
Commit: n/a (the user commits)

### P32 — Duplicate `@id` error with test  (2026-10-25)
Result: Done
Changed: `legible/build.py`: in `render_jsonld`, the silent `return ''` for a page node whose `@id` is already used by an entity node (`src/data/entity.json`) is now a `ValueError` saying `duplicate JSON-LD @id "<id>": it is already defined in src/data/entity.json. Rename the @id of this page node.` (the id is shown with `{{site_url}}` already resolved). No signature changed. In `compose_page`, the call to `render_jsonld` is wrapped so the error reaches the user as `✗ BUILD FAILED: page <url>: …` through `sys.exit`, the same style `check_unrendered` already uses (a plain `ValueError` would have escaped as a traceback, because the `try/except ValueError` in `build()` only covers the sitemap and `llms.txt`, not the page loop). The silent behaviour was not deliberate (it dropped the page's whole JSON-LD and the user then saw only "indexable page without JSON-LD"), so F-12 is fixed rather than documented. `tests/test_legible.py`: +1 test, `test_duplicate_jsonld_id_fails_the_build_and_names_the_id_and_the_page` (in `TestSpecialCharactersAndWarnings`): a temp project whose `about` page repeats `{{site_url}}/#business`; it asserts a non-zero exit, `BUILD FAILED`, the message text, the `@id` and `/about/` in stderr, and no `Traceback`. `README.md`: test count 115 → 116.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → **116 tests OK**, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Reproduced by hand before the change (a copy of the project with the duplicate node in `about`): exit 1 with only `about/index.html → indexable page without JSON-LD` in the report and the page written without JSON-LD. After the change, the same copy prints `✗ BUILD FAILED: page /about/: duplicate JSON-LD @id "https://example.com/#business": it is already defined in src/data/entity.json. Rename the @id of this page node.` and exits 1. The new test was run against the previous `build.py` and failed there (`0 == 0 : a duplicate @id must fail the build`), then passes with the fix. `diff -rq` of `dist/` against the output measured before P30: only `css/site.css` differs (P30), so valid input produces the same output as before.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the other `ValueError` in `compose_page` (`JSON-LD parse error: …`, a page whose JSON-LD is not valid JSON) and the `no dateModified` error in the sitemap code have the same weakness: the first escapes as a traceback and does not name the page. Not touched here (outside the card). It could be handled with the same one-line `sys.exit` pattern; proposed for P34 (narrowing `except` clauses) if you agree. A node repeated inside the page's own `@graph` (not an entity id) is still not detected; not part of F-12.
Notes / questions for the user: do you want the page-naming fix for the JSON-LD parse error added in P34? It is about 3 lines plus a test.
Commit: n/a (the user commits)

### P31 — Dead key and import tidy  (2026-10-25)
Result: Done
Changed: `legible/build.py`: the one-line `import os, re, json, html, shutil, sys, subprocess` is now one import per line in alphabetical order (`html`, `json`, `os`, `re`, `shutil`, `subprocess`, `sys`) plus `import textwrap`, which used to sit inside `report_lines` and is now at the top (the `sys.dont_write_bytecode` line and the `from` imports keep their place). `legible/dev.py`: removed the unused `last_error` variable and its `nonlocal`; `rebuild()` now prints `Build failed:` and `out + err`, or `Build OK`, exactly as before; `import threading` moved from inside `main` to the top, between `sys` and `time`. `src/data/site.json`: nothing to remove, see below.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. `grep -n "lead_strip" legible/build.py`: the code reads only `action_label`, `eyebrow`, `headline`, `button`, `action_url` and the locale key `lead_strip_lead_html`, never a `lead` key; `site.json` `generated_content.lead_strip` already holds only `action_url`, so the dead key from finding F-08 was already gone in the P27 archive and there was nothing to delete. `diff -rq` of `dist/` against the output measured before P30: no file differs except `css/site.css` (changed on purpose in P30), so the HTML, sitemap, `llms.txt` and `robots.txt` are unchanged. `python3 -m py_compile legible/build.py legible/dev.py` OK. `python3 legible/dev.py --port 3917`: it built, `GET /` and `GET /contact/` returned 200, and it stopped cleanly on SIGINT (`Stopping dev server`, process gone).
**V7 limit:** `pyflakes` could not be installed here (no network access in this environment: `No matching distribution found`), so V7 was NOT run as written. In its place I ran an AST check for unused imports over `build.py`, `dev.py`, `check_site.py`, `run_all.py` and `tests/test_legible.py` (result: none unused). That is weaker than pyflakes (it does not catch undefined names or unused variables), so please run `python3 -m pyflakes legible tests` on your machine; P36 re-runs V7 anyway.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none
Notes / questions for the user: please run `python3 -m pyflakes legible tests` locally and tell me if it reports anything; I will fix it in P32 or P36.
Commit: n/a (the user commits)

### P30 — CSS comments and `.toc`  (2026-10-25)
Result: Done
Changed: `src/css/site.css`: the header comment is now 4 clear lines in English (no JavaScript, no motion, no downloaded fonts, no costly effects; mobile-first; terminal look with the logo palette). The 11 section titles and every other comment (about 40, from the token notes to the WhatsApp button) are translated; the section titles keep the same width. One comment named the featured-action link in Spanish ("Auditoría gratis", "página de auditoría"); it now says "Featured-action link … its own page" (the rule it describes, `a.nav-action` / `.active`, is unchanged). A comment that referred to "the beta" now just describes the header and menu sizes. The unused `.toc` selectors were removed from the three "Related links" rules (`.related-links, .toc`, `.related-links a, .toc a`, and the hover/focus rule); the `.related-links` declarations are untouched. `README.md` (CSS hooks note): the sentence saying `toc` is defined but unused is gone. No other file mentions `toc` outside the plan and this log.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Compiled CSS: 20,384 bytes before → 20,338 bytes after (smaller by 46 bytes, from the `.toc` selectors). `diff -rq` of `dist/` before and after: the only differing file is `css/site.css`, so every HTML page, `sitemap.xml`, `llms.txt` and `robots.txt` is byte-identical. Confirmed no page, partial, layout or `build.py` output uses a `toc` class before deleting it (`grep -w toc` over `src`, `legible`, `tests`). No Spanish-looking comment left; the only non-ASCII characters inside comments are `·` and `✓`, already in the original.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none
Notes / questions for the user: none
Commit: n/a (the user commits)

### P29 — 404, `llms.txt`, `robots.txt`  (2026-10-25)
Result: Done
Changed: `src/pages/404.html`: English copy (title `Page Not Found | …`, h1 `404 - Page not found`, lead, "What can you do?" and the four links); `robots: noindex, follow`, `geo: false`, `canonical: none` unchanged. `src/static/llms.txt`: rewritten as a short generic English index (142 lines in the build, was about 205) with the same markers: business facts, which service fits which situation, pages, services with price and scope, limits and transparency, contact, 9 FAQs, sitemap and machine-readable files; `{{llms_guides}}`, `{{llms_blog}}` and `{{llms_sitemap_extra}}` kept. Removed: the GEO explainer section (`{{geo_topic}}`), `{{geo_description}}`, "why isn't my business on Google Maps", the reviews, directories and Google-listing wording, the "Structured Data Summary" JSON block (it hard-coded `EUR` and gave Service 3 a monthly duration, and the real JSON-LD is on every page) and the "Generated for SEO and GEO" footer. Corrections of old content that was wrong for the sample: prices now carry `$` like the pages; the "both services" row now shows `{{service_1_name}} + {{service_2_name}}` at `{{bundle_price}}` (as the services page does) instead of Service 3; Service 3 is listed as "one-off or monthly" (as the pricing page says), Service 5 and the bundle are listed (the pricing and services pages show them), Service 4 is the only "monthly" one; the FAQ now mirrors the 9 questions of the home page (same answers); facts that no page states (no premises, "same business day", "no fake reviews", the "not included by default" list) were dropped or aligned with the pages (reply within one business day, Mon–Fri 09:00–19:00, cancel with 7 days of notice, extra work at `{{extra_hourly_rate}}/h`). `src/static/robots.txt`: two comment lines at the top explaining the policy (crawlers welcome by design; how to block one); the rules are unchanged. `src/data/texts.json`: `value_proposition` and `differentiators` translated (2 values, only `llms.txt` used them); removed 10 keys that this rewrite left unused and that held Spanish or agency text: `geo_description`, `geo_topic`, `first_paid_service`, `faq_2_answer`, `faq_6_answer`, `faq_7_answer`, `faq_10_answer`, `faq_11_answer`, `faq_13_answer`, `faq_14_answer` (the card of P19 had already asked to remove `geo_topic` and `geo_description`; they were still used by `llms.txt`). 162 → 152 keys. README and DOCUMENTATION need no change (their description of `robots.txt` and `llms.txt` is still correct).
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. `dist/llms.txt` read end to end: no unresolved `{{`, no `CONFIRM`, no accented letter, no `€`. Built `404.html`: `robots` `noindex, follow`, one `h1`, no canonical, no unresolved `{{`. `dist/robots.txt` read: comments first, rules unchanged, sitemap line last. V4 on the three files → none. V5 on `404.html`, `llms.txt` and `texts.json` → only the `geo: false` front-matter flag (allowed, §9.4). V6/V3 for `geo_topic|geo_description|first_paid_service` → hits only in this log, the P19 log and the plan (DOCUMENTATION F-03 and the P19 card).
Extra fixes (rule 9): none beyond the data corrections above, which are part of rewriting `llms.txt`.
Found, not fixed (→ backlog): V7 now lists 33 unused `texts.json` keys (`action_include_1…5`, `action_not_include_1…4`, `after_1…3`, `featured_action_faq_includes`, `featured_action_limit_short`, `featured_action_meta_description`, `featured_action_not_includes_lead`, `guide_1…3_title` and `_summary`, `guide_topic_1…3`, `guides_intro`, `service_2…5_faq_includes` (4 keys), `service_3_delivery`, `service_4_delivery`, `value_props`); the `guide_*` ones still hold Spanish text. All go to P37.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P28 — Cookie policy `/cookie-policy/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/politica-de-cookies/` → `src/pages/cookie-policy/`. The only link to it, in `footer.html`, now points to `/cookie-policy/` (the page is `noindex`, so it is not in the sitemap or `llms.txt`). `src/pages/cookie-policy/index.html`: rewritten as a neutral English template with 7 sections (what are cookies, what this website uses, links to other services, managing cookies in your browser, if cookies are added later, changes, contact). It now matches what the template really does: no cookies, no local storage, no trackers or statistics tools, no scripts run in the browser (the mobile menu is a CSS checkbox), no external fonts or images, and `mailto:` / `wa.me/` are plain links. The new section 5 explains what to change if cookies are added later (list each cookie, check whether prior consent is required and add a consent mechanism, update the privacy policy, update the statements and the `updated` date). A visible note under the lead says it is a template to review with a lawyer. Removed: the LSSI art. 22.2 / AEPD reference, the invented `session_id` and `lang` cookies and their table, the `localStorage` `nav-toggle` claim, the language-preference and session cookies, and the four browser help links (see Notes). `robots: noindex, follow`, `geo: false` unchanged; `updated` `2026-10-25`; title `Cookie Policy | Your Business`, description 140 characters; anchor ids `que-son-title`, `que-usamos-title`, `tabla-title`, `terceros-title`, `gestion-title`, `cambios-title`, `contacto-title` → `what-title`, `use-title`, `links-title`, `manage-title`, `later-title`, `changes-title`, `contact-title` (no CSS, test or link used them). The page keeps `{{site_name}}`, `{{contact_email}}` and `{{last_update}}`.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/cookie-policy/` exists and `dist/politica-de-cookies/` does not; `robots` `noindex, follow`; one `h1`; no unresolved `{{`; no `CONFIRM`; no accented letter; "Last updated: 2026-10-25"; the home links to `/cookie-policy/` from the footer. Claim check on `dist/`: the only `<script>` tags are the 7 `application/ld+json` blocks (data, not executable), and nothing contains `localStorage`, `document.cookie` or `Set-Cookie`; `site.css` has no `url(` or `@font-face`. V3 for `politica-de-cookies` → hits only in `DOCUMENTATION.md` lines 285 and 597 (rename table and phase card, which are the plan). V4 on the page → none. V5 on the page → only the `geo: false` front-matter flag (allowed engine feature, §9.4); the word "analytics" was first used in the text and was reworded to "visitor statistics".
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none new. `llms.txt` lines 17 and 205 still print `{{last_update}}` inside Spanish text (P29). The old cookie page contradicted the template (it claimed session and language cookies and `localStorage` that the site never used); that is now resolved.
Notes / questions for the user: the browser help links (Chrome, Firefox, Safari, Edge) were removed on purpose: the Chrome one is on a `google.com` domain, which the V5 sample-content sweep forbids in `src/pages`, and help URLs change often. Section 4 gives generic instructions instead. If you prefer the links, say so and I add them (with `rel="noopener noreferrer"`) and record `google` as an allowed exception for that URL.
Commit: n/a (the user commits)

### P27 — Privacy policy `/privacy-policy/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/politica-de-privacidad/` → `src/pages/privacy-policy/`. The only link to it, in `footer.html`, now points to `/privacy-policy/` (the page is `noindex`, so it is not in the sitemap or `llms.txt`). `src/pages/privacy-policy/index.html`: rewritten as a neutral English template with the same 10 sections (data controller, purposes, legal bases, data collected, recipients, rights, retention, security, minors, changes). Removed: GDPR/LOPD-GDD and AEPD references, "Google Business Profile, Google Search Console, Analytics", "SEO tools", "CMS/hosting access" and "Google listing" data, and the "minors under 14" age. Data are stated as collected by email or WhatsApp; the page says the website uses no forms, cookies or tracking scripts (consistent with the template and with the cookie page rewrite in P28); the complaint goes to "the competent data protection authority in your country"; retention uses generic periods (1 year for enquiries, "the period required by tax and accounting law", until consent is withdrawn). The page keeps `{{site_name}}`, `{{location}}`, `{{contact_email}}`, `{{site_url}}`, `{{featured_action_name}}`, `{{service_1…5_name}}` and `{{last_update}}`. A visible note under the lead says it is a template to adapt to the real data practices and local law and to have reviewed by a lawyer. `robots: noindex, follow`, `geo: false` unchanged; `updated` `2026-10-25`; title `Privacy Policy | Your Business`, description 136 characters; anchor ids `responsable-title`, `finalidad-title`, … → `controller-title`, `purposes-title`, `bases-title`, `data-title`, `recipients-title`, `rights-title`, `retention-title`, `security-title`, `minors-title`, `changes-title` (no CSS, test or link used them). `src/data/texts.json`: `last_update` `2026-10-20` → `2026-10-25` (the page prints it; value only).
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/privacy-policy/` exists and `dist/politica-de-privacidad/` does not; `robots` `noindex, follow`; one `h1`; no unresolved `{{`; no `CONFIRM`; no accented character; "Last updated: 2026-10-25". V3 for `politica-de-privacidad` → no hits outside the plan/log. Sweep for `rgpd|lopd|aepd|search console|analytics|seo|google|ficha|cms` on the page → none.
Extra fixes (rule 9): `last_update` value bumped to match the page's new `updated` date (1 line, data only; it also feeds `llms.txt` and the cookie page).
Found, not fixed (→ backlog): the cookie policy still says (in Spanish) that technical cookies are used, which contradicts the privacy page statement of no cookies until P28 rewrites it to "no cookies, no trackers, no client scripts" as its card says. `llms.txt` lines 17 and 205 still print `{{last_update}}` inside Spanish text (P29). The placeholders for legal data in the privacy page are the resolved markers (`{{location}}` etc.), not `Your …` text, so a real site gets them from `site.json`.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P26 — Legal notice `/legal-notice/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/aviso-legal/` → `src/pages/legal-notice/`. The only link to it, in `footer.html`, now points to `/legal-notice/` (the page is `noindex`, so it is in neither `sitemap_base_order`, `sitemap.xml` nor `llms.txt`). `src/pages/legal-notice/index.html`: rewritten as a jurisdiction-neutral English template with 9 sections (owner identification, purpose, terms of use, intellectual property, disclaimer and liability, links, general provisions, changes and duration, governing law). No Spanish statute (the LSSICE reference and "normativa española" are gone) and no Spanish court wording. Owner identification uses the neutral placeholders `Your legal name`, `Your registered address`, `Your registration number` and `Your jurisdiction` (governing law and courts) next to `{{site_name}}`, `{{contact_email}}` and `{{site_url}}`; a visible note under the lead says it is a template to be reviewed by a qualified lawyer. `robots: noindex, follow` and `geo: false` unchanged; `updated` `2026-10-25`; title `Legal Notice | Your Business`, description 138 characters; anchor ids `datos-title`, `objeto-title`, … → `identification-title`, `purpose-title`, `terms-title`, `ip-title`, `liability-title`, `links-title`, `general-title`, `changes-title`, `law-title` (no CSS, test or link used them). `README.md` (launch note 12, pre-launch sweep) and `DOCUMENTATION.md` (§7.3 rule 10, §9.4 pre-launch sweep): "aviso legal" → "legal notice", the sweep now also catches `Your legal name|Your registered address|Your registration number|Your jurisdiction`, and both say the sample uses these placeholders while real sites use `[CONFIRM …]`.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/legal-notice/` exists and `dist/aviso-legal/` does not; `robots` `noindex, follow`; one `h1`; no unresolved `{{`; zero occurrences of `CONFIRM` (so the strict validator does not warn); no accented character; the home links to `/legal-notice/` from the footer. V3 for `aviso-legal` → no hits outside the plan/log. Sweep for Spanish law/jurisdiction wording on the page → none.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the footer label `Legal notice` was already English (P18). The placeholders are plain text, so the validator cannot flag them on a real project; the pre-launch sweep (README/§9.4) is the check that catches them. The privacy and cookie pages still carry Spanish copy (P27, P28).
Notes / questions for the user: none
Commit: n/a (the user commits)

### P25 — Contact `/contact/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/contacto/` → `src/pages/contact/`. Every `/contacto/` URL replaced by `/contact/` in `footer.html`, `src/pages/404.html`, `src/static/llms.txt` (URLs only), `src/data/site.json` (`sitemap_base_order`), the default `SITEMAP_BASE_ORDER` in `legible/build.py` and the `http://YOUR-DOMAIN.com/contacto/` fixture of `test_internal_http_link_is_an_error` in `tests/test_legible.py` (the test is unchanged otherwise). `src/pages/contact/index.html`: all copy, breadcrumb (visible and JSON-LD) and `aria-label` in English; title `Contact | Your Business`, description 130 characters; form-free as before (mailto and WhatsApp only), the mailto subject/body are English ("Enquiry from the website", "Tell us what you need and share any relevant links or details."); the first-message list now asks for "Any relevant links or details, if you have them" instead of the website and Google listing; the opening-hours row "Urgencias WordPress" is now the generic "Urgent requests" (subject "URGENT"); the response time reads "within one business day" like the services page; 3 FAQ questions and answers equal to the JSON-LD; anchor ids `primer-mensaje-title`, `horario-title`, `ubicacion-title`, `faq-contacto-title` → `first-message-title`, `hours-title`, `location-title`, `faq-contact-title` (no CSS, test or link used them); `updated` and `dateModified` `2026-10-25`. `src/data/texts.json`: English values for `contact_lead` (no "online presence" or website wording), `contact_email_description`, `contact_whatsapp_description`, `contact_action_description`, `contact_location_description`.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/contact/` exists and `dist/contacto/` does not; one `h1`; 312 words in `<main>`; no unresolved `{{`; no accented character; 3 FAQ questions and 3 answers equal to the JSON-LD; `sitemap.xml` and `llms.txt` list `/contact/`. V3 for `/contacto/`, `pages/contacto` → no hits outside the plan/log. Spanish/agency sweep (V4/V5 patterns) on the page source and on the `contact_*` values → none (the `grep -E` accent class also matches the en dash `–` in this shell's locale; a Python check on the built page found no accented character).
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the remaining `contacto` hits are Spanish prose in pages not yet rewritten (privacy policy "Datos de contacto" → P27; cookie policy id `contacto-title` and heading "7. Contacto" → P28) and in `llms.txt` (line 36 description, line 96 WhatsApp sentence → P29). The header menu has no Contact link (only the footer), unchanged.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P24 — About `/about/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/sobre-nosotros/` → `src/pages/about/`. Every `/sobre-nosotros/` URL replaced by `/about/` in `header.html`, `footer.html`, `src/pages/index.html`, `src/static/llms.txt` (URLs only), `src/data/site.json` (`sitemap_base_order`) and the default `SITEMAP_BASE_ORDER` in `legible/build.py`. `src/pages/about/index.html`: all copy, breadcrumb (visible and JSON-LD) and `aria-label` in English; title `About us | Your Business`, description 127 characters (the zone is `{{coverage_area}}`); headings "Who we are", "How we work", "Our principles", "Where we work"; anchor ids `quienes-title`, `como-title`, `valores-title`, `zona-title` → `who-title`, `how-title`, `principles-title`, `area-title` (no CSS, test or link used them); principle headings no longer mention positions or Google ("No guaranteed outcomes"); `updated` and `dateModified` `2026-10-25`. `src/data/texts.json`: English values for `about_lead`, `about_who_we_are`, `about_mission` (no Google/Maps/AI wording), `how_1…4_description`, `principle_1…4`, `about_zone_description` (now "We work with businesses in `{{coverage_area}}`. Knowing the local area helps us understand what your nearby customers really need…", no keywords or Google listing) and `about_remote_description`. `tests/test_legible.py`: the page path used by the two marker tests and the "must say which page it is on" assertion now use `about` and `/about/` (4 lines; assertions not weakened).
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/about/` exists and `dist/sobre-nosotros/` does not; one `h1`; 305 words in `<main>`; no unresolved `{{`; no accented character; `sitemap.xml` and `llms.txt` list `/about/`. V3 for `sobre-nosotros` → no hits outside the plan/log. Spanish/agency sweep (V4/V5 patterns) on the page source and on the `about_*`, `how_*`, `principle_*` values → none.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `llms.txt` line 35 keeps its Spanish description ("Quiénes somos y cómo trabajamos") around the new URL (P29). `contacto/` and the three legal pages still carry Spanish copy (P25–P28). The home text that says "read how we work" links to `/about/` as before.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P23 — Featured action `/featured-action/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/accion-destacada/` → `src/pages/featured-action/`. Every `/accion-destacada/` URL replaced by `/featured-action/` in `header.html`, `footer.html`, `src/pages/index.html`, `services/index.html`, `services/sample-service/index.html`, `pricing/index.html`, `contacto/index.html`, `sobre-nosotros/index.html`, `404.html`, `src/static/llms.txt` (URLs only), `src/data/site.json` (`sitemap_base_order` and `generated_content.lead_strip.action_url`), `src/data/entity.json` (offer and service URLs), the default `SITEMAP_BASE_ORDER` in `legible/build.py` and `README.md` (launch notes). `src/pages/featured-action/index.html`: rewritten in English: title `Free Consultation | Your Business`, description 101 characters, breadcrumb (visible and JSON-LD), facts, included/not-included lists, conditions, "What happens next?" steps, 4 FAQ questions equal to the JSON-LD, related links, lead strip; `serviceType` `Initial consultation`; `areaServed` now `{{city_1…4}}` (was hard-coded `Ciudad 1…4`); `priceCurrency` `EUR` → `USD` (2 places); the pre-filled WhatsApp text and email subject use `{{featured_action_name_url}}` and no longer ask for a website; anchor ids `que-incluye-title`, `no-incluye-title`, `despues-title` → `includes-title`, `not-included-title`, `after-title` (no CSS, test or link used them); `updated` and `dateModified` `2026-10-25`. Removed the "changes to your website or Google listing" wording and the "we analyse your website, Google listing…" step. `src/data/entity.json` and the `build.py` fallback: sample offer `Featured Action` → `Free Consultation`. `src/data/texts.json`: English values for `featured_action_meta_description/delivery/limit/description/faq_includes/not_includes_lead/ideal_for/not_includes/limit_short/limit_note`, `action_include_1…5`, `action_not_include_1…4` (4 is the Google-listing one, now generic) and `after_1…3`. `README.md` and `DOCUMENTATION.md` (dictionary row, §7.3 sample-values list, §9.4 pre-launch sweep) now say `Free Consultation` instead of `Featured Action`.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/featured-action/` exists and `dist/accion-destacada/` does not; one `h1`; 354 words in `<main>`; no unresolved `{{`; no accented character or `€`; 4 FAQ questions equal to the JSON-LD; every `priceCurrency` is `USD`; WhatsApp link `…the%20Free%20Consultation%20for%20my%20business…`, mailto subject `Free%20Consultation`; `sitemap.xml` and `llms.txt` list `/featured-action/`; the home shows the offer name `Free Consultation` and still exactly one price-0 offer. V3 for `accion-destacada` → no hits outside the plan/log. Spanish/agency sweep (V4/V5 patterns) on the page source → none.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `action_include_1…5`, `action_not_include_1…4` and `after_1…3` are not used by any page or by `llms.txt` (the page text is written directly); I translated their values so no Spanish stays in `texts.json`, but they are dead keys → P37. The nav label `Featured action` (header/footer, P18) is kept: it describes the slot, not the sample offer name. `differentiators` is still Spanish (P29). `sobre-nosotros/`, `contacto/` and the legal pages still carry Spanish copy next to the new URL (P24–P28).
Notes / questions for the user: none
Commit: n/a (the user commits)

### P22 — Pricing `/pricing/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/precios/` → `src/pages/pricing/`. Every `/precios/` URL replaced by `/pricing/` in `header.html`, `footer.html`, `src/pages/index.html`, `services/index.html`, `accion-destacada/index.html`, `src/static/llms.txt` (URLs only: the Spanish text around them stays for P29), `src/data/site.json` (`sitemap_base_order`), the default `SITEMAP_BASE_ORDER` in `legible/build.py` and `tests/test_legible.py` (4 places: the domain-change route, the broken-link/short-description fixtures and the http-link test). `src/pages/pricing/index.html`: rewritten in English: title `Pricing | Your Business` (23), description 114 characters, `h1`, breadcrumb (visible and JSON-LD), table headers and row types (`Free`, `One-time`, `One-time / Monthly`, `Monthly`), prices with `$` and `/mo`, `priceCurrency` `EUR` → `USD` (7 places), advanced plans (`Growth Plan`, `Partner Plan`, "on request", "3 places"), "What no price includes" list (Google Ads/Google positions/AI wording replaced by generic items), FAQ and JSON-LD FAQ (3 questions, identical; the domain/hosting question became "Are materials and travel included in `{{service_1_name}}`?"), lead strip, `updated` and `dateModified` `2026-10-25`. Anchor ids `planes-avanzados`, `precios-tabla-title`, `no-incluye-precios-title`, `faq-precios-title` → `advanced-plans`, `pricing-table-title`, `not-included-title`, `faq-pricing-title` (no CSS, test or link used them). `src/data/texts.json`: English values for `growth_plan_price` (`$299`), `growth_plan_description`, `partner_plan_price` (`$490`), `partner_plan_description` (no AI wording) and `featured_action_short_includes` ("A short review and clear recommendations.").
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/pricing/` exists and `dist/precios/` does not; one `h1`; 372 words in `<main>`; no unresolved `{{`; no accented character or `€`; 3 FAQ questions equal to the JSON-LD; every `priceCurrency` is `USD`; exactly one price-0 entry (`$0`, the featured action) in the table; `sitemap.xml` and `llms.txt` list `/pricing/`. V3 for `/precios/` and `pages/precios` → no hits outside the plan/log (the remaining word `precios` is Spanish prose: `texts.json` `differentiators`, `accion-destacada` link text, `llms.txt` line 34 description). Spanish/agency sweep (V4/V5 patterns) on the page source → none.
Extra fixes (rule 9): `growth_plan_price` and `partner_plan_price` held `299 €/mes` and `490 €/mes` while the page appends `/mes`, so the output would have read `/mes/mes` (same defect as `extra_hourly_rate` in P21); now `$299` and `$490` and the page appends `/mo`. Value-only change. `featured_action_short_includes` translated here because only this page uses it and it showed Spanish inside the English table (P23 will not need to touch it).
Found, not fixed (→ backlog): the pricing page still links to `/accion-destacada/` and its JSON-LD still points the featured action there (renamed in P23 with every link). The "Service 1–5" rows all point to the single sample page (documented in §3.4). `differentiators` in `texts.json` is Spanish and is used only by `llms.txt` line 16 (handled in P29).
Notes / questions for the user: none
Commit: n/a (the user commits)

### P21 — Sample service page `/services/sample-service/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/services/servicio-generico/` → `src/pages/services/sample-service/`. Every `servicio-generico` URL replaced by `sample-service` in `header.html`, `footer.html`, `src/pages/index.html`, `services/index.html`, `precios/index.html`, `entity.json` (10 offer/service URLs, now the `/services/sample-service/` the P17 card asked for), `site.json` (`sitemap_base_order`), `src/static/llms.txt`, the default `SITEMAP_BASE_ORDER` in `build.py` and `README.md` (copy-a-service-page instructions). `src/pages/services/sample-service/index.html`: copy, `aria-label`s, breadcrumb (visible and JSON-LD), FAQ and JSON-LD FAQ in English; `priceCurrency` `EUR` → `USD`; the prices show `$`; WhatsApp and email pre-filled texts in English (the email subject now uses `{{service_1_name_url}}`). `src/data/texts.json`: English, generic values for `service_1_*` (meta description, full/short description, headline, lead, price note, includes/not-includes, delivery, target, delivery format, leads, ideal for), `service_N_short_includes`, `service_N_faq_includes`, `service_N_not_includes`, `service_2…5_delivery`, `service_2…4_full_description`, `service_2…4_ideal_for`, `service_4_requirements` ("Your current setup must already be in place and active."), `service_special_note`, `include_1…6` and `not_include_1…6` (generic items, no agency content). `extra_hourly_rate` is now `$55` (it was `55 €/h` and both the page and `llms.txt` append `/h`, so the output read `55 €/h/h`).
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built page: `dist/services/sample-service/` exists and `dist/services/servicio-generico/` does not; no unresolved `{{`; title `Service 1 | Your Business`, description 132 characters, one `h1`, 338 words in `<main>`, 4 FAQ questions equal to the JSON-LD; `sitemap.xml` lists `/services/sample-service/`. V3 for `servicio-generico` → no hits outside the plan/log. Spanish/agency sweep on the page source → none.
Extra fixes (rule 9): `extra_hourly_rate` `/h/h` duplication (value-only change, see above).
Found, not fixed (→ backlog): the pricing page still has Spanish copy and old keys (P22). `llms.txt` keeps Spanish text around the now-English values (P29). `service_N_name` links all point to the single sample page (documented in §3.4): the "Service 1–4" menu links stay.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P20 — Services index `/services/`  (2026-10-25)
Result: Done
Changed: folder `src/pages/servicios/` → `src/pages/services/` (the sample service page moves with it and is still `services/servicio-generico/` until P21). Every `/servicios/` URL replaced by `/services/` in `header.html`, `footer.html`, `src/pages/index.html`, the sample service, pricing, featured-action and 404 pages, `src/static/llms.txt`, `src/data/site.json` (`sitemap_base_order`), `src/data/entity.json` (offer and service URLs), the default `SITEMAP_BASE_ORDER` in `legible/build.py`, `tests/test_legible.py` (`_SERVICES` folder, `SERVICE`, folder paths, the "does not exist" service URL, the services page used by the broken-link test) and `README.md` (copy-a-service-page instructions). `src/pages/services/index.html`: all copy, `aria-label`s, breadcrumb (visible and JSON-LD), FAQ and JSON-LD FAQ in English; the FAQ answer that mentioned a "ficha de Google" is now "If you are starting from scratch, begin with `{{service_1_name}}`. If you already have the basics but something is missing, `{{service_2_name}}` covers it…"; anchor `#pack-arranque` → `#starter-bundle` (also in the home and in this page's links) and ids `servicios-grid-title`/`otros-title`/`faq-servicios-title`/`pack-title` → English; prices with `$` and `/mo`; WhatsApp and email pre-filled texts in English. `src/data/texts.json`: `services_page_lead` in English. Title `Services | Your Business`, description 117 characters.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built output: `dist/services/` exists, `dist/servicios/` does not; `sitemap.xml` lists `/services/` and `/services/servicio-generico/`; home links point to `/services/…`; services page has one `h1`, 537 words in `<main>`. V3 for `/servicios/`, `pages/servicios`, `pack-arranque` → no hits outside the plan/log. Sweep on the page for Spanish accents/words and Google/GEO wording → none.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the sample service page and the pages not yet rewritten (pricing, featured action, about, contact, legal, 404, `llms.txt`) still contain Spanish copy next to the new `/services/` links; they follow in P21–P29. The sample service URL is still `/services/servicio-generico/` (P21 renames it and updates `entity.json`, header, footer, `sitemap_base_order`, `llms.txt`, README).
Notes / questions for the user: none
Commit: n/a (the user commits)

### P19 — Home page `/`  (2026-10-25)
Result: Done
Changed: `src/pages/index.html`: all copy, `aria-label`s, FAQ questions and JSON-LD FAQ in English; the GEO/AI section (`geo-title`, `{{geo_topic}}`, `{{geo_description_lead}}`) is replaced by a neutral "Why choose `{{site_name}}`" section (`{{why_choose_us}}`); anchor id `no-hacemos-title` → `not-do-title`; the two FAQ entries about GEO and reviews are gone and "Do I own what you deliver?" / "How long does it take?" are now in both the visible FAQ and the JSON-LD (9 questions, same order and wording); prices on the cards and in the situation table show `$` (`${{service_N_price}}`, `/mo` for monthly); the WhatsApp and email pre-filled texts are English (the email subject now uses `{{featured_action_name_url}}`). `src/data/texts.json`: English values for every key the home uses (`home_headline`, `home_lead`, `home_description` — agency wording removed, 124 chars —, `services_intro`, `featured_action_*`, `bundle_*`, `coverage_area`, `lead_strip_*`, `service_N_short_description`, `situation_N`, `step_N_description`, `zone_description`, `what_we_dont_do`, `faq_1/3/4/5/8/9/12/15_answer`, `site_description`); new key `why_choose_us`; removed `geo_description_lead` (home-only). `src/data/entity.json` (extra fix, see below).
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built home: title `Your Business - Service 1 and Service 2 in Your City` (51), one `h1`, 937 words in `<main>`, 9 FAQ `summary` texts equal to the JSON-LD questions. Agency/Spanish sweep (V4/V5 patterns) on `src/pages/index.html`: no accented character, no SEO/Google/GEO/AI/agency wording; the only hits are the engine flag `geo: true` (allowed, §9.4) and the old URL slugs `/servicios/`, `/precios/`, `servicio-generico` (renamed in P20–P22, V3 then).
Extra fixes (rule 9): `src/data/entity.json` had only 4 offers (Service 1, 2, 3, Featured Action), so `{{service_4_*}}` resolved to the featured action and the home showed "monthly care" for `$0/mo` (the pricing page the same). Added the two missing sample offers, `Service 4 (Monthly)` 299 and `Service 5` 290, before the featured one (still exactly one price-0 offer). Larger than 5 lines, but it is sample data, not code, and without it the rewritten home would show a wrong price. Tests unchanged and green; the pricing page now shows `299/mes` instead of `0/mes`.
Found, not fixed (→ backlog): `geo_topic`, `geo_description`, `faq_10_answer`, `faq_11_answer` stay in `texts.json` because `src/static/llms.txt` still uses `{{geo_topic}}`, `{{geo_description}}` and `{{faq_10_answer}}` (removed with the rest of the agency copy in P29; `faq_11_answer` is then unused → P37). `featured_action_name` price `0` offers still render as bare numbers on pages not yet rewritten (`99`, `149`), fixed page by page in P20–P22. The home links still use the old Spanish paths (`/servicios/`, `/servicios/#pack-arranque`, `/precios/`, `/sobre-nosotros/`, `/accion-destacada/`); the anchor `#pack-arranque` is renamed in P20.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P18 — `layout.html`, header, footer  (2026-10-25)
Result: Done
Changed: `src/layout.html`: skip link `Skip to content`, WhatsApp `aria-label` `Open WhatsApp chat`, comment `Floating WhatsApp button`; `<meta charset>` indentation and the blank line before the stylesheet tidied. `src/partials/header.html`: `aria-label`s (`{{site_name}}, home`, `Open menu`, `Main navigation`) and labels `Services`, `Service 1–4`, `Pricing`, `About us`, `Featured action`. `src/partials/footer.html`: the agency sentence is now `{{footer_about}}`; headings `Services`, `Company`, `Legal`; links `All services`, `Service 1–4`, `Pricing`, `About us`, `Featured action`, `Contact`, `Legal notice`, `Privacy policy`, `Cookie policy`; WhatsApp label `Contact us on WhatsApp`; copyright `© {{year}} {{site_name}}. All rights reserved.` `src/data/texts.json`: new key `footer_about` ("`{{site_name}}` is a `{{service_category_1}}` and `{{service_category_2}}` business based in `{{location}}`. We help `{{target_audience}}` get clear, dependable service with written scopes and fair prices."), no mention of Google, SEO or AI. The four "Service 1–4" links and all URLs (`/servicios/…`, `/precios/`, `/sobre-nosotros/`, `/accion-destacada/`, `/contacto/`, legal pages) are unchanged: those folders are renamed in P20–P28, each updating header and footer.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built home read: footer sentence renders "Your Business is a Service 1 and Service 2 business based in Your City, Your Region. We help businesses in City 1, City 2, City 3 …"; `nav aria-label="Main navigation"`, skip link in English; no Spanish accented character or Spanish label left in the built header or footer. No test, README or doc cited the old labels.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the labels are English only, also with `language: es` (the locale files carry only `nav_guides`/`nav_blog`); moving them to `locales/` would be a new feature, out of scope. `{{footer_blog}}` and `{{nav_guides}}` are generated by the engine (locale-aware), unchanged.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P17 — `site.json`, `entity.json` and engine sample defaults  (2026-10-25)
Result: Done
Changed: `src/data/site.json`: `site_url` `https://YOUR-DOMAIN.com`, `site_name` `Your Business`, `language` `en` (flipped from `es`, as announced in P12), `contact_email` `hello@example.com`, `phone_e164` `+15550100`, English `whatsapp_message`, `build_banner` `Legible • Static site generator`, `check_banner` `Legible • Site validator`, `city` `Your City`, `region` `Your Region`, `collection_topics` `Topic 1…5`. `generated_content` reduced to what is needed: `lead_strip.action_url` (`/accion-destacada/`, still the existing URL until P23), English `guides_index.extra_paragraphs` and `blog_index.criteria_paragraphs` (they keep both indexes above the 250-word limit; every other field now comes from the English locale defaults). `src/data/entity.json`: `City 1…4`, `addressCountry` `US`, `priceCurrency` `USD` (offers and price specifications), catalog name `{{site_name}} services`, offers `Service 1`, `Service 2`, `Service 3 (Monthly)`, `Featured Action` (serviceType `Initial consultation`); `availableLanguage` already used `{{lang}}` and `inLanguage` `{{in_language}}` (P12). `legible/build.py`: sample defaults `Servicio N`→`Service N`, `Ciudad N`→`City N`, `Acción Destacada`→`Featured Action`, `negocios de`→`businesses in`, `99 €`/`149 €`/`49 €/mes`/`299 €/mes`/`290 €`→`$99`/`$149`/`$49/mo`/`$299/mo`/`$290`, default `COLLECTION_TOPICS` `Topic 1…5`. `tests/test_legible.py`: `IS_TEMPLATE` and the three `TU-DOMINIO` assertions/fixtures now use `YOUR-DOMAIN` (no test removed or weakened). `README.md`: sample domain, pre-launch sweep command (now the English one from DOCUMENTATION §9.4) and the sample-values sentences.
Checks run: V1 before → 115 tests OK, strict build `CHECK PASSED`, 11 pages; after → 115 tests OK, strict build `CHECK PASSED`, 11 pages, `No issues`, `No warnings`. Built home: `<html lang="en">`, `og:locale en_US`, JSON-LD `USD`/`US`/`+15550100`. V3 for `TU-DOMINIO`, `Tu Negocio`, `Tu Ciudad`, `Tu Provincia`, `contacto@example`, `34600000000` → no hits outside the plan/log (the only `Tema N` left are three unused `guide_topic_*` keys in `texts.json`, T-01 → P37). `grep` for Spanish sample defaults in `build.py` (`Servicio|Ciudad|Tema|Acción|negocios de| €`) → none.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): (1) `sitemap_base_order` and the offer URLs in `entity.json` keep the existing Spanish paths (`/servicios/servicio-generico/`, `/accion-destacada/`), because the folders still exist under those names; pointing the offers to `/services/sample-service/` now would build and pass the validator but leave dead URLs in the JSON-LD. They change in P20/P21/P22/P23 together with each folder (the P21 card already lists `entity.json`). I tried `/services/sample-service/` on a copy: it passes, so the switch is safe once the folders exist. (2) The page copy is still Spanish while `language` is `en`, so the generated parts (menu, breadcrumbs, indexes) are English and the pages Spanish until P18–P29. (3) If an `entity.json` list is emptied or a name is left as a `{{…}}` marker, the build stops with `marker {{featured_action_name}}`/`{{city_1}}` has no value`; the engine "unwrap" defaults only apply to placeholders inside the lists. This is existing behaviour, not caused by this phase, and not touched.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P16 — Language regression tests  (2026-10-25)
Result: Done
Changed: `tests/test_legible.py`: new `TestLanguageRegression(TempProject)` (placed after `TestCollectionsInTheBuild`, before the "5. domain and markers" section), 4 tests: `test_default_build_is_english` (removes `language` from a temp project's `site.json`, builds, strict-checks, asserts `<html lang="en"` and `content="en_US"` on the home page); `test_language_es_builds_and_validates_with_spanish_months_and_breadcrumb` (`language: es`, 3 blog articles with a known `published` date, builds, strict-checks, asserts `<html lang="es"`/`content="es_ES"` and, on `blog/index.html`, the Spanish month name `5 de marzo de 2026`, breadcrumb `aria-label="Migas de pan"` and the `Inicio` home link); `test_unknown_language_fails_with_a_clear_message` (`language: fr` → non-zero exit, `unsupported language 'fr'`, `supported: en, es`, no traceback); `test_collection_paths_localisation_works_together_with_language` (`language: en` + `collection_paths: {"guides": "how-to", "blog": "blog"}`, a guide piece under `src/pages/how-to/`, builds, strict-checks, asserts the home page links `<a href="/how-to/">Guides</a>` and the `how-to/index.html` breadcrumb says `Home`). Uses the existing `TempProject`/`build_ok`/`check_ok` helpers and `add_piece`/`piece_html`; no production code changed. `README.md`: test count 111→115 and the suite-coverage sentence now mentions language regression.
Checks run: V1 before → 111 OK; after → 115 tests OK (new tests ran individually first, then the full discovery run), strict build `CHECK PASSED`, 11 pages, no issues/warnings. Each new test does its own build + strict `check_site` run, so the strict validator ran against all four scenarios (default/no `language` key, `es`, invalid `fr`, and custom `collection_paths` with `en`), not just the sample project.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none
Notes / questions for the user: none
Commit: n/a (the user commits)

### P15 — Configurable collection URL paths  (2026-10-25)
Result: Done
Changed: `legible/build.py`: `load_collection_paths()` reads `site.json › collection_paths` (default `{"guides": "guides", "blog": "blog"}`), validates it (object with only those two keys; lowercase ASCII hyphenated slugs; the two must differ; otherwise `✗ BUILD FAILED: collection_paths …`) and defines `COLLECTION_PATHS`, `GUIDES_URL`, `BLOG_URL`. They are used for the content folders read by `load_collections` (folder, `rel` URL and the messages that name the folder), the "type outside its folder" check, the generated index URLs, JSON-LD of the indexes, the menu/footer links, the home resources section, the sitemap order, `llms.txt` (section links and the sitemap-extra filter) and the guides link inside the blog lead (locale strings now carry `{guides_url}`). Internal keys (`'guides'`, `'blog'`) and `type` values (`guide`/`article`, D-5) are unchanged. `legible/locales/en.json` and `es.json`: `blog_lead_guides_link` uses `{guides_url}`. `tests/test_legible.py`: 2 new tests in `TestCollectionsInTheBuild` (custom paths build, pass the strict validator and move folders/URLs/sitemap/menu; invalid values stop the build). `README.md` (Guides and blog section, `site.json` list, test count 111) and `DOCUMENTATION.md` §3.1 updated.
Checks run: V1 before → 109 OK; after → 111 tests OK, strict build `CHECK PASSED`, no issues/warnings. Default paths: `diff -r` of a project with 1 guide + 3 articles built from the P14 tree vs this tree → no differences. Temp project with `{"guides": "guias", "blog": "articulos"}`, pieces in `src/pages/guias/` and `src/pages/articulos/`: `dist/guias/` and `dist/articulos/` generated, no `dist/guides/`, sitemap, `llms.txt` and home links use the new paths, strict validator `No issues`. Invalid values (`"Guías"`, same slug twice, unknown key, non-object) → clear error, exit 1, no traceback. V3: no hard-coded `/guides/` or `/blog/` left in `build.py` (one docstring reworded).
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `related` and `service` front-matter values are literal URLs, so a site that changes the collection paths must write them with the new paths (documented by the validator error "is not an existing guide or article"). Page copy and the sample `src/` files still use the default `/guides/` wording; the Spanish rename of the sample is Track D.
Notes / questions for the user: the plan said the test count only changes in P16, P32, P33; I added 2 regression tests here (109 → 111) and README/STATUS say 111.
Commit: n/a (the user commits)

### P14 — Generated page copy into locale files  (2026-10-25)
Result: Done
Changed: `legible/locales/en.json` and `es.json`: 30 new keys (`lead_strip_*`, `home_resources_*`, `guides_index_*`, `blog_index_*`, `blog_lead_guides_link/text`, `llms_guides_description`, `llms_blog_description`). The Spanish values are the strings that were hard-coded in `build.py`; the English ones are new, generic copy (no agency or product references). `legible/build.py`: `_lead_strip_html` (including the "or write to us at {email} or on {whatsapp}" line, now `lead_strip_contact`), `render_home_resources`, `render_guides_index`, `render_blog_index` (eyebrows reuse `nav_guides`/`nav_blog`, the guides link in the blog lead is `blog_lead_guides_link/text`), `render_llms_guides`, `render_llms_blog` read their defaults with `t()`; `site.json › generated_content` still overrides each field. Default lead-strip `action_url` is now `/featured-action/` (was `/accion-destacada/`; the sample `site.json` sets its own, so nothing changes there). In `render_home_resources` the comprehension variable `t` was renamed so it no longer shadows the `t()` helper. Anchor ids `blog-criterio`→`blog-criteria` and `blog-lista`→`blog-list` (Spanish leftovers, same pattern as P08; no CSS, test or doc used them). `README.md` and `DOCUMENTATION.md` mention where the defaults live. No test asserted this copy, so no test changed.
Checks run: V1 before → 109 OK; after → 109 tests OK, strict build `CHECK PASSED`, no issues/warnings. Temp project with 1 guide + 3 articles, `language: es`: `diff -r` against the P13 tree → only `blog/index.html` differs, by the two renamed ids. Same project with `generated_content` reduced to the `action_url` (so every default is used): again only `blog/index.html` (ids). Same project in `en` with no overrides: builds; `guides/index.html` H1 "Guides to solve questions about your business", eyebrow/breadcrumb "Guides", `llms.txt` section `## Guides`/`## Blog` with English descriptions, lead strip and contact line in English, no unresolved marker.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): with no `generated_content` overrides and no `extra_paragraphs`/`criteria_paragraphs`, the strict validator warns `thin content` on `/guides/` (135 words) and `/blog/` (188 words) (< 250). This is identical for the former Spanish defaults (their output is byte-identical), so it is not a regression; the sample `site.json` supplies the extra paragraphs. To revisit in P17 (English sample `site.json` with English extras). The English blog title default was lengthened ("Articles and news for your business") to clear the `title too short` warning. `llms.txt` template text and other Spanish copy in `src/` remain for Track D; `'Acción Destacada'` fallback at `build.py:1052` is P17.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P13 — Locale files, loader, dates and shared labels  (2026-10-25)
Result: Done
Changed: new `legible/locales/en.json` and `legible/locales/es.json` (keys: `months`, `long_date`, `breadcrumb_home`, `breadcrumb_label`, `nav_guides`, `nav_blog`, `card_read_guide`, `card_read_article`; the Spanish values are the strings that were hard-coded in `build.py`). `legible/build.py`: `load_locale(language)` (missing file → `✗ BUILD FAILED: no locale file legible/locales/<l>.json (available: …)`), `LOCALE`, helper `t(key, locale=None)` (missing key → `✗ BUILD FAILED: key "<key>" is missing in legible/locales/<l>.json`); `MESES_ES` removed; `format_long_date(iso, locale=None)` uses `long_date` and `months`; breadcrumb (visible label, `aria-label`, JSON-LD `Inicio`), index breadcrumb labels, menu/footer links for Guides and Blog and the card link texts now come from `t(...)`. `tests/test_legible.py`: new `TestLocale.test_format_long_date_in_both_languages`. `README.md` (layout tree, test count 109) and `DOCUMENTATION.md` (locales note) updated.
Checks run: V1 before → 108 OK; after → 109 tests OK, strict build `CHECK PASSED`, no issues/warnings. `diff -r` of a temp project with 1 guide + 3 articles built from the P11 tree vs this tree (`language: es`): no differences. With `language: en`: `Read the guide`, `Read the article`, `aria-label="Breadcrumb"`, `Home`, menu `Blog`, date `January 10, 2026`. Deleted key and deleted file → the two errors above, exit 1. V3 `MESES_ES` → none outside plan/log. Unit test: `2026-03-05` → `March 5, 2026` / `5 de marzo de 2026`.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the plan says the test count only changes in P16/P32/P33; P13 asks for a unit test, so it is now 109 (reported here). Eyebrows `Guías`/`Blog` on the index pages, the home-resources card link texts (`Ver las guías`, `Ver los artículos`) and `llms.txt` labels are copy for P14.
Notes / questions for the user: none
Commit: n/a (the user commits)

### P12 — `language` setting and derived markers  (2026-10-25)
Result: Done
Changed: `legible/build.py`: `LANGUAGES = {'en': ('en','en_US','en-US'), 'es': ('es','es_ES','es-ES')}`, `LANGUAGE` read from `site.json` (default `en` when absent), constants `LANG`, `OG_LOCALE`, `IN_LANGUAGE`; unknown value → `✗ BUILD FAILED: unsupported language 'fr' in src/data/site.json; supported: en, es`. New derived markers `{{lang}}`, `{{og_locale}}`, `{{in_language}}`. `_index_jsonld` uses `IN_LANGUAGE`. `src/layout.html`: `<html lang="{{lang}}">`, `og:locale` `{{og_locale}}`. `src/data/entity.json` (`availableLanguage`, WebSite `inLanguage`), `src/static/llms.txt` (`availableLanguage`) and the 7 page JSON-LD blocks (`inLanguage`) use the markers. `tests/test_legible.py`: the `piece_html` fixture uses `{{in_language}}`. `README.md`: `language` documented in the `site.json` list. `site.json`: new key `"language": "es"`.
Checks run: V1 before and after → 108 tests OK, strict build `CHECK PASSED`, no issues/warnings. Build of the P11 tree vs this tree (`--minify false --no-validate`, `SITE_URL=https://example.com`): `diff -r` → identical output with `language: es`. Temp copy with `"en"`: `<html lang="en">`, `og:locale en_US`, JSON-LD `inLanguage en-US`, `availableLanguage en` (index.html and llms.txt); guides index and a guide page also `en-US`. `"fr"` → the error above, exit 1. Key absent → `<html lang="en">`.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): the plan says to add `"language": "en"`, but the sample content is still Spanish until Track D, so `site.json` is set to `"es"` for now to keep the output unchanged; it flips to `"en"` in P17 together with the sample data. The language tests are P16 (test count stays 108 here).
Notes / questions for the user: none
Commit: n/a (the user commits)

### P11 — Tests in English, part 2  (2026-10-25)
Result: Done
Changed: `tests/test_legible.py`, from `TestColeccionesDirectas` to the end. Classes `TestDirectCollections`, `TestCollectionsInTheBuild`, `TestDomain`, `TestMarkers`, `TestSafeOutput`, `TestSpecialCharactersAndWarnings`, `TestCommandLine`; all 57 test names, helper methods (`problems`, `rejected`, `_with_name`, `_break`), local variables, docstrings, comments, assertion messages and fixtures (slugs `one`/`two`/`three`, `bad-guide`, `Uppercase`, `Invented`, test domains `example.org`, `one.example`, `two.example`, city `Seville`, English guide title/description) in English.
Checks run: V1 before and after → 108 tests OK (`-v | grep -c "ok$"` = 108), strict build `CHECK PASSED`, no issues/warnings. `py_compile` OK. `grep -nE "[áéíóúñ¿¡«»]" tests/test_legible.py` → only deliberate fixtures: `'ñ  é'` (JSON-LD round trip, line 379), slug `guía-útil` (accented slug must be rejected, lines 510/513), `Café "Ana" & Sons \ Ltd.` (accent + quotes + `&` + backslash in the site name, lines 860/875). The `€` price sign (lines 411, 421, 1xx) stays too.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): tests still depend on the current sample data and are updated in the phase that changes it: `/servicios/`, `sobre-nosotros`, `precios`, `/contacto/`, `TU-DOMINIO`, `Valdemoro` (geo test), `inLanguage: 'es-ES'` → Tracks C/D (P16, P17–P28).
Notes / questions for the user: none. Track B is complete.

### P10 — Tests in English, part 1  (2026-10-25)
Result: Done
Changed: `tests/test_legible.py`, from the top through `TestMinifyHtml` (up to the "4. guides and blog" separator). Constants `SOLO_SIN_COLECCIONES`→`ONLY_WITHOUT_COLLECTIONS`, `SOLO_PLANTILLA`→`ONLY_TEMPLATE`, `SIN_COLECCIONES`→`WITHOUT_COLLECTIONS`, `ES_PLANTILLA`→`IS_TEMPLATE`, `TEMA_1`→`TOPIC_1`, `SERVICIO(_SLUG)`→`SERVICE(_SLUG)`, `_SERVICIOS`→`_SERVICES`; helpers `pieza_html`→`piece_html`, `add_pieza`→`add_piece`; classes `ProyectoTemporal`→`TempProject`, `TestHumo`→`TestSmoke`. These identifiers are also used in part 2, so they were renamed file-wide (identifier-only change there). In part 1: module docstring, section separators, helper docstrings, comments, all test names (51 renamed, none added/removed/merged), local variables, assertion messages and fixture texts (filler `lorem`, piece title/description/summary, CSS/HTML minifier inputs) are English.
Checks run: V1 before and after → 108 tests OK (`-v | grep -c "ok$"` = 108 before and after), strict build `CHECK PASSED`, no issues/warnings. `py_compile` OK. V3 for `ProyectoTemporal`, `TestHumo`, `SOLO_PLANTILLA`, `SOLO_SIN`, `add_pieza`, `pieza_html` → no hits outside the plan/log. Part 1 has no Spanish left except two deliberate fixtures: `'ñ  é'` (non-ASCII JSON-LD round trip) and the `€` price sign.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): part-1 fixtures still tied to current sample data and left for Tracks C/D: `/servicios/` path (`SERVICE`), the `https://TU-DOMINIO` prefix in `IS_TEMPLATE`, `inLanguage: 'es-ES'` in `piece_html`. Part 2 (from `TestColeccionesDirectas`) is still Spanish → P11.
Notes / questions for the user: none
Commit: `P10: Tests in English, part 1`

### P09 — Data and marker names  (2026-10-25)
Result: Done
Changed: `src/data/textos.json` → `src/data/texts.json` (`git mv`, history kept). `legible/build.py`: loader path and variables (`textos`→`texts`, `textos_path`→`texts_path`), the two error messages and the comments/docstring that name the file. `tests/test_legible.py`: file path, variable names and test names that mention `textos` (full test renaming is P10/P11). `README.md`: all 8 mentions (overview, layout tree, data files section, Mermaid diagram, build steps, directory table, launch checklist). `src/data/texts.json`: unused leftover key `guias_intro` → `guides_intro` (the only Spanish-named key). The `site.json` key `text` stays, as the card says.
Marker audit (`grep -rhoE "\{\{[a-z0-9_]+\}\}" src legible | sort -u` plus the 161 keys of `texts.json` and all keys of `site.json`/`entity.json`): no Spanish-named marker or key remains after P08 and this phase; nothing else needed renaming.
Checks run: V1 before and after → 108 tests OK, strict build `No issues`. `py_compile` OK. Hand checks on a copy: invalid `texts.json` → "✗ BUILD FAILED: could not read src/data/texts.json: Expecting property name…"; a `texts.json` missing keys → "✗ BUILD FAILED: marker {{site_description}} (on page /accion-destacada/) has no value. Add "site_description" to src/data/texts.json or write it directly in the page." V3 `textos`: no hits in `legible/`, `tests/`, `README.md` or data; only 2 Spanish copy words remain (`llms.txt` line 90, `aviso-legal/index.html` line 46: "textos" meaning "texts" in prose), left for Track D (P26, P29).
Extra fixes (rule 9): none
Found, not fixed (→ backlog): 34 unused keys in `texts.json` (T-01, includes `guide_*`, `guides_intro`) → P17. `DOCUMENTATION.md` still says `textos.json` only inside the plan, dictionary and phase cards (intended).
Notes / questions for the user: existing projects must rename their `src/data/textos.json` to `texts.json` (breaking change by design, D-1).
Commit: `P09: Data and marker names`

### P08 — Collection naming  (2026-10-25)
Result: Done
Changed: `legible/build.py`: `COLLECTION_DIRS = {'guides': 'guide', 'blog': 'article'}`, dict keys and folder names (`guias`→`guides`), `type` values (`guia`→`guide`, `articulo`→`article`), variables (`guias`, `articulos`, `guias_exist`, `guias_txt`), functions (`render_guias_index`→`render_guides_index`, `render_llms_guias`→`render_llms_guides`, `render_home_recursos`→`render_home_resources`), markers (`{{nav_guias}}`→`{{nav_guides}}`, `{{llms_guias}}`→`{{llms_guides}}`, `{{home_recursos}}`→`{{home_resources}}`) and hard-coded `/guias/` paths→`/guides/` (still hard-coded until P15); generated anchor ids `home-recursos`→`home-resources`, `guias-tema-N`→`guides-topic-N`, `guias-como`→`guides-how`. Same markers in `src/partials/header.html`, `src/partials/footer.html`, `src/pages/index.html`, `src/static/llms.txt`; the `{guias_txt}` placeholder in the `site.json` collection lead is now `{guides_txt}`. `tests/test_legible.py`: temp projects use `guides/`, `type: guide`/`article`, `/guides/` URLs and the slugs `my-guide`, `my-first-guide`, `my-article` (test names are left for P10/P11). `README.md`: collection table, `/guides/` index, `{{home_resources}}` and the "do not create index.html in `guides/`" note.
Checks run: V1 before and after → 108 tests OK, strict build `No issues`. Temp project with 1 guide + 3 articles: build and strict validation passed (17 pages); `dist/guides/` and `dist/blog/` generated, `/guides/` in sitemap.xml and llms.txt, `href="/guides/"` in the home, `home-resources` section present. V3: `guias`, `guia\b`, `articulo`, `recursos` → no hits in `legible/`, `tests/`, `src/` except the two below.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `src/data/textos.json:145` has the unused key `guias_intro` (leftover sample-guide data, finding T-01) → P09/P17. Visible Spanish copy that mentions guides/resources (`Recursos para tu negocio`, `Guías`, `Ver las guías`, `mira las guías`) is page copy, left for P14 as the card says. `DOCUMENTATION.md` still lists the old names only in the plan, dictionary and P08 card (intended).
Notes / questions for the user: existing sites with a `src/pages/guias/` folder or `type: guia` must rename them (breaking change by design, D-5).
Commit: `P08: Collection naming`

### P07 — Python identifiers: `build.py` (internal names only)  (2026-10-25)
Result: Done
Changed: `legible/build.py`: `fecha_larga`→`format_long_date`, `protegidas`→`protected`, `en_riesgo`→`at_risk`, `tarjetas`→`cards`, `USO`→`USAGE`, `reemplazos`→`replacements` (19 occurrences, whole-word renames, no scope collisions). `legible/run_all.py`: `paso`→`step`, `titulo`→`title` (the plan lists `paso`→`step`; it was the only Spanish identifier left outside `build.py`). The plan's `piezas`→`pieces` needed no change (the code already uses `pieces`). Collection names (P08), marker/data names (P09) and `MESES_ES` (P13, becomes locale month names) deliberately left.
Checks run: `python3 -m py_compile` on both files OK; V3 for each old name (`fecha_larga`, `protegidas`, `en_riesgo`, `tarjetas`, `USO`, `reemplazos`, `titulo`) → zero hits in `legible/`, `tests/`, `README.md` (the only mentions left are the plan text in `DOCUMENTATION.md` and this log). V1 → 108 tests OK, strict build `No issues`; `build.py --foo` prints the usage with `USAGE`; `run_all.py --skip-tests --no-dev` OK.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `pyflakes` (V7) could not be installed in this environment (no PyPI access), so no static unused/undefined-name check was run; to be done in P31/P36 where pyflakes is available. Remaining Spanish identifiers in `build.py` all belong to P08/P09: `guias`, `articulos`, `guias_exist`, `guias_txt`, `nav_guias`, `render_guias_index`, `render_home_recursos`, `render_llms_guias`, `textos`, `textos_path`.
Notes / questions for the user: none
Commit: `P07: Python identifiers: build.py`

### P06 — Console messages: `dev.py`, `run_all.py`, `build.sh`  (2026-10-25)
Result: Done
Changed: `legible/build.sh`: 6 messages (`python3 is not available`, `Building and minifying`, `CSS_MINIFY=FALSE: building without minifying`, `Running check_site.py (strict)...` / `(errors only)...`, `Build finished in dist/`). `legible/run_all.py`: step titles (`1/3 Tests`, `2/3 Build + validation (build.sh)`, `3/3 Local server (Ctrl+C to quit)`), the stop message, the missing-bash message, the `--no-dev` message and argparse description/help. `legible/dev.py`: nothing to change (its messages were already English). The Python identifier `paso` in `run_all.py` is left for P07.
Checks run: V1 → 108 tests OK, strict build `No issues`. `python3 legible/run_all.py --no-dev` → all three step titles and messages in English, exit 0. `python3 legible/dev.py --port 3917` → printed `Serving .dev-dist on http://localhost:3917` and `Build OK`, `GET /` → 200, `GET /nope/` → 404, SIGINT printed `Stopping dev server` and the port closed. Failing step (`SITE_URL=http://bad.example`) → `✗ "2/3 Build + validation (build.sh)" failed (exit code 1). Stopping here.`, exit 1. `bash -n legible/build.sh` OK. No test or document cited the old messages.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none new. Default port in the plan text says 3001 and `dev.py` default is 3001 (consistent).
Notes / questions for the user: none
Commit: `P06: Console messages: dev.py, run_all.py, build.sh`

### P05 — Console messages: `check_site.py`  (2026-10-25)
Result: Done
Changed: `legible/check_site.py`: every `E(...)`, `W(...)`, `errors.append`, `warnings.append`, the report banner default (`Site validator`) and the argparse description/help translated to English, keeping each message's meaning. The leftover regex is now `\bTODO\b|\[CONFIRM` with message `contains TODO or [CONFIRM`. `tests/test_legible.py`: 3 assertion fragments updated (`broken internal link`, `http instead of https`, `description too short`). `README.md`: the two mentions of `[CONFIRMAR` now say `[CONFIRM` (rule 8).
Checks run: V1 before and after → 108 tests OK, strict build `No issues`. Validator on a deliberately broken copy of `dist/` (one `alt` removed) → report reads `<img> without alt: /images/logo.svg` and the rest of the report in English; `--help` shows the English description and help. AST scan: no Spanish-looking string literal left in `check_site.py`.
Extra fixes (rule 9): `build.py` line 830 (missed in P04): default report banner `' • Generador de webs estáticas'` → `' • Static site generator'`. One line, no behaviour change (site.json overrides it).
Found, not fixed (→ backlog): `src/data/site.json` still sets `build_banner` ("Legible • Generador de webs estáticas") and `check_banner` ("Legible • Validador del sitio"), so the reports still show them in Spanish; they are data, handled in P17.
Notes / questions for the user: none
Commit: `P05: Console messages: check_site.py`

### P04 — Console messages: `build.py`  (2026-10-25)
Result: Done
Changed: `legible/build.py`: all user-facing console/error messages translated to short English: `BUILD FAILED` family (site.json/textos.json read and type errors), `SITE_URL must start with https://`, unresolved-marker error, `BUILD ABORTED` (unsafe output folder), `invalid Guides/Blog front matter` and the 19 collection problem messages, missing `updated`/`dateModified`, unresolved marker in llms.txt, CLI usage and argument errors. Date format hints are now `YYYY-MM-DD`. `tests/test_legible.py`: 17 `assertIn` fragments updated to the new wording (rule 5: wording only, no assertion weakened). HTML/JSON-LD strings that end up in pages are untouched (P14).
Checks run: V1 before and after → 108 tests OK, strict build `No issues`. Triggered by hand: bad `SITE_URL=http://example.com` → "✗ SITE_URL must start with https:// (current value: 'http://example.com'); check src/data/site.json"; unresolved `{{marcador_inexistente}}` → "✗ BUILD FAILED: marker {{marcador_inexistente}} (on page /) has no value. Add "marcador_inexistente" to src/data/textos.json or write it directly in the page."; also bad `--minify`, unknown argument and a broken guide (8 collection problems) all read correctly in English. No old message fragment remains in README/DOCUMENTATION.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): messages still name current Spanish identifiers (`guias/`, `textos.json`); they follow the renames in P08/P09.
Notes / questions for the user: none
Commit: `P04: Console messages: build.py`

### P03 — Comments/docstrings: other scripts  (2026-10-25)
Result: Done
Changed: `legible/check_site.py` (module docstring + 7 docstrings + 30 comments), `legible/dev.py` (2 docstrings, 2 comments, new one-line module docstring), `legible/run_all.py` (module docstring), `legible/build.sh` (2 comments). Translated to short English; string literals, console messages and logic untouched.
Checks run: V2 (AST comparison) on `check_site.py`, `dev.py`, `run_all.py` → `IDENTICAL CODE` for all three (the new `dev.py` module docstring is ignored in the comparison, since it is added on purpose); `bash -n legible/build.sh` → OK and its non-comment lines are identical to before; no Spanish left in comments/docstrings of the four files. V1 → 108 tests OK, strict build `No issues`.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none new. Spanish console strings in these files (e.g. `python3 no está disponible`, `Compongo y minimizo`, argparse help) remain for P05/P06.
Notes / questions for the user: none
Commit: `P03: Comments/docstrings: other scripts`

### P02 — Comments/docstrings: `build.py`  (2026-10-25)
Result: Done
Changed: `legible/build.py` only: every Spanish comment and docstring translated to short English (82 lines changed). The stale "Orden histórico del sitemap (F3)" is now "Base sitemap order; new pages follow: /guides/ + guides, /blog/ + articles." String literals, identifiers and logic untouched.
Checks run: V2 (AST comparison, docstring text ignored) → `IDENTICAL CODE`; a tokenizer/AST scan finds no Spanish left in comments or docstrings. V1 → 108 tests OK, strict build `No issues`.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): comments/docstrings still cite current real names (`guias`, `textos.json`, `{{home_recursos}}`, `/guias/`) because the code still uses them; they will be updated in P08/P09 together with the renames.
Notes / questions for the user: none
Commit: `P02: Comments/docstrings: build.py`

### P01 — Single English README  (2026-10-25)
Result: Done
Changed: deleted `README.es.md`; `README.md`: removed the `[English] · [Español]` line, replaced `README.es.md` by `DOCUMENTATION.md` in the layout tree, added one line after the overview linking to `DOCUMENTATION.md`.
Checks run: V1 before → 108 tests OK, strict build `No issues`; V1 after → 108 tests OK, strict build `No issues`, 11 pages. `grep -rn "README.es" . --exclude-dir=dist --exclude-dir=.git` → only historical mentions inside `DOCUMENTATION.md` (plan/F-01/P01 card) and this log; no live references. README anchors: 0 broken.
Extra fixes (rule 9): none
Found, not fixed (→ backlog): `README.md` still says the template is Spanish (Overview note) and names `textos.json`; both are handled in P09/P38.
Notes / questions for the user: the zip did not include `.git`; Git was re-initialised with `P00: baseline` before this phase.
Commit: `P01: Single English README`

### P00 — Baseline and backup  (2026-10-25)
Result: Done
Changed: no project file changed. Added `DOCUMENTATION.md` (the plan) and this `STATUS.md` at the repository root; initialised Git with a baseline commit so every later phase can be diffed and rolled back.
Checks run: V1 → 108 tests OK; strict build and validation pass (11 pages, no errors, no warnings). `dist/` and `__pycache__/` removed afterwards (no build output ships in the archive).
Extra fixes (rule 9): none
Found, not fixed (→ backlog): none new (the audit findings T-01…T-11 are in `DOCUMENTATION.md` §5.2 and mapped to phases)
Notes / questions for the user: none blocking. Next is P01 (delete `README.es.md`, remove the language selector, link to `DOCUMENTATION.md`).
Commit: see `git log` (`P00: baseline`)

---

## 5. Backlog (found, deliberately not fixed)

Anything noticed during a phase that is not tiny or not clearly a bug goes here with a reason. Items already planned are in `DOCUMENTATION.md` §5.2.

| ID | Found in | Description | Reason not fixed | Proposed phase |
|---|---|---|---|---|
| T-05 | audit | 8 lines over 200 characters in `build.py` (generated HTML f-strings) | Cosmetic; changing them risks output differences | — |
| T-08 | audit | Footer year uses the current year, so output is not byte-reproducible across years | Acceptable; documented only | — |
| F-15 | review | `compose_page` has 17 parameters; `build()` is ~260 lines | Known debt; refactoring is out of scope | — |
| T-12 | P36/P39 audit | `pyflakes` unavailable because the module is absent; the release check was attempted again and could not run | No dependency added; retry where the package is available | Open |

---

## 6. Open questions for the user

| # | Question | Needed before | Answer |
|---|---|---|---|
| — | None at the moment | — | — |

---

## 7. Extra fixes log (rule 9)

| Phase | File | What and why |
|---|---|---|
| P05 | `legible/build.py` | Default build banner translated (missed in P04); 1 line |
| P19 | `src/data/entity.json` | Two missing sample offers (Service 4, Service 5) added so `{{service_4_*}}` is not the featured action |
| P21 | `src/data/texts.json` | `extra_hourly_rate` `55 €/h` → `$55` (page and `llms.txt` append `/h`, output read `/h/h`) |
| P22 | `src/data/texts.json` | `growth_plan_price` / `partner_plan_price` `… €/mes` → `$299` / `$490` (page appends `/mo`, output would read `/mes/mes`); `featured_action_short_includes` translated (only this page uses it) |
