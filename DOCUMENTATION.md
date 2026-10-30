# legible — Reference documentation

> **Who this document is for**
> - **A person** who wants to understand what legible does, how it is built and which rules protect it.
> - **An AI that builds a site** from this base: it interviews the user, writes a phased `SITE_PLAN.md` and executes it one phase per session (sections 5 and 6, and [`AGENTS.md`](AGENTS.md)). **This is the default and main use of the project.**
> - **An AI that modifies the engine** (`legible/`, `tests/`) only as an exception, and must keep the change small, tested and consistent (sections 0.1 and 2).
>
> **Language policy:** everything is in **English** — README, this document, `AGENTS.md`, code, comments, identifiers, console messages, tests, data-file names and the sample site. Spanish (or any other language) is supported **only as a per-site choice** (see section 4).

---

## 0. How to use this document

| You want to… | Read… |
|---|---|
| Understand what legible is | Section 1 |
| Understand how it works inside | Sections 2, 3 |
| Know the language and naming rules | Section 4 |
| Understand the methodology (commands, interview, plan, phases, completion) | Section 5.0 and `AGENTS.md` |
| Build a site with an AI | `AGENTS.md`, then sections 5, 6 |
| Look up markers, rules, commands and checks | Section 7 |

### 0.1 Ground rules when changing the project

These rules apply when the **engine** changes. Building a site is the default job and changes only `src/`; the engine changes only when there is no other way ([`AGENTS.md`](AGENTS.md) section 7).

1. Add no dependencies, no client-side JavaScript and no frameworks. If a change needs one, do not make the change.
2. Never weaken tests or validator thresholds to get a green result. If a test must change because a name or message changed, update it and say why.
3. Keep the baseline (section 7.3, V1) green after every change.
4. Keep changes small and reviewable. A change that turns out to be big is split.
5. Keep `README.md`, `DOCUMENTATION.md` and `AGENTS.md` in step with any rename or behaviour change.
6. Report with facts: run the commands and paste real results. Never claim something passed if it was not run.
7. Keep one source of truth. [`AGENTS.md`](AGENTS.md) holds the procedures, numbers, limits and commands that an AI follows; this document holds the reasoning and the reference tables. Change a number or a step in `AGENTS.md` only, and do not copy it here: refer to the section instead. If the two ever differ, `AGENTS.md` wins and the other file is fixed.

---

## 1. What legible is

A static-site generator for **local service businesses**, written with the Python standard library only.

- **Input:** HTML templates + three data files (`site.json`, `entity.json`, `texts.json`).
- **Output:** a `dist/` folder with plain HTML, one CSS file, `sitemap.xml`, `robots.txt`, `llms.txt`, and one JSON-LD (Schema.org) `@graph` per page.
- **Quality gate:** a validator (`check_site.py`) checks the compiled output; in strict mode warnings also fail the build.
- **It does not promise** rankings, indexing or traffic — only predictable, inspectable output.

### 1.0 Built-in SEO checks

`legible` ships its own minimal SEO checks. They are part of the base, run on every build and need no configuration:

| Built in | What it does |
|---|---|
| Generated metadata and Schema.org JSON-LD | One `@graph` per page, plus title, description, canonical, Open Graph and Twitter tags |
| `sitemap.xml`, `robots.txt`, `llms.txt` | Generated from the site data; only indexable pages in the sitemap |
| Strict validator (`check_site.py`) | Checks the compiled output; warnings also fail the build (section 7.2) |
| Pre-launch sweep | A search for sample values and `[CONFIRM` markers left in a real project (section 7.4) |

Not included: analytics, Search Console, rank tracking, performance audits, accessibility audits and interactive features. These are not promised and are not in the base. An AI that builds a site uses the built-in checks, never asks the user whether to enable them, and records any request for something outside the base in the plan's **Later** list.

### 1.1 Design principles (non-negotiable)

| Principle | Practical consequence |
|---|---|
| Standard library only | Nothing to `pip install` in production |
| No client-side JavaScript | The only `<script>` elements are `application/ld+json` blocks |
| No third-party requests | No external fonts, CDNs or trackers; system fonts |
| One source of truth for business facts | Written once, propagated via `{{markers}}` |
| Fail fast and clearly | An unresolved `{{marker}}` stops the build, naming marker and page |
| The validator is a gate | `build.sh` exits non-zero if anything fails |
| Opinionated | Local service businesses (`ProfessionalService`), not a CMS |
| Safe output and a confined dev server | The build refuses an output folder that is, or contains, the project, `src/` or `legible/`; the dev server serves only `.dev-dist/` and blocks path traversal |
| Correct escaping | Derived values are HTML-escaped and JSON-LD values are JSON-escaped (section 2.5) |
| Careful minifiers | The CSS and HTML minifiers protect attributes, `pre`, `textarea`, `calc()` and `url()` |
| All problems at once | Collection validation reports every problem in one pass, not one at a time |
| A test suite that adapts | Tests that depend on the sample data are skipped when a project replaces it, so derived projects keep a green suite |

### 1.2 Known limits (not bugs)

- Shortcut markers cover up to 4 cities, 6 categories and 5 offers.
- The `ProfessionalService` node type is required: the build reads business facts from it and the validator demands it.
- Not a CMS and not a general-purpose static-site framework.
- `compose_page` takes many parameters and `build()` is a long function. They are left as they are on purpose: reshaping them requires tests that cover the behaviour first.

### 1.3 Design decisions

- **Everything is English**, including identifiers, data-file names, marker names and sample URLs: one architecture that every contributor and AI can read. Only site *content* changes language.
- **The default `language` is `en`; other languages ship as locale files** (`legible/locales/<code>.json`, engine-generated strings only) and the content of a site is translated per project.
- **Sample values are neutral and fictional:** currency USD, country `US`, phone `+15550100`, email `hello@example.com`.
- **The `featured_action_*` marker names and the `/featured-action/` URL stay.**
- **The `type` values `guide` and `article` stay English for every site language:** they are architecture, not content.
- **Legal pages are jurisdiction-neutral templates.** They use neutral placeholders (`Your legal name`, `Your jurisdiction`…) and tell the reader to have the text reviewed by a qualified lawyer; a real project turns missing facts into `[CONFIRM …]` markers.
- **Building a site comes first; the engine adapts only when it must.** The zip is a generic base. A site is made by changing `src/`, guided by an interview and a phased plan (section 5). An engine change is a small, recorded exception, never a first reaction.
- **The sample brand assets stay** (legible's own branding) as placeholders to be replaced (section 3.7).

---

## 2. Architecture

### 2.1 Overview

```mermaid
flowchart LR
    subgraph SRC["src/ — what you edit"]
        D["data/<br/>site.json · entity.json · texts.json"]
        P["pages/ · partials/ · layout.html"]
        S["css/ · static/"]
    end
    SRC --> B["legible/build.py"]
    L["legible/locales/<br/>en.json · es.json"] --> B
    B --> C["dist/"]
    C --> V{"legible/check_site.py --strict"}
    V -- "no errors, no warnings" --> E["Deploy dist/ to a static host"]
    V -- "otherwise" --> F["Non-zero exit + report"]
```

> `legible/locales/` holds the strings the engine generates in each language: months and date format, breadcrumb, menu and card labels, the default copy of the guides/blog indexes, the lead strip, the home resources section and the `llms.txt` labels. `site.json › generated_content` overrides the lead strip and the index copy, and `generated_content.locale_overrides` replaces any single locale text (see below).

> **The closing strip of `/guides/` and `/blog/`** (`lead_strip`) ends with a contact line that offers only the channels the site has: email and WhatsApp when both exist; only the email when there is no telephone (locale key `lead_strip_contact_email_only`, with no WhatsApp link and no empty `href`); only WhatsApp when there is no email (`lead_strip_contact_whatsapp_only`); no line, just the button, when there is neither. To write the line yourself, set `generated_content.lead_strip.contact_html` in `site.json` (HTML; it may use `{{markers}}`, and an empty string removes the line); it replaces the automatic line whatever contact data exists. A new locale must define the three `lead_strip_contact*` keys.

> **Changing the wording of the engine's texts** (`generated_content.locale_overrides`). The default copy of the home resources section, the guides and blog indexes, the closing strip and the `llms.txt` labels is generic ("your business") and lives in `legible/locales/`, which a site does not edit. To change any of it, put an object `{locale key: new text}` in `src/data/site.json`:
>
> ```json
> "generated_content": {
>   "locale_overrides": {
>     "home_resources_heading": "Resources from {{site_name}}",
>     "guides_index_lead": "Practical help from the {{site_name}} team.",
>     "llms_guides_description": "Guides written by {{site_name}}."
>   }
> }
> ```
>
> The valid keys are exactly the keys of `legible/locales/<language>.json`. The build checks every override and reports **all** the problems at once, naming the key, instead of publishing the default text by mistake: an unknown key (with a "did you mean" suggestion), an empty or blank text, a text of the wrong kind (`months` is a list of exactly 12 texts) and a `{placeholder}` that the default text does not receive (a text may leave a placeholder out, never invent one). `{{markers}}` such as `{{site_name}}` are always allowed and are resolved in every place, `llms.txt` included. Order of precedence: a per-section value (`generated_content.guides_index.heading`, `lead_strip.headline`…) beats an override, and an override beats the locale file. With no `locale_overrides` the output is byte for byte what it was.
>
> | Keys | Where they appear | Format | Placeholders |
> |---|---|---|---|
> | `months`, `long_date` | dates on cards and pages | text | `long_date`: `{day}` `{month}` `{year}` |
> | `breadcrumb_*`, `nav_guides`, `nav_blog`, `card_read_*` | breadcrumb, menu, eyebrows, card links, JSON-LD | text, escaped by the engine | none |
> | `lead_strip_action_label`, `lead_strip_eyebrow`, `lead_strip_headline`, `lead_strip_button` | closing strip | text, escaped | none |
> | `lead_strip_lead_html` | closing strip, lead | **HTML** | `{action_link}` |
> | `lead_strip_contact`, `lead_strip_contact_email_only`, `lead_strip_contact_whatsapp_only` | closing strip, contact line | **HTML** | `{email}` `{whatsapp}` |
> | `home_resources_*` | "resources" section of the home page | **HTML** | none |
> | `guides_index_title`, `guides_index_description`, `guides_index_heading`, `guides_index_extra_heading`; the same four for `blog_index_*` plus `blog_index_list_heading`, `blog_index_criteria_heading` | `<title>`, description, headings | text, escaped | none |
> | `guides_index_lead`, `guides_index_intro`, `blog_index_lead`, `blog_index_intro`, `blog_lead_guides_link`, `blog_lead_guides_text` | introduction of each index | **HTML** | `blog_index_lead`: `{guides_txt}`; `blog_lead_guides_link`: `{guides_url}` |
> | `llms_guides_description`, `llms_blog_description` | `llms.txt` | plain text | none |
>
> "HTML" texts are inserted as they are, so write `&amp;` for `&`; "text" is escaped for you. Titles and descriptions are still subject to the validator's length limits and to the rule that every page has its own.

Mental rule: **`src/` changes per site; `legible/` is the engine and does not.**

### 2.2 Folder structure

```text
.
├── README.md                  Project presentation
├── DOCUMENTATION.md           This document (full reference and AI guide)
├── AGENTS.md                  Entry point for AI agents (mode, interview, plan and execution protocol)
├── SITE_PLAN.md               Phased plan and its status (created by the interview and returned inside the zip; not part of the template)
├── LICENSE · readme-logo.svg · .gitignore
├── legible/                   ENGINE (reusable, not edited per site)
│   ├── build.py               Generator
│   ├── check_site.py          Validator for the compiled output
│   ├── build.sh               Build + strict validation (what CI runs)
│   ├── dev.py                 Local server that rebuilds when src/ changes
│   ├── run_all.py             Tests → build+validate → dev server
│   └── locales/               en.json · es.json — engine-generated strings
├── src/                       CONTENT (edited per site)
│   ├── data/                  site.json · entity.json · texts.json
│   ├── pages/                 one folder per URL (index.html with front matter) + 404.html
│   ├── partials/              header.html · footer.html
│   ├── layout.html            Document shell and <head>
│   ├── css/site.css           Single stylesheet; design tokens at the top
│   └── static/                Images, favicons, robots.txt, llms.txt (copied to output root)
├── tests/test_legible.py      Regression suite (unittest)
├── dist/                      Build output (ignored by Git)
└── .dev-dist/                 Dev-server output (ignored by Git)
```

### 2.3 Responsibilities

| Piece | Does | Does not |
|---|---|---|
| `build.py` | Load data, resolve markers, compose pages, JSON-LD, collections (guides/blog), minify, sitemap, robots, llms.txt | Judge SEO quality (the validator does) |
| `check_site.py` | Validate `dist/` | Modify anything |
| `build.sh` | Run build, then strict validation, driven by env vars | Business logic |
| `dev.py` | Serve `.dev-dist/`, rebuild on change (polls every 0.5 s) | Serve anything outside `.dev-dist/` |
| `run_all.py` | Tests → `build.sh` → `dev.py`, stopping at first failure | — |
| `layout.html` | `<head>`, metadata, shell, floating WhatsApp link | Page content |
| `partials/` | Header with menu, footer with navigation and legal links | — |
| `site.css` | Styling via `:root` tokens; no JS, no motion | — |

### 2.4 Exact flow of `build.py`

1. Load `site.json`; apply `SITE_URL` (env wins; an empty `SITE_URL` counts as not set); **abort unless it starts with `https://`**. Check that `language` is supported, load its locale file and apply `generated_content.locale_overrides` on top of it (validated; an invalid override stops the build and names the key).
2. Refuse an output folder that is, or contains, the project, `src/` or `legible/`; then empty it.
3. Copy `src/static/`; write the (optionally minified) CSS.
4. Read `entity.json` and compute the derived values (section 3.2). Load and validate the guide/blog front matter and report **every** problem at once.
5. Build the marker table: `texts.json` first (on top of an optional `site.json › text` object), then the derived values (**derived values win**). Markers are replaced repeatedly (up to 5 passes), so a text may reference another text defined earlier or later; a circular reference (a → b → a) stays unresolved and the build fails with a marker that has no value.
6. Resolve markers in layout, partials and `entity.json` nodes; fill the navigation, footer-blog and year markers.
7. For each page in `src/pages/`: front matter → active menu entry → `geo.*` tags → canonical → merged JSON-LD `@graph` → **fail on any leftover `{{…}}`**.
8. Generate `/guides/` and `/blog/` indexes (at their configured paths) when their rules are met (section 3.5).
9. Write `sitemap.xml`; resolve `robots.txt` and `llms.txt`.
10. Run the validator (unless `--no-validate`) and print the report.

### 2.5 Escaping

| Destination | Rule |
|---|---|
| HTML | **Derived** values (name, city, `{{target_audience}}`…) are HTML-escaped; values from `texts.json` are **not** (they may contain HTML on purpose) |
| JSON-LD | Values are JSON-escaped; `&` and quotes cannot break the JSON |
| `robots.txt` / `llms.txt` | Plain-text substitution |
| Empty JSON-LD values | Dropped (an empty `price_range` is not published) |

---

## 3. Content model

### 3.1 The three data files

| File | Holds | Notes |
|---|---|---|
| `src/data/site.json` | Project settings: `site_url`, `site_name`, `language`, `project_stage`, `contact_email`, `phone_e164`, `whatsapp_message`, `city`, `region`, `geo_enabled`, `geo_region_code`, `price_range`, `build_banner`, `check_banner`, `generated_content`, `collection_topics`, `collection_paths` (default `{"guides": "guides", "blog": "blog"}`: folder and URL of each collection, lowercase ASCII slugs with hyphens, different from each other), `sitemap_base_order`; optionally `text`, an object of extra marker values. `generated_content` also takes `locale_overrides`, an object that replaces engine-generated texts (section 2.1) | Empty `geo_region_code`/`price_range` are simply omitted from the output. Keys of `texts.json` win over `text`. `project_stage` (`template`, `in_progress` or `complete`) is ignored by the build and the validator; only an AI reads it (section 5.0) |
| `src/data/entity.json` | Business identity in Schema.org: a `ProfessionalService` node and a `WebSite` node | **Keep the `ProfessionalService` type**: cities (`areaServed`), categories (`knowsAbout`) and offers (`hasOfferCatalog`) are read from it |
| `src/data/texts.json` | Reusable copy: key `x` becomes marker `{{x}}` | Derived values override same-named keys |

### 3.2 Derived markers

Full catalogue in section 7.1. In short: identity (`site_name`, `site_url`, `contact_email`), language (`lang`, `og_locale`, `in_language`), contact (`whatsapp_link`, `whatsapp_base`, `phone_e164`, `phone_digits`), place (`city`, `region`, `location`, `city_1…4`), services (`service_category_1…6`, `service_N_name/price/price_number` for N=1…5, `featured_action_name`), `_url` variants for WhatsApp messages and `target_audience`.

**The offer priced `0` in `hasOfferCatalog` is the "featured action"** (page `/featured-action/`). There must be exactly one.

**`{{target_audience}}`** is computed from the names in `areaServed`: the text `businesses in ` followed by the first three names joined with `, `. It is a derived marker like the others: escaped for HTML and JSON-LD, and usable in `robots.txt` and `llms.txt` too. Every `areaServed` entry must be an object such as `{"@type": "City", "name": "Your City"}`. If `areaServed` is empty the marker stays unresolved and the build fails wherever it is used (the sample `footer_about` text uses it). The wording is fixed in English in `build.py`, so a site in another language that does not want it simply leaves the marker out of its texts.

### 3.3 Pages and front matter

Each page is `src/pages/<slug>/index.html` (URL `/<slug>/`) and starts with:

```text
---
title: Page title | {{site_name}}
description: A 70–160 character summary.
robots: index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1
geo: true
canonical: auto
updated: 2026-01-31
---
```

- Required: `title`, `description`. `updated` is required on indexable pages. The sitemap `lastmod` comes from the `dateModified` of the page's JSON-LD if it has one, or from `updated` if not; when both exist they must be the same date or the build fails. `last_update` in `texts.json` (used by the legal pages and `llms.txt`) is a third, independent value: update it by hand together with the other two.
- `canonical: none` + `robots: noindex, follow` → pages such as the 404.
- `active` forces which menu entry is highlighted; otherwise the page's own entry or its closest parent.
- The page's `<script type="application/ld+json">` block is extracted and merged with the business nodes into one `@graph`.
- `geo` is an engine feature flag (emit `geo.*` meta tags); the name stays. When it is absent, `site.json › geo_enabled` decides.

### 3.4 Template pages and URLs

| Page | URL (English sample) |
|---|---|
| Home | `/` |
| Services index | `/services/` |
| Sample service | `/services/sample-service/` |
| Pricing | `/pricing/` |
| Featured action | `/featured-action/` |
| About | `/about/` |
| Contact | `/contact/` |
| Legal notice | `/legal-notice/` |
| Privacy policy | `/privacy-policy/` |
| Cookie policy | `/cookie-policy/` |
| 404 | `/404.html` |

The four "Service 1–4" menu entries all point to the sample service page; that is intentional placeholder content. Real sites must point each to its own page.

### 3.5 Optional collections (guides and blog)

| Collection | Content path | `type` | Generated index |
|---|---|---|---|
| Guides | `src/pages/guides/<slug>/index.html` | `guide` | `/guides/` once there is one guide, grouped by topic |
| Blog | `src/pages/blog/<slug>/index.html` | `article` | `/blog/`, newest first |

Each piece needs: `type`, `topic` (one of `collection_topics`), `published`, `updated` (ISO, `updated ≥ published`), `summary`, `service` (an existing path), `title`, `description`. Lowercase-hyphen slug. `related`: at most 2, each an existing guide or article other than the piece itself. **Never hand-create an `index.html` inside the guides or blog folder.**

Blog visibility: 0 articles → no blog; 1–2 → exists as `noindex`, not in menu, footer, sitemap or `llms.txt`; ≥3 → indexable and announced.

The folder names are configurable (`collection_paths`), so a Spanish site can use a localized folder and URL such as `/guias/`.

### 3.6 Generated outputs

HTML per URL · `css/site.css` · JSON-LD per page · `sitemap.xml` (indexable pages only) · `robots.txt` (allows GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Applebot, Meta-ExternalAgent) · `llms.txt` · floating WhatsApp link (`wa.me`, no script).

### 3.7 Sample brand assets

`logo.svg`, `favicon.svg`, `favicon.ico`, `apple-touch-icon.png` and `og-image.png` are legible's own branding, used as neutral placeholders. They contain no agency branding. Every real site replaces them.

---

## 4. Language policy and naming conventions

### 4.1 The rule

| Layer | Language |
|---|---|
| Architecture: code, identifiers, comments, docstrings, console messages, tests, file/folder names under `legible/` and `tests/`, data-file names, marker names, JSON keys, README, this document, `AGENTS.md` | **English, always** |
| The sample site in `src/` (pages, texts, menu, legal pages, `llms.txt`, URLs) | **English**, generic, no trace of any specific business or agency |
| A real site in another language (e.g. Spanish) | The content and URLs of **that site** follow that language; the architecture does not change |

### 4.2 How to build a site in another language

1. `site.json`: `"language": "es"` → `<html lang="es">`, `og:locale es_ES`, `inLanguage es-ES`, `availableLanguage es`, Spanish month names and Spanish engine-generated strings (breadcrumb, index headings, card links, lead strip, `llms.txt` section labels). The supported values are the languages listed in `LANGUAGES` in `legible/build.py` (`en` and `es`); any other value stops the build.
2. Translate everything under `src/`: pages, `texts.json`, layout, partials, `llms.txt`, legal pages.
3. Rename page folders to localized slugs (e.g. `services/` → `servicios/`); update header/footer links, `sitemap_base_order`, internal links and `generated_content.lead_strip.action_url`.
4. `site.json`: `"collection_paths": {"guides": "guias", "blog": "blog"}` for localized collection URLs. Rename the folders under `src/pages/` to match.
5. Keep markers, JSON keys, front-matter keys and `type` values (`guide`, `article`) **in English**: they are the architecture.
6. Unresolved-confirmation markers: the validator matches `[CONFIRM`, which also catches `[CONFIRMAR …]`.
7. `{{target_audience}}` is built with an English phrase (section 3.2); leave it out of translated texts.
8. The engine's generic copy ("your business") can be reworded for the site, in any language, with `generated_content.locale_overrides` (section 2.1); never edit `legible/locales/` for one site.

**Any other language** needs two things: a file `legible/locales/<code>.json` (copy `en.json` and translate every value; a missing key stops the build) and a row `'<code>': (html lang, og:locale, inLanguage)` in the `LANGUAGES` table of `legible/build.py`. That table row is the only engine edit a new language requires. Then set `language` to the new code.

### 4.3 Naming conventions

- Python: `snake_case` functions and variables, `UPPER_SNAKE` constants, `CamelCase` classes.
- JSON keys and markers: `snake_case`. URL slugs and folders: `kebab-case`, ASCII.
- Comments and identifiers are plain ASCII. Console reports may use symbols such as `✓`, `✗` and box-drawing characters. The exceptions are the user-facing strings of non-English locale files (`legible/locales/es.json`) and test fixtures that deliberately exercise Spanish or Unicode.
- Comments explain *why*, in one short sentence.
- Some names are engine vocabulary and stay as they are on every site: the `geo` front-matter flag, the `{{geo}}` marker, the `geo.*` meta tags, `llms.txt`, the AI-crawler entries in `robots.txt` and the `{{llms_*}}` markers.

---

## 5. Guide for an AI to generate a site from this base

This part is a **contract**: an AI that reads it together with the repository and receives a **briefing** must be able to produce a complete site without breaking the engine.

### 5.0 The methodology: start, interview, plan, phases, completion

This is how an AI and a person build the base of a site together with legible. It exists so that the AI does the right thing from the first message, does not redesign the engine, and leaves a written trail that survives between sessions.

**Where the rules live.** The procedures, numbers, limits and commands are in [`AGENTS.md`](AGENTS.md), which is the source of truth. This section explains why the method is built this way and holds the reference tables (the fit check, and what each interview answer decides). It points to `AGENTS.md` instead of repeating it, so a change is made in one place only.

**Principles**

1. **The AI looks for the plan first.** On entering the zip, `AGENTS.md` tells the AI to look for `SITE_PLAN.md`. If it exists, the AI continues the plan, whether the user says `legible continue` (or anything similar, in any language) or says nothing specific. If it does not exist, `legible start` starts the interview. No other prompt is needed. The routing table is in `AGENTS.md` section 1.
2. **Anything else gets an explanation first.** With no plan, any request that is not `legible start` makes the AI explain what legible is, what it fits, which SEO checks it includes (section 1.0) and how it is used, and only then answer. With a plan, the AI explains the same way when the user clearly asks for something other than continuing (a question, an engine change, something outside the base). It never starts an unusual job before warning how legible works.
3. **One job by default: adapt `src/`.** The engine, the tests and the architecture are fixed. They change only through the recorded exception in `AGENTS.md` section 7. Deployment is outside the process.
4. **Ask little, propose a lot.** The interview asks only what the AI cannot derive. Page list, URLs, menu, design direction and phases are proposed by the AI and confirmed by the user.
5. **Never invent.** What the user does not know becomes a visible `[CONFIRM …]` marker and a row in the plan's pending table.
6. **One phase per session, with real checks.** A phase is `done` only after its verification actually ran.
7. **The plan is the memory, it travels inside the zip, and it stays small.** `SITE_PLAN.md` lives in the root of the project. The AI returns the zip with the plan inside, so the plan travels with the project; when that zip is attached to a new session, the AI finds the plan and continues. A new session knows nothing else, and it reads the whole plan every time, so the plan is the base structure only: a briefing, a URL map, a few small phases and the lists of pending facts and Later items. Detail is decided when each phase runs, not written in advance.

**The stage beacon.** `src/data/site.json` carries one field, `project_stage`, with three values: `template` (the untouched base), `in_progress` (set when phase 1 starts) and `complete` (set when the plan finishes). `complete` also means that the site is in detailed work and the flow no longer applies, even if the plan is gone (see refinement mode below). The engine ignores it, so it needs no engine change. While the plan exists and phase 1 has not started, the field is still `template`; that is consistent because the AI always looks for the plan before it reads the field. It is a coarse beacon that lives in the project data, next to the content, so it survives if `SITE_PLAN.md` is deleted; the plan remains the only place with detail and status. If the two disagree, the AI trusts the plan, corrects the field and notes it in the log.

**Why the plan is called `SITE_PLAN.md`.** It holds the plan of the site and, as work advances, its state. The name says what it is (the plan of this site) and avoids any confusion with the engine's own build files.

**The control surface: what tells the AI what**

The method keeps its state in three places, and the user's message adds a fourth. Each signal has one owner and one meaning, so an AI never has to guess.

| Signal | Lives in | Survives the session? | Set by | Meaning |
|---|---|---|---|---|
| `FLOW_OFF.lock` | A file in the project root | Yes, until deleted | The maintainer (`legible flow off` / `legible flow on`) | The AI flows are off: ordinary repository work |
| `SITE_PLAN.md` | A file in the project root, inside the zip | Yes, it travels with the zip | The AI | Which phase comes next, or that the plan is complete |
| `project_stage` | A field in `src/data/site.json` | Yes | The AI | `template`, `in_progress` or `complete`: a coarse beacon for when the plan is missing |
| The user's message | The conversation | No | The user | A command (`legible start`, `legible continue`, `legible help`, `legible flow off`, `legible flow on`) or any other request |

**Precedence.** The lock wins over everything; then the plan; then `project_stage`; and only then the message. This is also the order of the routing table in `AGENTS.md` section 1.

**Engine mode is deliberately different: it is not state.** It has no file and no field. It exists only in the session where the user asks for a change to `legible/` or `tests/` and confirms it. Because nothing persists, the AI makes it visible: it says `Engine mode on: <the change>` when it enters and ends its final message with `Engine mode off` and the record of what changed (the plan's **Engine notes**, or the final message and `CHANGELOG.md` when there is no plan). The next session starts again with the engine fixed.

**Why a lock file for the flows and not for the engine.** The two switches serve different people. The flows switch is for the maintainer, who works on the project across many sessions and needs the setting to stay put, so it is a file; the maintainer must remove it before packaging, which `.gitignore` and the test suite enforce. Engine mode is an occasional, justified exception for someone building a site, so it stays short-lived and visible in the conversation instead of becoming a setting that could linger.

**What the AI does when the request is not `legible start` or `legible continue`**

The cases (a question, a partial fit, something outside the base, a request to change the engine, a deployment request, a review or audit) and the answer to each are in the requests table in `AGENTS.md` section 1.

**Fit check**

legible is a generator for one local service business per site. The AI checks the fit in interview question 1 and says so openly instead of forcing it.

| Fit | Examples | Response |
|---|---|---|
| Good | Clinic, workshop, consultancy, cleaning, trades, studio with services and a contact route | Continue |
| Partial | Business with a large catalogue (the shortcuts cover 6 categories and 5 offers), bookings or orders, several languages at once (the base has one `language` setting per site), several locations that each need their own pages | Say what does not fit, what would go to **Later**, and what the options are; continue only after the user confirms |
| Outside the base | Online store, CMS, user accounts, client-side JavaScript, external widgets, fonts or trackers, another framework | Explain, offer options (**Later**, an engine exception, or another tool) and wait for the decision |

**Decision flow**

This diagram summarizes the routing table in `AGENTS.md` section 1. If they ever differ, the table wins.

```mermaid
flowchart TD
    A[User message with the zip] --> L{FLOW_OFF.lock in the root?}
    L -->|Yes| N[Flows off: ordinary repository work, no interview or plan, engine changes recorded in CHANGELOG.md]
    L -->|No| B{SITE_PLAN.md in the zip?}
    A -.->|legible help, in any state| C
    B -->|Yes| K{Continue, start or nothing specific?}
    K -->|Yes, phases left| H[Execute the next pending phase, update the plan, return the zip]
    K -->|Yes, complete| I[Maintenance: report the final state, work on the part the user names]
    K -->|No, another request| C
    B -->|No| M{project_stage in site.json?}
    M -->|In progress| R[Recovery: audit the project, rebuild SITE_PLAN.md, confirm]
    R --> G
    M -->|Complete| Q[Refinement: no flow, work on the part the user names]
    M -->|Template| E{legible start?}
    E -->|No| C[Explain legible, its fit, its checks and how it is used]
    C --> D[Answer according to the request: question, limits, engine, review]
    E -->|Yes| F[Full interview, or fast start when the message has inputs: a style URL, fields or images]
    F --> G[Return the zip with SITE_PLAN.md inside]
    G --> H
    H -->|Last phase done| J[Plan complete: Final state recorded in SITE_PLAN.md]
    J --> I
```

**The interview**

Twelve questions in three rounds, listed in `AGENTS.md` section 4. They run only when `legible start` comes with no inputs; with a style URL, fields in one line or images the AI runs the shorter **fast start** (section 6.1.1). The AI skips what the user already said, writes in the user's language and changes no project file; the only thing it adds is `SITE_PLAN.md`. Each answer decides something concrete:

| Question | Decides | Lands in |
|---|---|---|
| 1 Business and kind | The fit check; the `ProfessionalService` identity | `entity.json`, plan briefing |
| 2 Language and tone | `language`, translated content, localized slugs, `collection_paths` (section 4.2) | `site.json`, every page |
| 3 Domain and existing URLs | `site_url`, canonical URLs; existing URLs are only noted (legible generates no redirects, and deployment is outside the process) | `site.json`, plan URL map |
| 4 Place | City, region, country, address fields, `geo` settings | `site.json`, `entity.json` |
| 5 Contact | Email, phone, WhatsApp link (or its removal) | `site.json`, `layout.html` |
| 6 Service area | `areaServed` and the `city_1…4` shortcuts | `entity.json` |
| 7 Services | Categories (`knowsAbout`), one page per real service, its URL | `entity.json`, `src/pages/`, header, services index |
| 8 Offers | `hasOfferCatalog`, currency, the single offer priced 0 | `entity.json`, pricing and featured-action pages |
| 9 Design | Colour tokens, logo, favicon, social image; the limits of the base (one stylesheet, system fonts, no external resources, no JavaScript) | `src/css/site.css`, `layout.html`, `partials/`, `src/static/` |
| 10 Hours and legal | `openingHoursSpecification` or none; legal pages with `[CONFIRM …]` where data is missing | `entity.json`, legal pages |
| 11 Later | What stays out of the base | plan **Later** list |
| 12 Unknowns | The pending-confirmation table | plan |

After round 3 the AI shows what it understood and proposes the URL map, the design direction and the phases. The user confirms or corrects, and only then does the AI deliver the plan.

**Delivering the plan**

The AI creates `SITE_PLAN.md` in the root of the project and returns the complete project as a zip with the plan inside. That is deliberate: the zip is the only thing that travels between sessions, so a plan that is not inside it is lost (principle 7). A zip that lost files (a truncated listing, a skipped folder) breaks the next session, so the AI compares the file list of the zip it returns with the original's before handing it over. The exact procedure, including that comparison and what to do when a zip cannot be created, is in `AGENTS.md` section 5.

**Keeping the plan small.** The interview must not produce a big plan: a new session reads the whole plan every time, and a long plan uses context that the work itself needs. The limits (length of the file, lines per phase, the URL map, the Later list, the execution log, and what does not belong in the plan) and the commands that measure them are in `AGENTS.md` section 5. They are measured, not estimated, because an estimate of length is unreliable.

If a request does not fit in the base, it goes to **Later**.

**The phases**

The plan is a short list of phases, each small enough to finish in one session of a free-plan chat with room to spare. The default catalogue, the session budget, how to adapt the catalogue to a site and the default `Read:` line of each phase are in `AGENTS.md` section 5. The method behind them:

- **Design and content are each split into several phases**, because they are the largest and least predictable parts of the base (the stylesheet and the pages are its biggest files), and a phase that does not finish costs more than an extra phase.
- **A phase the site does not need stays in the plan as `done`, with the reason**, instead of being deleted. The numbering stays stable between sessions and the freed slot can be used to split a heavy phase.
- **The brand-assets phase never fakes binary images.** An AI can write SVG, but not a real PNG or ICO. The sample `og-image.png` stays in place (the validator requires that file to exist), and each sample binary is listed as pending until the user supplies the real one.
- **Each phase reads only what it needs**, through its `Read:` line, so no session has to load this whole document.
- **The phases map onto the stages of section 5.4**, which describe the work itself and are used as they are in one-session mode.

The plan format, the statuses (`pending`, `in_progress`, `done`, `blocked`) and the exact protocol are in `AGENTS.md` sections 5 and 6.

**A session in execution mode**

The user attaches the zip that contains `SITE_PLAN.md` and says `continue` (or anything similar, or nothing specific). The AI takes the first phase that is not `done`, reads only what that phase lists, works only in `src/`, verifies the phase with real commands, updates the plan and returns the zip. The steps and the verification rules are in `AGENTS.md` sections 6 and 9.

Two principles explain most of the design: **one phase per session**, so no session is asked for more than it can finish and verify; and **real checks**, so a phase is `done` only after its verification actually ran. The strict build is relaxed only for warnings that come from facts still pending, and never in the last phase; an AI that cannot run commands says so and never claims a pass.

**Completion and maintenance**

When the last phase is `done`, the plan is marked `complete`, `project_stage` becomes `complete`, and the plan's **Final state** records the state of everything, so a later session does not have to rediscover it. From then on, attaching the zip starts maintenance mode: the AI reports the final state and works only on the part the user names. This lets the user improve the site part by part without repeating the interview. The steps are in `AGENTS.md` section 6.

**Recovering a missing plan**

If the zip holds an adapted site but no `SITE_PLAN.md` (the file was deleted or never returned), the AI does not start the interview from zero, because the phases would rewrite work that already exists. It reads `project_stage` in `src/data/site.json`. The table in `AGENTS.md` section 1 says what to do for each value, including the fallback for older zips that lack the field.

- **Recovery mode** (`in_progress`) rebuilds a short plan from evidence: the data files, the pages, the design tokens, the baseline and the pre-launch sweep (sections 7.3 and 7.4). A phase is marked `done` only when the evidence supports it, a fact that is not in the files is never guessed, and the user confirms the plan before it is used.
- **Refinement mode** (`complete`) applies no flow at all: the AI works only on the part the user names. Starting over from zero requires an explicit request and a warning that the interview and the phases would rewrite the existing site.

The steps are in `AGENTS.md` section 6.

**Out of scope: deployment.** The AI does not deal with hosting, DNS, CI, publishing or host-level redirects. Section 7.6 is a reference for people.

**Why it is built this way.** An AI without a protocol tends to refactor what it was not asked to touch, invent facts to fill gaps, drift into unrelated work and lose context between sessions. The start command, the explanation for anything else, the fit check, the confirmed plan that travels inside the zip, the one-phase sessions, the recorded exceptions and the final state each remove one of those failure modes.

### 5.1 What the AI must understand

- legible = an **engine** (`legible/`) + a **template** (`src/`). To create a site, **only `src/` changes** (plus `site.json`'s settings). The AI does not improve or refactor the engine on its own initiative.
- Business facts live in three files and spread through `{{markers}}`.
- The validator is strict: any warning stops the build. That is fixed by correcting content, **never** by relaxing rules or tests.
- No JavaScript, no dependencies, no frameworks — none are added.
- Facts the client did not provide are **never invented**. In a real project they stay as visible `[CONFIRM …]` markers (the validator flags them, which is intended: it blocks launch until filled).
- The sample site is English and generic. If the briefing says the site must be in another language, follow section 4.2.

### 5.2 Briefing the AI must receive

The twelve-question interview in `AGENTS.md` section 4 collects the subset needed for a first version and records it in `SITE_PLAN.md`; the table below is the complete set a site can use. Extra items go to the plan's **Later** list.

Minimum set (if something is missing, the AI **asks or marks it pending** — it does not invent it):

| Block | Fields |
|---|---|
| Identity and fit | Business name, domain (HTTPS), one-line description, kind of business (fit check, section 5.0) |
| Contact | Email, phone (E.164), is WhatsApp confirmed? yes/no |
| Location | City, region, street address (if customers visit), ISO 3166-2 `geo_region_code` (optional), country |
| Service area | Up to 4 cities with shortcuts; others as plain list |
| Services | Service list grouped into ≤6 categories; up to 5 priced offers; currency |
| Featured offer | Exactly one offer priced 0 (name, what it includes / excludes) |
| Price range | `price_range` or empty |
| Hours | Confirmed hours or "no hours" |
| Audience | Who the site speaks to |
| Tone | Formal/friendly; (Spanish sites: tú/usted) |
| Legal | Legal name, tax/registration ID, registered address, governing law |
| Design and brand | Logo, favicon, 1200×630 social image, colours, a reference site, or "keep the base look" |
| Collections | Guides? Blog? How many pieces, which topics |
| **Language** | `en` (default) or another; for non-English also the desired URL slugs |
| **URLs** | Existing URLs that must be kept (legible generates no redirects; the host handles them) |
| **Not provided** | An explicit list of what is unknown and must not be invented |

**Fill-in template**

```text
BUSINESS BRIEFING (optional shortcut: fill in and paste it so the interview can skip these questions)
Name:
Domain (https):
One-line description:
Email:            Phone (E.164):            WhatsApp confirmed (yes/no):
City:             Region:           Country:       Street address (only if customers visit):
ISO 3166-2 geo_region_code (optional):
Service area (up to 4 cities with shortcuts; others as a plain list):
Services (grouped into at most 6 categories):
Priced offers (at most 5):                 Currency:
Featured offer (exactly one, priced 0): name / includes / excludes:
price_range (or empty):
Opening hours (confirmed hours, or 'no hours'):
Audience:                 Tone (formal or friendly; tú or usted for Spanish):
Legal: legal name / tax or registration ID / registered address / governing law:
Design: logo / favicon / 1200x630 social image / colours / reference site, or 'keep the base look':
Existing URLs to keep (legible generates no redirects):
Collections: guides? blog? how many pieces and which topics:
LANGUAGE: en (default) or other. URL slugs for non-English sites:
NOT PROVIDED (the AI must not invent these):
```

### 5.3 Invariants the AI must not break

1. Always `{{site_url}}` for the domain in pages; set `site_url` in `site.json` and also build with the `SITE_URL` env var.
2. Keep the `ProfessionalService` node, type and `@id`. Add real address fields only if provided; no invented coordinates or ratings.
3. Shortcuts cover 4 cities / 6 categories / 5 offers. Anything beyond is written literally on its own page.
4. Exactly one offer priced `0`; keep the featured-action URL consistent across `lead_strip.action_url`, `sitemap_base_order`, header, footer and `llms.txt`.
5. Sample values (`Service 1`, `Your City`, `$99`, `Topic 1`, `Free Consultation`, `YOUR-DOMAIN`…) **pass the validator**, so **all must be replaced**, and `sitemap_base_order` updated.
6. Every page: `title` 20–60, `description` 70–160, one `h1`, ≥250 words in `<main>` if indexable, `updated: YYYY-MM-DD`, a JSON-LD block, and at least one contextual inbound link from another page's `<main>`. Unique titles and descriptions. Visible FAQ and FAQ JSON-LD identical word for word.
7. New service pages: copy `services/sample-service/`, give each a distinct purpose, add to the menu (`header.html`) and the services index. **No near-duplicate pages per town or keyword.**
8. Images: accurate `alt`, explicit `width` and `height`.
9. WhatsApp: if the phone is not confirmed for WhatsApp, say so and propose removing the floating link (layout) and the WhatsApp calls to action.
10. Legal pages use only provided data; missing items stay as `[CONFIRM …]` (the sample pages use neutral placeholders such as `Your legal name` so the template passes the validator; the pre-launch sweep finds them); do not state legal obligations as fact; recommend legal review. Hours, response times and limits appear in several files; remove or replace every one, and delete `openingHoursSpecification` if no hours were provided.
11. No guides/blog unless requested; if created, follow section 3.5 (≥3 articles for an indexable blog).
12. No JavaScript, no dependencies, no external resources. Do not edit `legible/` or `tests/` to get around a failure. The only engine change allowed is the recorded, minimal exception in `AGENTS.md` section 7, and it never weakens a test or a validator rule. Interactive features (calculators, booking, forms with a backend, maps) are not part of the base: they go to **Later**, or are listed in the plan as an exception that needs an explicit decision. The built-in SEO checks (section 1.0) are part of the base and are always used.
13. Never invent testimonials, awards, certifications, years in business or figures.
14. **Non-English sites:** apply section 4.2 completely (language setting, translated content, localised slugs, `collection_paths`) and keep markers, keys and `type` values in English.

### 5.4 Stages (the AI stops after each one if asked to)

The stages are the work inside the plan's phases: S0 is the interview; S1 is phase 1 (data); S2 is phase 2 (structure and URLs); S3 is phases 3 to 6 (brand tokens, component styles, layout and partials, brand assets); S4 is phases 7 to 9 (content); S5 and S6 are phase 10 (legal and close). Collections (guides and blog, section 3.5) are not part of a first version and go to **Later** unless the user insists; if they are built, they are an extra stage after S4. A plan phase is one session. In one-session mode the stages run in order in a single session.

| Stage | What it does | Checked with |
|---|---|---|
| S0 Read | Read `AGENTS.md`, this document and `README.md`; inspect `src/data/*.json`, `layout.html`, `partials/`, one page, `llms.txt`. In one-session mode, reply with a short plan and the list of missing briefing data. In phased mode this stage is the interview and the output is `SITE_PLAN.md` | Plan delivered |
| S1 Data | Fill `site.json`, `entity.json`, `texts.json` | `SITE_URL=… ./legible/build.sh` (may fail on pages not yet adapted) |
| S2 Structure | Decide pages, URLs and menu; create or remove service pages; update `sitemap_base_order` and internal links | Menu, internal links, `sitemap_base_order` |
| S3 Design and brand | Colour tokens in `site.css` (phase 3), component styles (phase 4), layout and partials within the invariants (phase 5), logo, favicon, social image (phase 6) | Build; look at the output in the dev server |
| S4 Content | Write pages following section 5.3 rule 6 | Strict validator |
| S5 Legal | Legal pages with `[CONFIRM …]` where data is missing | Pre-launch sweep (section 7.4) |
| S6 Close | Full baseline; inspect `dist/` (sitemap, robots, llms.txt, JSON-LD of home and one service page) | Final report |

### 5.5 Definition of done

**For a phase** (one session):

- The phase's verification **actually ran** with real results; the phase is `done` only then. The rules for warnings that come from pending facts, and for an AI that cannot run commands, are in `AGENTS.md` section 9.
- `SITE_PLAN.md` is updated: status, date, verification, execution log, pending confirmations and Later list.
- The complete zip (without `dist/`) is returned with the changes and the updated plan.

**For the plan** (all phases `done`, overall status `complete`):

- Tests and strict build **actually run** and green, or remaining failures listed and justified.
- Pre-launch sweep resolved or each hit justified.
- `dist/` inspected, not just sources.
- The **Final state** section of `SITE_PLAN.md` is filled with the state of everything: what changed, the real results of the commands, the facts still awaiting confirmation (including expected validator warnings) and the Later list.
- The user is told that the plan is finished and that the state is recorded inside the zip. Deployment is not mentioned.

---

## 6. Prompt templates

### 6.1 Start a site (interview and plan)

Attach the zip and say the start command, exactly as written and in English whatever language you speak:

```text
legible start
```

It has no aliases and no translations. Phrases such as `start site`, `run legible` or `ejecutar legible` are not commands: the AI answers with a short explanation of what `legible` is and the list of commands. With no `SITE_PLAN.md` in the zip and the base untouched, `legible start` starts the interview and returns the zip with the plan inside. Followed by inputs, it starts a **fast start** instead (section 6.1.1).

### 6.1.1 The commands, and the fast start

| Command | What it does | It asks |
|---|---|---|
| `legible start` | Full interview (twelve questions, three rounds) | Everything |
| `legible start <url>` | Style from a website | The business name, and whether to keep the same theme |
| `legible start name: …; activity: …` | Your data in one line; the design is proposed from the theme | Nothing |
| `legible start <url> name: …; activity: …` | Style from a website plus your data | Nothing |
| `legible start` + attached images | An image of a design (style) and/or an image of the business data; `style: design.png; data: card.jpg` says which is which | Nothing if there are data; otherwise the name and the theme |
| `legible continue` | Continues the plan; with a plan, loose phrases in any language also work | Nothing |
| `legible help` | A simple explanation of what `legible` is, plus this list | Nothing |
| `legible flow off` / `legible flow on` | Turns the AI flows off or on for a working copy | Nothing |

**Fast start.** The full interview exists for someone who brings nothing. When the start command comes with inputs, the AI reads them, asks only for what is missing from a minimum (the business name and the theme) and writes the plan with no confirmation round. Every other fact is derived or left as a `[CONFIRM …]` row in the plan's **Pending confirmation**, to be settled later.

Examples (the businesses are made up):

```text
legible start https://example-style-site.com/
legible start name: Bodega La Esquina; activity: wine shop with tastings; city: Valdemoro; phone: 600 000 000
legible start style: https://example-style-site.com/; name: Bodega La Esquina; activity: wine shop with tastings
legible start style: design.png; data: card.jpg
```

The fields are `name`, `activity`, `city`, `phone`, `email`, `address`, `hours`, `services`, `style` (a URL, an image file name or a short description), `data` (an image file name) and `site` (the domain). Spanish names work too (`nombre`, `actividad`, `ciudad`, `tel`, `dir`, `horario`, `servicios`, `estilo`, `datos`, `web`). They go in any order, separated by `;`; only the first `:` of each field splits key and value, so hours and URLs are safe, and a value must not contain `;`. Free text with the same facts also works. When typed fields and an image or website disagree, the typed fields win.

| Inputs | What the AI asks |
|---|---|
| A style source only (URL, image or description) | One message: the business name, and whether to keep the same theme as the reference (if not, what the business does) |
| Any data, typed or read from an image | Nothing, unless the name or the theme is missing |

**What the AI may and may not write.**

| Kind | Rule |
|---|---|
| Facts: phone, email, address, hours, prices, years in business, awards, certifications, reviews, figures, legal data | Never invented. They come from the user or stay `[CONFIRM …]` |
| Descriptive copy: headlines, introductions, service blurbs, calls to action | May be written as short, generic examples on the theme, with no claim that could be checked. Each such page starts with `<!-- SAMPLE COPY -->` and is listed in **Pending confirmation**; the pre-launch sweep finds the marker |
| Facts read from an image | Used, and recorded as "read from image, verify" |

**How the style is read.** The AI uses what it can: the text of the page, or the image if it can see one. Some assistants read more than others, so the plan records how much was really read ("text only, palette estimated", "from a screenshot"). From the reference it takes the palette, the feel of the typography (mapped to system fonts), the order of the sections, the proportions and the shape of buttons and cards. It does not copy the reference's name, logo, images or text, and it does not build a page that could be mistaken for it. The base limits apply (one stylesheet, system fonts, no external resources, no client-side JavaScript), so fonts, carousels, animations and menus that need scripts are not imitated. If the AI cannot read the URL or see the image, it says so and asks for the other source (a screenshot or a short `style:` description) instead of inventing a style.

**`legible help`.** At most six short lines in plain words (what it is, what you get, what it fits, how it works, that deployment is not part of it), then the command table above and the state of the plan.

**Turning the flows off (for the maintainer).** `legible flow off` makes the AI create `FLOW_OFF.lock` in the project root; `legible flow on` deletes it. While the file exists the AI skips the interview, the plan and the explanations and treats the project as an ordinary repository, so the project itself can be edited and tested. The lock is a local switch: it is listed in `.gitignore`, and `tests/test_legible.py` fails if it exists, so it cannot reach a distributed zip unnoticed. Run `legible flow on` before packaging. The procedure the AI follows is in `AGENTS.md` section 1.

### 6.2 Continue the plan

Attach the zip that already contains `SITE_PLAN.md` (the one the AI returned) and say:

```text
legible continue
```

Any similar phrase works (`continue`, `next phase`, `continúa con el plan`, `sigue`), and so does saying nothing specific: on entering the zip the AI looks for the plan and, if it exists, continues it. The AI executes the next pending phase, updates the plan and returns the zip. When the plan is complete, the same command starts maintenance mode: the AI reports the final state and asks which part to work on.

### 6.3 Build everything in one session (optional)

Use it only when the user explicitly wants the whole site without a phased plan. It overrides the interview and the plan (`AGENTS.md` one-session mode); every other rule still applies.

```text
Read AGENTS.md first.

ROLE
Act as a careful senior web developer. Adapt the legible project into a complete, coherent website for the business below. Reuse the existing architecture and conventions. Add no frameworks, dependencies or client-side JavaScript. Do not touch legible/ or tests/.

START HERE
Read DOCUMENTATION.md fully (especially sections 3, 4.2, 5 and 7) and the "Configure a site" part of README.md. Then inspect src/data/*.json, src/layout.html, src/partials/, one page under src/pages/ and src/static/llms.txt. Reply with (1) a short plan listing the files you will change and (2) the briefing data that is missing. Then work through stages S1…S6 (section 5.4), running the checks after each and summarising the result.

BRIEFING: paste the filled template from 5.2

RULES
Obey the invariants in DOCUMENTATION.md section 5.3. If data is missing, leave a visible [CONFIRM …] marker or ask me; never invent it. Do not weaken validator rules or tests.

DONE WHEN
DOCUMENTATION.md section 5.5 is satisfied. Deliver the final report with its three sections.
```

---

## 7. Appendices

### 7.1 Marker catalogue

**Derived (computed by the build; they override `texts.json`):**

| Marker | Source |
|---|---|
| `{{site_name}}` | `entity.json` name, else `site.json` |
| `{{site_url}}` | `site.json` / `SITE_URL` |
| `{{lang}}`, `{{og_locale}}`, `{{in_language}}` | `site.json › language` |
| `{{contact_email}}` | `entity.json`, else `site.json` |
| `{{phone_e164}}`, `{{phone_digits}}` | `entity.json` telephone, else `site.json` |
| `{{whatsapp_link}}` | `https://wa.me/<digits>?text=<encoded message>` |
| `{{whatsapp_base}}` | `https://wa.me/<digits>` (no text; append `?text=…` by hand) |
| `{{city}}`, `{{region}}`, `{{location}}` | `entity.json` address, else `site.json` |
| `{{city_1}}`…`{{city_4}}` | `areaServed` |
| `{{target_audience}}` | `businesses in ` + the first three `areaServed` names (section 3.2) |
| `{{service_category_1}}`…`{{service_category_6}}` | `knowsAbout` |
| `{{service_N_name}}`, `{{service_N_price}}`, `{{service_N_price_number}}` (N=1…5) | `hasOfferCatalog` |
| `{{featured_action_name}}` | the offer priced `0` |
| `{{featured_action_name_url}}`, `{{service_1_name_url}}` | the above, URL-encoded |
| `{{price_range}}` | `entity.json`, else `site.json` |
| `{{geo_region}}` | `site.json › geo_region_code`, only if set |
| `{{home_resources}}` | Generated HTML: resources section when guides or a visible blog exist |

A field in `entity.json` falls back to `site.json` whether it is a `{{placeholder}}`, missing entirely, or `null` (for example no `contactPoint`, no `telephone`, or no `address` at all): none of these stop the build.

**Numbered slots and sample values.** `{{service_category_N}}`, `{{city_N}}` and `{{service_N_name}}`, `{{service_N_price}}`, `{{service_N_price_number}}` read the N-th entry of `knowsAbout`, `areaServed` and `hasOfferCatalog`. If that entry is missing, `null` or still a `{{placeholder}}`, the marker takes a sample value (`Service N`, `City N`, `$149`…) so a half-filled site still builds, and the build warns for every sample value that is really published, naming the marker, the reason and the files that use it. An offer with no `price` counts as empty. A sample value that nothing uses stays silent. With `CHECK_STRICT=TRUE` (the default) these warnings fail the build like the validator's, so a published site never carries them; `CHECK_STRICT=FALSE` is for phases in progress. Fix them by adding the data to `entity.json` or by removing the marker from the page or text that uses it. `build.py --strict` does the same without `build.sh`.

**From the layout:** `{{title}}`, `{{description}}`, `{{robots}}`, `{{geo}}`, `{{canonical}}`, `{{og_url}}`, `{{jsonld}}`, `{{header}}`, `{{content}}`, `{{footer}}`.
**From partials:** `{{nav_guides}}`, `{{nav_blog}}`, `{{footer_blog}}`, `{{year}}`.
**In `llms.txt`:** `{{llms_guides}}`, `{{llms_blog}}`, `{{llms_sitemap_extra}}`.
**Anything else:** any key of `texts.json`.

### 7.2 Validator rules

| Area | Errors (always fail) | Warnings (fail in strict mode) |
|---|---|---|
| Document metadata | missing `lang`, viewport, `<title>`, description or robots; non-HTTPS or wrong canonical; indexable page without canonical; `og:url` ≠ canonical; `og:image` or `og:url` not HTTPS; `og:image` file missing; 404 with a canonical or `og:url` | title outside 20–60; description outside 70–160; missing Open Graph/Twitter tags; `og:title` ≠ `<title>`; missing `og:image:alt`; unusual `lang`, `og:locale` or `twitter:card` values; viewport without `width=device-width` |
| Structure | not exactly one `h1`; empty headings; more than one `aria-current` | first heading not `h1`; skipped levels; fewer than 250 words in `<main>` (indexable) |
| Images | `<img>` without `alt` | `alt` over 125; missing `width`/`height`; `<img>` without `src` or `srcset` |
| Links | broken internal links, anchors, assets; missing trailing slash; malformed `mailto:`/`tel:`; empty `href`; internal `http://` links | external `http://`; relative links; `target="_blank"` without `noopener`/`noreferrer`; orphan pages (no contextual inbound link from another page's `<main>`) |
| Leftovers | unresolved `{{…}}` | `TODO` or `[CONFIRM` in visible text |
| Structured data | indexable page without JSON-LD; invalid JSON; wrong `@context`; duplicate or undefined `@id`; missing `ProfessionalService` or `WebSite`; `url` ≠ real URL; FAQ differs from visible FAQ; FAQPage without `mainEntity` | `name` ≠ `<title>`; non-ISO `dateModified`; malformed FAQ `Question`/`Answer` |
| Duplicates | duplicate titles/descriptions among indexable pages | — |
| Site files | missing `index.html`, `404.html`, `sitemap.xml`, `robots.txt`; invalid/duplicate/off-domain sitemap URLs; sitemap URL without a generated page; indexable page missing from sitemap or `noindex` page present; global `Disallow: /` | missing `llms.txt`; `lastmod` not ISO or ≠ `dateModified`; `robots.txt` without `Sitemap:` |

Thresholds are constants at the top of `check_site.py`. These checks do not replace browser testing, accessibility review or the search engines' own tools.

### 7.3 Verification kit

**V1 — Baseline (after every change)**
```bash
python3 -B -m unittest discover tests
SITE_URL=https://example.com ./legible/build.sh
```
Expected: `OK` from the tests and `CHECK PASSED` with no warnings.

The suite does not assume that the template's sample pages or data exist. It asks for "a page that exists" (`pick_page()`, `page_routes()` and `related_page()` in `tests/test_legible.py`) and reads the domain, city and email from `src/data/site.json`, so it loads and passes in an adapted site: pages renamed, replaced or removed, own domain, no `services/` or `pricing/`. Tests that really read the template's sample data carry `@ONLY_TEMPLATE` and are skipped there (`site_url` no longer starts with `https://YOUR-DOMAIN`). A new test follows the same rule: `TestSuiteIsIndependentOfTheSamplePages` fails if a test names a sample page or sample data (unless its line says `# template-only`), and it runs the page-editing tests against a copy of the template whose pages were renamed.

Because of this, V1 is the baseline of an adapted site too, not only of the template. If a test fails there for a reason that comes from the site's own content, the AI does not relax or skip the test: it fixes the content, or records the failure and tells the user (`AGENTS.md` section 9).

**V2 — Technical audit**
```bash
bash -n legible/build.sh                       # expect: no output
grep -nE "except( Exception)?( as \w+)?:\s*$" legible/*.py          # review each hit
grep -rnP '<a[^>]*target="_blank"(?![^>]*noopener)' src             # expect: no output
python3 - <<'PY'                               # texts.json keys that nothing uses
import json, pathlib, re
keys = json.load(open('src/data/texts.json'))
used = set()
for f in list(pathlib.Path('src').rglob('*')) + [pathlib.Path('legible/build.py')]:
    if f.is_file() and f.suffix in ('.html', '.txt', '.json', '.py') and f.name != 'texts.json':
        used |= set(re.findall(r'\{\{([a-z0-9_]+)\}\}', f.read_text(errors='ignore')))
print(sorted(k for k in keys if k not in used) or 'no unused keys')
PY
python3 legible/check_site.py --dir /nonexistent >/dev/null 2>&1; echo "exit=$?"   # expect: exit=1
```

**V3 — Template neutrality (sample content only)**
```bash
grep -rnIiE "seo|google|geo\b|chatgpt|gemini|perplexity|copilot|search console|analytics|valdemoro|business profile|directorio|directories" src
```
Expected: no output. `README.md`, `DOCUMENTATION.md` and `legible/` may mention SEO, Google, JSON-LD and AI crawlers: that is what the tool does. **`src/pages`, `src/partials`, `src/data/texts.json` and `src/layout.html` must not.** The engine features that keep their names (`geo` flag, `llms.txt`, AI-crawler entries) are listed in section 4.3.

### 7.4 Pre-launch sweep

Run it on a real project before publishing:

```bash
grep -rIniE 'Your Business|Your City|Your Region|YOUR-DOMAIN|Service [1-6]\b|City [1-4]\b|Topic [1-5]\b|Free Consultation|Your legal name|Your registered address|Your registration number|Your jurisdiction|example\.com|555|\$(49|55|99|149|229|290|299|490)\b|09:00|19:00|9am|7pm|business day|business hours|addressCountry|priceCurrency|CONFIRM|SAMPLE COPY' dist src
```

The sweep is a review aid, not a pass/fail test. Replace every hit, or justify it explicitly (for example a real price that happens to match). The sample logo and social image are replaced with the site's own assets (section 3.7). Hits for `CONFIRM` mark facts that are still awaiting confirmation. Hits for `SAMPLE COPY` mark pages whose descriptive text was written as an example in a fast start (section 6.1.1) and must be rewritten with the business's real wording or confirmed. The sweep also flags sample opening hours, response times and limits (for example "max. 3 per week"), currency and country, which are repeated across `entity.json`, pages, FAQs and `llms.txt`: review all of them at once. Keep the command in single quotes: in double quotes the shell turns `\$(99|149|290)` into `$(99|149|290)` and the price patterns match nothing.

### 7.5 Commands

| Action | Command |
|---|---|
| Tests + build + server | `python3 legible/run_all.py [--skip-tests] [--port N]` |
| Without server | `python3 legible/run_all.py --no-dev` |
| Tests only | `python3 -B -m unittest discover tests` |
| Strict build + validation | `SITE_URL=https://example.com ./legible/build.sh` |
| Unminified build | `CSS_MINIFY=FALSE ./legible/build.sh` |
| Warnings do not fail (validator and sample-value warnings of the build) | `CHECK_STRICT=FALSE ./legible/build.sh` |
| Build only | `python3 legible/build.py [--out FOLDER] [--minify true\|false] [--no-validate] [--strict]` |
| Local server (port 3001) | `python3 legible/dev.py [--port N] [--minify]` |
| Validate an existing build | `python3 legible/check_site.py --dir dist --strict --site-url https://example.com` |

`build.sh` variables: `SITE_URL` (empty counts as not set), `CSS_MINIFY` (default `TRUE`), `CHECK_STRICT` (default `TRUE`). If the output still uses the sample domain `YOUR-DOMAIN.com`, `build.sh` prints a warning but does not fail. `build.py` also reads `RENDER_GIT_BRANCH` and `RENDER_GIT_COMMIT`, which feed the report when there is no Git checkout. If the executable bit is missing (for example after unpacking an archive), run `bash legible/build.sh`.

### 7.6 Deployment

This section is a reference for people. An AI that builds a site does not deal with deployment (`AGENTS.md` section 8, rule 7).

Publish `dist/` on any static host (Cloudflare Pages, GitHub Pages, Netlify, Render, S3, Nginx).

```text
Build command:      ./legible/build.sh
Publish directory:  dist
Environment:        SITE_URL=https://your-domain.com
```

The build environment needs Python 3.8+ and `bash`. A failed validation exits non-zero, so the host will not publish it.

### 7.7 Glossary

| Term | Meaning |
|---|---|
| Marker / placeholder | `{{key}}` replaced at build time |
| Front matter | The `---` block at the top of a page (`title`, `description`…) |
| JSON-LD / `@graph` | Schema.org structured data; one per page, merging business + page nodes |
| Indexable | A page without `noindex` that is not the 404; it appears in the sitemap |
| Orphan | A page with no contextual inbound link from another page's `<main>` |
| Strict mode | Validator warnings also fail the build |
| `llms.txt` | Plain-text file with business facts for AI assistants |
| Featured action | The offer priced 0 (`/featured-action/`) |
| Locale file | `legible/locales/<language>.json`: engine-generated strings for one language |
| Briefing | The set of business facts a site is built from (section 5.2); anything not in it is not invented |
| Pre-launch sweep | The search for sample values and `[CONFIRM` markers left in a real project (section 7.4) |
| Built-in checks | The minimal SEO checks that `legible` ships: generated metadata and JSON-LD, sitemap, `robots.txt`, `llms.txt`, strict validator and pre-launch sweep (section 1.0) |
| Interactive feature | Anything that needs client-side JavaScript, a backend or an external service (calculator, booking, form backend, map). Not in the base; goes to **Later** |
| Interview | The twelve questions in three rounds in `AGENTS.md` section 4 that produce the plan; the only thing it adds to the project is `SITE_PLAN.md` |
| Fit check | The AI's check, in interview question 1, of whether the business suits legible (section 5.0) |
| URL map | The table in `SITE_PLAN.md` of every page, its URL and its purpose, proposed by the AI and confirmed by the user |
| `SITE_PLAN.md` | The phased plan for the first version, with its status; it lives in the project root and travels inside the zip |
| Phase | One step of the plan, small enough for one session of a free-plan chat; statuses `pending`, `in_progress`, `done`, `blocked`. The catalogue and its limits are in `AGENTS.md` section 5 |
| Command | The exact English phrases `legible start`, `legible continue`, `legible help`, `legible flow off` and `legible flow on` (section 6.1.1). Anything else is not a command and gets an explanation when there is no plan |
| `FLOW_OFF.lock` | A file in the project root, created by `legible flow off`, that turns the AI flows off in a working copy. Ignored by git; the test suite fails if it exists |
| `project_stage` | The field in `site.json` that marks the project as `template`, `in_progress` or `complete`; ignored by the engine, read by AIs |
| Refinement mode | What the AI does when `project_stage` is `complete` and there is no plan: no flow, only the part the user names |
| Recovery mode | What the AI does when `project_stage` is `in_progress` and `SITE_PLAN.md` is missing: audit the project and rebuild a short plan from the evidence |
| Maintenance mode | What the AI does with a `complete` plan: report the final state and work only on the part the user names |
| Final state | The closing section of `SITE_PLAN.md`: state of everything, pending facts, remaining warnings and Later |
| Later | The plan's list of requests beyond the first version |
| Engine exception | A minimal, recorded change to `legible/` made only when `src/` cannot meet the need (`AGENTS.md` section 7) |
| Fast start | `legible start` followed by inputs (a style URL, fields in one line, images): the AI asks only for the missing name or theme and writes the plan with no confirmation round (section 6.1.1) |
| Sample copy | Short descriptive text the AI writes as an example in a fast start; the page carries `<!-- SAMPLE COPY -->` and the pre-launch sweep finds it. Facts are never sample copy |
| Engine mode | The session in which the AI may change `legible/` or `tests/` after the user asks and confirms. It has no file or field: the AI announces `Engine mode on` and `Engine mode off` (section 5.0, control surface) |
