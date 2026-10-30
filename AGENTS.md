# AGENTS.md

`legible` is a lightweight static-site generator for local service businesses. It uses only the Python standard library and ships no client-side JavaScript. This file is the entry point for AI agents and the source of truth for procedures, numbers, limits and commands. The reasoning behind them and the reference tables are in [`DOCUMENTATION.md`](DOCUMENTATION.md), section 5.0 (the methodology).

**At a glance**
- **Your job:** adapt the sample base into a website for one business, changing only `src/`.
- **Not your job:** the engine (`legible/`), the tests (`tests/`), the architecture and deployment.
- **First step:** check whether `FLOW_OFF.lock` exists in the project root (if it does, the flows are off), then look for `SITE_PLAN.md`. Section 1 tells you what to do next.
- **Commands:** the user drives the process with the exact commands below. Anything else gets an explanation first, never the interview.
- **Always:** keep missing facts as `[CONFIRM …]` markers and report only checks you really ran (sections 8 and 9).
- **If a case is not covered:** stop and ask one question (end of section 8).

**Commands** (always in English, whatever language the user writes in; details in sections 1 and 4)

| Command | What it does | It asks |
|---|---|---|
| `legible start` | Full interview (twelve questions, three rounds) | Everything |
| `legible start <url>` | Style from a website (palette, structure, proportions) | The business name, and whether to keep the same theme |
| `legible start name: …; activity: …` | Your data in one line, fields separated by `;`. The design is proposed from the theme | Nothing |
| `legible start <url> name: …; activity: …` | Style from a website plus your data | Nothing |
| `legible start` + attached images | An image of a design (style) and/or an image of the business data (card, flyer, menu, listing screenshot). `style: design.png; data: card.jpg` says which is which | Nothing if there are data; otherwise the name and the theme |
| `legible continue` | Continues the plan. With a plan, loose phrases in any language also work (`continúa`, `sigue`, `next phase`…) | Nothing |
| `legible help` | A simple explanation of what `legible` is, plus this list | Nothing |
| `legible flow off` / `legible flow on` | Turns the flows off or on by creating or deleting `FLOW_OFF.lock` (for the maintainer) | Nothing |

**Fields** of the one-line data (any order, all optional except name and theme): `name`, `activity`, `city`, `phone`, `email`, `address`, `hours`, `services`, `style` (a URL, an image file name or a short description), `data` (an image file name) and `site` (the domain). The Spanish names work too: `nombre`, `actividad`, `ciudad`, `tel`, `dir`, `horario`, `servicios`, `estilo`, `datos`, `web`. Only the first `:` of each field splits key and value; a value must not contain `;`.

`run legible`, `ejecuta legible`, `start site` and similar phrases are **not** commands. They get the explanation. "Run" and "ejecuta" never mean "run the tests, the build or the server" unless the user asks for those explicitly.

<!-- LESSONS-LOG:START
TEMPORARY (testing phase). To remove this feature, delete everything from this comment down to the closing comment of this block. Nothing else in the project refers to it. -->
## Temporary rule: lessons log

While the method is being tested, keep a log of what could be improved, for the user to analyze later. This rule **overrides** any other instruction that says to change only `src/`, to add only `SITE_PLAN.md`, or to change nothing (including read-only reviews and audits). It is the only exception.

- **File:** `LECCIONES_APRENDIDAS.md` in the root of the project. If it exists in the zip, append to it: do not rewrite or reorder it, and do not read it in full, just add your entry at the end. If it does not exist, create it with a one-line title. It is not `SITE_PLAN.md`: the plan size checks do not apply to it.
- **When:** once per session, before your final reply, in every mode. If nothing is worth recording, add one line: `<date> · <mode and phase> · no observations`.
- **What to record:** instructions that were ambiguous, contradictory or missing; things you had to guess; steps that wasted effort or context (for example a file read that was not needed); commands or checks that failed or were hard to run; places where the plan, the phases or their size did not fit the session; corrections the user had to make; and ideas to improve the method or the architecture.
- **Format:** one entry per observation, at most five per session (keep the most important), at most ten lines each, in the language the user writes in:

```
### <YYYY-MM-DD> · <mode and phase>
- Type: process | architecture | documentation | tests | other
- Where: file and section (for example `AGENTS.md` section 5)
- What happened: facts only, with the real command output or the exact instruction involved
- Proposal: the smallest change that would help
- Impact: low | medium | high
```

- **Record, do not act.** Do not change the engine, the tests, `AGENTS.md` or `DOCUMENTATION.md` because of a lesson, and do not start working on a proposal. The log is for analysis; the decision to change anything is the user's.
- **Facts only.** Record what actually happened, never what you assume. Do not put business data in the log (names, phones, addresses, prices): refer to the file and the section instead.
- **Delivery.** The file travels inside the zip you return, like the plan. If you cannot create files, put the entry in your final message.
<!-- LESSONS-LOG:END -->

## 1. First step: look for the plan, then read the request

**Always start by checking for `FLOW_OFF.lock`, then for `SITE_PLAN.md`, in the root of the project.** If only some `.md` files are attached and not the zip, ask for the zip before doing anything else.

**Flows switch.** `FLOW_OFF.lock` exists only on a maintainer's working copy. It is never part of a distributed zip.

- **If it exists, the flows are off.** Do not run the interview, execution, recovery, refinement or maintenance modes, do not explain `legible` unasked and do not create `SITE_PLAN.md`. Work as on any normal repository: do what the user asks in any file, including `legible/` and `tests/`, without the engine-mode confirmation. Sections 8 and 9 still apply: report only checks you really ran and keep the tests and the strict validator green. Record any engine or test change in your final message and in `CHANGELOG.md` (there is no plan to hold Engine notes). Open your first reply with one line saying the flows are off (`FLOW_OFF.lock`), in the user's language. If the user says `legible start` or `legible continue` while the lock exists, answer that the flows are off and that `legible flow on` comes first. If you return a zip that still contains the lock, remind the user to run `legible flow on` before distributing it.
- **`legible flow off`:** create `FLOW_OFF.lock` in the root with one line (`flows off since <date>`), confirm in one line, and change nothing else.
- **`legible flow on`:** delete `FLOW_OFF.lock`, confirm in one line, and start no flow by yourself.
- Create or delete the lock only when the user types one of these two exact commands, never on your own initiative. If you cannot create or delete files, say so.

If the lock does not exist, continue with the plan and the table below.

If there is no plan, read `project_stage` in `src/data/site.json` (`template`, `in_progress` or `complete`). If the field is missing (an older zip), fall back to the sample values. The site is still the base only when `site_name` is `Your Business` and `site_url` is `https://YOUR-DOMAIN.com`. If either has been replaced, treat the site as `in_progress`.

Then take the first row of this table that matches:

| Plan | `project_stage` | The user says | Go to | First words |
|---|---|---|---|---|
| Any | any | `legible help` | Explain `legible` (below) | Add the state of the plan. Change nothing |
| Exists, phases left | any | `legible continue`, a continue phrase, `legible start`, or nothing specific | **Execution mode** (section 6) | Do not explain `legible` first |
| Exists, status `complete` | any | `legible continue`, a continue phrase, `legible start`, or nothing specific | **Maintenance mode** (section 6) | Report the final state in a few lines and ask which part to work on |
| Exists | any | clearly something else: a question, an engine change, a deployment, something outside the base | The requests table below | Mention the state of the plan |
| Missing | `in_progress` | anything | **Recovery mode** (section 6) | Say you found a site in progress with no plan. If the request was unrelated, handle it with the requests table below and mention that the plan is missing |
| Missing | `complete` | anything, including `legible start` or a continue phrase | **Refinement mode** (section 6) | One line: the site is marked complete and needs no plan. Ask which part to work on. No interview, no recovery, no new plan |
| Missing | `template` | `legible start`, with or without inputs (a URL, fields, images) | **Interview mode** (section 4: full interview, or fast start when there are inputs) | Do not explain `legible` first |
| Missing | `template` | a continue phrase | One line: there is no plan yet, and `legible start` begins one | Do not interview and do not explain at length |
| Missing | `template` | anything else (including `run legible`, `ejecuta legible`, `start site`) | Explain `legible` (below), then the requests table | Do not start working. The one exception is an explicit request to run the tests, the build or the server: do it, report the real results and add one line pointing to `legible help` |

**Continue phrases.** The official command is `legible continue`. When a plan exists, loose phrases in any language also continue it, because the plan itself is the control. They include `continue`, `keep going`, `resume`, `next phase`, `carry on with the plan`, `continúa`, `continúa con el plan`, `sigue`, `siguiente fase`, or the equivalent in the user's language.

**The start command** is exactly `legible start`, optionally followed by inputs (section 4). It has no aliases and no translations: `start site`, `new site`, `run legible`, `empezar sitio` or `ejecutar legible` are not start commands and get the explanation. When a plan exists, `legible start` behaves like `legible continue`.

**Explaining `legible`** (the base is untouched and the request is not `legible start`, or the user typed `legible help`). Keep it simple: at most six short lines, plain words and no jargon, in the user's language.

- What it is: a tool that turns a few text files into a fast, static website for one local business (a clinic, a workshop, a shop) and checks it.
- What you get: the site's pages with titles, structured data, a sitemap and the files that search engines and AIs read, plus automatic checks. It promises no rankings and no traffic.
- What it fits: one business, one language. No online shop, no booking or forms with a backend, no scripts and no external widgets.
- How it works: you say `legible start` (optionally with a style website, your data or images), the AI writes a short plan inside your zip and executes it one phase per session.
- Deployment is not part of it.

Then show the commands table from the top of this file, copied literally, and say whether a `SITE_PLAN.md` exists and in what state. For `legible help` stop there; for any other request continue below.

Then answer the request as follows (the same table applies when a plan exists and the request is not to continue it):

| The user asks for | You do |
|---|---|
| A question about `legible` or the project | Answer it, mention `legible start`, and say whether a `SITE_PLAN.md` exists and what state it is in |
| A site for a business that fits only partly (large catalogue, bookings, several languages at once, several locations with their own pages) | Say exactly what does not fit, what would go to **Later** and what the options are; continue only after the user confirms |
| Something `legible` does not do (online store, CMS, user accounts, client-side JavaScript, external widgets, fonts, analytics or trackers, another framework) | Explain that it is outside the base and why (`DOCUMENTATION.md` section 1.1), offer the options (record it in **Later**, an explicit engine exception under section 7, or another tool), and wait for the decision |
| To improve, refactor or change the engine, the tests or the architecture | Explain that the engine is deliberately fixed, ask which need it would solve, check whether `src/` can meet it, and enter engine mode only if the user confirms |
| Deployment, hosting, DNS, CI or publishing | Say that it is outside this process and do not touch it. The human reference is `DOCUMENTATION.md` section 7.6 |
| A review, audit or explanation of the code or the site | Do it read-only and change nothing |

## 2. Your job: build a site with `legible`

The zip is the **generic base**. Your job is to adapt it into a website for one business, changing **only `src/`**.

Your job is **not** to improve, refactor, optimize or "fix" the engine (`legible/`), the tests (`tests/`) or the architecture. Do not open them for editing on your own initiative, even if you see something you would do differently. The only exception is section 7. Deployment is not your job either (section 8, rule 7).

## 3. Modes

The first five modes are chosen by the table in section 1. The flows-off mode is chosen by the lock file (section 1) and takes precedence over all of them.

| Mode | When | Where |
|---|---|---|
| **Interview** | No plan, base untouched, `legible start`: the full interview, or fast start when the message has inputs | Section 4 |
| **Execution** | A plan with phases not `done`, and `legible continue`, a continue phrase, `legible start` or no specific request | Section 6 |
| **Recovery** | No plan and `project_stage` is `in_progress`: rebuild the plan from the project state, then continue | Section 6 |
| **Refinement** | No plan and `project_stage` is `complete`: no plan and no flow; work on the part the user names | Section 6 |
| **Maintenance** | A plan whose status is `complete`, and `legible continue`, a continue phrase, `legible start` or no specific request: report the final state and work only on the part the user names | Section 6 |
| **Engine mode** | The user explicitly says "engine mode" or asks to change `legible/` or `tests/` (with or without a plan; with `FLOW_OFF.lock` no confirmation is needed). Read `DOCUMENTATION.md` sections 0.1 and 2 first; keep the change small, update the tests and keep the baseline green | Section 7 |
| **One-session mode** | The user explicitly asks to build the whole site in one session without a plan (`DOCUMENTATION.md` section 6.3). Skip the interview and the plan, follow stages S0 to S6 in `DOCUMENTATION.md` section 5.4, and obey sections 8 and 9 of this file | `DOCUMENTATION.md` |

## 4. Interview mode

**Goal:** collect just enough to write a short plan for the base of the site. The only thing you add to the project is `SITE_PLAN.md`; you change no other file.

**First check the message for inputs.** If `legible start` came with a URL, `key: value` fields or attached images, follow **Fast start** at the end of this section and skip the twelve questions. With no inputs, run the full interview below.

Open with one line, in the user's language: you will ask twelve short questions in three rounds, and the plan will come back inside their zip.

- Ask the **minimum**: only what you cannot derive. Ask in **three short rounds**, not all at once. Skip anything the user has already told you. Speak the user's language.
- **Propose, do not ask**, what you can derive: page list, URLs, menu, design direction and phases. The user confirms or corrects.
- Anything the user does not know becomes a visible `[CONFIRM …]` marker in the plan. **Never invent** hours, reviews, awards, certifications, years in business or figures.
- Anything the user wants beyond the base goes into the plan's **Later** list, not into the phases.

**Round 1: the site**
1. Business name, one line on what it does, and what kind of business it is. This is where you check the fit (section 1). If it fits only partly, say so now.
2. Site language (`en`, `es` or other; one language per site) and tone (formal or friendly; tú or usted for Spanish).
3. Domain (HTTPS), or "not yet". Is there an existing site whose URLs must be kept? `legible` generates no redirects; note any such URLs in the plan and do nothing more about them.
4. City, region, country, and whether customers visit a street address.

**Round 2: contact and offer**
5. Email, phone in E.164 format, and whether the phone is confirmed for WhatsApp.
6. Service area: up to 4 cities with shortcuts; others as a plain list.
7. Services, grouped into at most 6 categories. You propose one page per real service and its URL.
8. Priced offers (at most 5) and currency, and the featured offer, priced 0: name, what it includes and excludes.

**Round 3: design and gaps**
9. Design: logo, favicon and a 1200×630 social image if available (otherwise placeholders), brand colours, or "keep the base look". A reference site is welcome. Say plainly what the base allows: one stylesheet with design tokens, system fonts, no external resources, no client-side JavaScript.
10. Opening hours, or "no hours". Legal data (legal name, tax or registration ID, registered address, governing law), or "pending".
11. Anything wanted **later**: blog, guides, extra pages, interactive features (calculators, booking, forms with a backend, maps).
12. Anything unknown that must not be invented.

**Built-in checks are not a question.** The SEO checks that `legible` provides (validator, JSON-LD, sitemap, `robots.txt`, `llms.txt`, pre-launch sweep) are part of the base and are always used. Do not ask the user whether they want them and do not list them as a request.

**Interactive features.** The base has no client-side JavaScript and no external resources (`DOCUMENTATION.md` section 1.1). If the user asks for interactive features, record them under **Later**, unless the user says they are essential to the base. In that case, list them in the plan as an **exception** that needs an explicit decision (section 7).

**Propose and confirm.** After round 3, show in a few lines what you understood and what you propose: the page list with its URLs (lowercase ASCII, hyphens, localized for a non-English site, one page per real service, no near-duplicate pages per town or keyword), the design direction, and the phases. Ask the user to confirm or correct it. Then deliver the plan (section 5).

### Fast start

Used when `legible start` comes with inputs. The inputs may be combined freely:

- **A URL** is a style reference (the same as `style: <url>`).
- **Fields** `key: value` separated by `;` (keys in the commands table at the top). Free text with the same facts is also accepted.
- **Attached images**, at most two of each kind. `style: <file>` and `data: <file>` say which is which. When they do not, decide by content: a screenshot or mock-up of a site is style; a business card, flyer, menu or listing screenshot is data. If it is ambiguous, ask one question.
- If typed fields disagree with an image or a website, the typed fields win.

**What to ask**, and nothing more:

| Inputs | Ask |
|---|---|
| A style source only (URL, image or `style:` description), no data of any kind | One message with two questions: the business name, and whether to keep the same theme as the reference (yes or no; if no, what the business does) |
| Any data (typed or read from an image), with or without a style source | Nothing, except the name or the theme if either is missing |

The **minimum to start** is the business name and the theme. The theme comes from `activity`, from the style reference or from a data image. Everything else is derived or left as `[CONFIRM …]`, and you do not ask about it: domain (`site_url` stays the sample, with a `[CONFIRM …]` row), address, hours, legal data, email, service area (the city, otherwise `[CONFIRM …]`), language (the user's), tone (friendly), services (propose three, as sample copy) and the name of the featured offer (a sample, with a `[CONFIRM …]` row).

**Facts and copy.** Never invent facts: phone, email, address, hours, prices, years in business, awards, certifications, reviews, figures or legal data. They come from the user or stay `[CONFIRM …]`. You may write short descriptive copy (headlines, introductions, service blurbs, calls to action) on the theme: generic, with no claim that could be checked. Put `<!-- SAMPLE COPY -->` at the top of the body of every page that carries it, and list "sample copy" in **Pending confirmation**.

**Reading the style.** Use what you can: fetch the page, look at the images. Take only the palette, the feel of the typography (mapped to system fonts), the order of the sections, the proportions and the shape of buttons and cards. Never copy the reference's name, logo, images or text, and never build a page that could be mistaken for it. The base limits apply (one stylesheet, system fonts, no external resources, no client-side JavaScript), so do not try to imitate fonts, carousels, animations or menus that need them. Record in the briefing what you could really read ("text only, palette estimated", "from a screenshot"). If you cannot read the URL or see the image, say so in one line and ask for the other source (a screenshot or a short `style:` description). Do not invent a style.

**Data from an image.** Transcribe the facts you can read and use them. Record every phone, email, address and opening hour read from an image in **Pending confirmation** as "read from image, verify". If you cannot read an image, say so and ask for the data as text.

**Deliver.** Write the plan (section 5) with no confirmation round; the standard catalogue and size limits apply. Say in a few lines what you read, what is sample copy and what is pending, and tell the user to correct it by replying or when they say `legible continue`.

## 5. The plan: `SITE_PLAN.md`

The plan covers the **base of the site only**: the structure and the basics. It is a short map, not a task list. It has at most **ten phases** (twelve when the business has more than three service pages), each small enough to execute in one session of a free-plan chat (see the session budget below).

**Size limits.** A later session reads `SITE_PLAN.md` in full, so keep it small:
- The whole file fits in about 120 lines. If it does not, cut it; do not compress it.
- The briefing is one short line per item, not paragraphs.
- Each phase has **at most two lines** of detail: what to read (so a session never loads the whole documentation), what to touch with the expected result, and the verification command.
- **Session budget.** One phase touches at most about **three pages or three large files**, and never needs to read the whole stylesheet at once. Prefer a phase that finishes with room to spare over one that fills the session: a half-done phase costs more than an extra phase.
- No per-page outlines, no copy, no keyword lists, no checklists of small tasks. What each page says is decided in the content phases, with the data already in the plan.
- The URL map has one row per page, with a purpose of a few words.
- Each **Later** item is one line.
- Detail is decided when a phase runs, not before.
- If a phase seems to need more than one session, split it, up to the limit of ten phases. If it still does not fit, move part of it to **Later**.
- A site with more than three service pages may add one extra phase for each further three, up to twelve phases in total.
- A phase the site does not need (for example the brand tokens when the user keeps the base look) is not removed. It stays in the table as `done` with "not needed" and its reason in the Verification column, so the numbering is stable and its slot can be used to split a heavy phase.
- The execution log is at most three lines per session. When the log gets long, summarize the old entries into one line.

**Check the plan before you deliver it, and after every update.** The limits above are measured, not guessed:

```bash
wc -l SITE_PLAN.md                     # expect 120 or fewer; if more, summarize the log and cut, do not compress
grep -cE '^[|] [0-9]+ [|]' SITE_PLAN.md   # phases in the table: expect 10 or fewer (12 at most, see above)
```

**Default `Read:` lines.** Each phase reads only these, so a session never loads the whole documentation (section numbers are those of `DOCUMENTATION.md`). Use them as they are in the plan, and change them only when the catalogue changes. On a site that is not in English, add section 4.2 to phases 1, 2 and 7 to 10.

| Phase | Read |
|---|---|
| 1 Data | Sections 3.1, 3.2 and 7.1; the three data files |
| 2 Structure and URLs | Sections 3.3 and 3.4, and 5.3 rules 4 and 7; the page tree, `header.html`, `sitemap_base_order` |
| 3 Brand tokens | Lines 1 to 62 of `site.css` (the tokens block) and nothing else |
| 4 Component styles | `site.css` from line 63, one numbered section at a time, only those needed; 5.3 rule 12 |
| 5 Layout and partials | 5.3 rules 8 and 9; `layout.html`, `header.html`, `footer.html` |
| 6 Brand assets | Section 3.7; the icon and image lines in the head of `layout.html` |
| 7, 8, 9 Content | 5.3 rules 6 and 13 (rule 7 and `services/sample-service/` for phase 8); the briefing in the plan; only the pages of that phase |
| 10 Legal and close | 5.3 rule 10, then sections 7.2 and 7.4 |

**Where the plan goes.**
- Create `SITE_PLAN.md` in the **root of the project** and **return the complete project as a zip with the plan inside it**, under the same file name the user attached (normally `legible.zip`). Exclude `dist/`, `.dev-dist/`, `__pycache__/` and `.git/`.
- Say plainly that the plan is already inside the zip and that the user does not need to add it anywhere. The zip is what carries the project between sessions: when it is attached to a new session with the plan inside, the work continues from there.
- You may also give the plan as a separate file or as text, but only as a convenience. The copy inside the zip is the one that counts.
- If you cannot create a zip, output `SITE_PLAN.md` in full and tell the user to place it in the root of the project.

Write headings, table columns and status values in English. Free text may use the user's language. Use this structure:

````markdown
# SITE PLAN: <business name>

> Build this site with `legible`. Change only `src/`. Do not improve or refactor the engine, the tests or the architecture. Do not deal with deployment. Read AGENTS.md first. Execute one phase per session.

**Status:** not started | in progress | complete · **Language:** <en|es|…> · **Domain:** <https://…>

## Briefing
- **Site:** business, one-line description, kind of business, fit notes, language, tone.
- **Contact and place:** email, phone, WhatsApp confirmed or not, city, region, country, street address.
- **Offer:** service area, service categories, priced offers, currency, featured offer.
- **Design:** assets available, colours, reference site, or "base look".
- **Sources:** style reference and how it was really read; data source; sample copy yes or no (fast start only).
- **Gaps:** hours, legal data, existing URLs to keep, everything unknown as [CONFIRM …].

## URL map
| Page | URL | Purpose |
|---|---|---|

## Phases
| # | Phase | Status | Date | Verification |
|---|---|---|---|---|
| 1 | Data: `site.json`, `entity.json`, `texts.json` | pending | | |
| 2 | Structure and URLs: pages, menu, `sitemap_base_order`, internal links | pending | | |
| 3 | Brand tokens: the `:root` block of `site.css` (colours, type, spacing) | pending | | |
| 4 | Component styles: the rest of `site.css`, only what the tokens do not solve | pending | | |
| 5 | Layout and partials: `layout.html`, `header.html`, `footer.html` | pending | | |
| 6 | Brand assets: `logo.svg`, `favicon.svg`, and the PNG and ICO files if provided | pending | | |
| 7 | Content: home, services index and pricing | pending | | |
| 8 | Content: service pages (at most three per phase) | pending | | |
| 9 | Content: featured action, about and contact | pending | | |
| 10 | Legal and close: legal pages, 404, pre-launch sweep, full strict baseline | pending | | |

### Phase details
<for each phase, at most two lines: `Read:` the documentation sections and files it needs, and nothing else · `Touch:` the files and the expected result · `Verify:` the command>

## Pending confirmation
| Fact | Where it appears | Status |
|---|---|---|

## Engine notes
<empty unless an exception under AGENTS.md section 7 was used>

## Execution log
<one short entry per session, at most three lines: date, phase, what changed and the decisions taken, real command results>

## Later
<requests beyond the base>

## Final state
<empty until the plan is complete; see AGENTS.md section 6>
````

Allowed phase statuses: `pending`, `in_progress`, `done`, `blocked` (with the reason).

**Adapt the catalogue to the site.** The ten rows above are the default catalogue, sized for one session each. When the plan is written:
- If the user keeps the base look (interview question 9), mark phases 3 and 4 `done` with "not needed: base look kept". Mark phase 5 the same way only when `layout.html` and the partials need no change beyond what phase 2 already did.
- With a style source (fast start), phases 3 to 5 are needed: the look comes from the reference. Do not mark them "not needed".
- Phase 6 is never skipped silently. The AI can write SVG (`logo.svg`, `favicon.svg`) but should not fake binary images: `og-image.png` (1200×630), `apple-touch-icon.png` and `favicon.ico` stay as the sample files, with a row in **Pending confirmation**, until the user supplies them. The SVG files are replaced, or listed as pending if the user has no logo.
- Phase 8 repeats for each further three service pages (see the size limits), and its pages are named in the phase details.
- Phase 10 combines the three legal pages, the 404 page and the close. If the legal data is mostly `[CONFIRM …]` this is light; if it is not, split it into legal (before) and close (after), using a slot freed by a skipped phase.

## 6. Execution, completion, maintenance, recovery and refinement

**Execution mode**

1. Read `SITE_PLAN.md`. Take the first phase that is not `done`. Read only what that phase's `Read:` line lists; do not load `DOCUMENTATION.md` in full. Before you start, measure the work: `wc -c` on the files the phase will read or change. If the total is more than about 50000 bytes, split the phase first (section 5, size limits). Execute **only that phase**, unless the user asks for more.
2. Work only in `src/`. Respect anything the user changed by hand since the last session; note it in the log instead of reverting it. If a new instruction from the user contradicts the plan, say so and ask which one wins. If `project_stage` disagrees with the plan, trust the plan, fix the field and note it in the log.
3. Verify the phase (section 9) and run the baseline when the phase says so. Do not mark a phase `done` without a real check.
4. Update `SITE_PLAN.md`: phase status and date, verification result, the execution log with the decisions taken, the pending-confirmation table, the Later list and the overall status (`in progress`).
   - Run the plan checks of section 5 on the updated file and shrink it if it is over a limit.
   - When phase 1 starts, set `project_stage` in `src/data/site.json` to `in_progress`.
   - If the phase failed or stopped halfway, set `blocked` or `in_progress` and write where it stopped.
5. **Return the complete project as a zip** (same name, same exclusions as in section 5) with your changes and the updated `SITE_PLAN.md` inside it. If you cannot create files, output every changed file in full, including `SITE_PLAN.md`.
6. Finish with two or three lines: what was done and which phase is next.

**Completion.** When the last phase is `done`:

1. Set the overall status to `complete`, set `project_stage` in `src/data/site.json` to `complete`, and fill **Final state** (at most 20 lines): a short table of area, state and notes (pages, data, design, legal, validator result), the facts still pending, the warnings that remain and why, and the Later list.
2. Shrink the phase details and the execution log to one line each, so the file stays small.
3. Tell the user, in a few lines, that the plan is finished, that the state of everything is recorded in `SITE_PLAN.md` inside the zip, and that they can attach the zip at any time and ask for one part to be fixed or extended. Say nothing about deployment.

**Maintenance mode** (the plan is `complete`). Report the final state in a few lines and ask which part the user wants to work on. Work only on that part, only in `src/`, and verify it (section 9). Then record it in the plan: one line in the execution log, and an update to the pending table, **Final state** and **Later** if they changed. Return the zip as in section 5. Do not reopen finished phases or start new ones on your own initiative.

**Refinement mode** (`project_stage` is `complete` and there is no `SITE_PLAN.md`). The site is finished and is now refined part by part. No plan is needed, so do not create one, do not interview and do not offer recovery.
1. Ask which part the user wants to work on, unless they already said.
2. Work only on that part, only in `src/`, under the rules of section 8, and verify it (section 9).
3. Finish with one or two lines saying what changed and the real result of the check.
4. Only if the user explicitly asks to redo the site from zero: warn that the interview and the phases would rewrite what exists, and, once the user confirms, set `project_stage` to `template` and start interview mode.

**Recovery mode** (`project_stage` is `in_progress` but `SITE_PLAN.md` is missing). The state of the project is the evidence; rebuild the plan from it.
1. Tell the user what you found: a site in progress with no plan. Offer two options and recommend the first: **rebuild the plan from the current state** (read-only audit, then a short plan), or **start the interview from zero** (warn that the phases would then rewrite existing data and content). If the user only wants to work on one part, recommend rebuilding the plan first so the work is recorded.
2. Audit without changing anything: read `src/data/*.json`, the tree of `src/pages/`, `layout.html`, `partials/`, the tokens in `site.css` and `src/static/`; run the baseline (section 9) and the pre-launch sweep (`DOCUMENTATION.md` section 7.4).
3. Write `SITE_PLAN.md` from the evidence, within the size limits of section 5: the briefing from the data files, the URL map from the pages that exist, and the pending table from the `[CONFIRM` and sweep hits.
   - Mark a phase `done` only when the evidence supports it: data with no sample values; pages and menu consistent with `sitemap_base_order`; design tokens and assets replaced; every page free of sample content and passing the validator; legal pages with no sample values and a clean sweep.
   - Otherwise mark it `pending` or `in_progress` and say what is missing.
   - Never guess a fact that is not in the files: it goes to the pending table.
4. Ask at most three questions, only about what the files cannot tell (for example what was meant for **Later**). Show the reconstructed plan and ask the user to confirm it.
5. Return the zip with `SITE_PLAN.md` inside (section 5), with one log line saying the plan was reconstructed from the project state on that date. Set `project_stage` to match: `complete` and a filled **Final state** if every phase is `done`, otherwise `in_progress`, and the next session continues with the first phase that is not `done`.

## 7. The engine exception

The engine adapts only when there is no other way. Engine mode has no file marker: it exists for the session in which the user asks for it, so make it visible. When you enter, say in one line `Engine mode on: <the change>`. When you finish, end your final message with `Engine mode off` and the record of step 4. Before touching `legible/` or `tests/`:

1. Confirm that the need cannot be met from `src/`.
2. Make the smallest possible change, with no new dependencies and no client-side JavaScript.
3. Keep the tests and the strict validator green. Never weaken a test or a validator rule.
4. Record it in the plan under **Engine notes** (what and why) and in your final message. Never change the engine silently.

If the change is large or would break the rules in section 8, stop and ask the user.

With `FLOW_OFF.lock` present (section 1) the maintainer is working on the project itself: step 1 and the stop-and-ask line do not apply, steps 2 and 3 still do, and the record of step 4 goes in the final message and in `CHANGELOG.md`, since there is no plan.

## 8. Rules that never bend

1. No new dependencies, frameworks, client-side JavaScript or external resources.
2. Never invent business facts. Missing data stays as a visible `[CONFIRM …]` marker, or you ask. The only invented text allowed is short descriptive sample copy in a fast start (section 4), marked `<!-- SAMPLE COPY -->`.
3. Never weaken tests or validator rules to get a green result; fix the content instead.
4. Every page must pass the strict validator (rules in `DOCUMENTATION.md` section 7.2).
5. Replace every sample value and every `SAMPLE COPY` page, and run the pre-launch sweep (`DOCUMENTATION.md` section 7.4) before the plan is closed.
6. Do not run Git commands (commit, tag, push) unless the user asks.
7. Do not deal with deployment: no hosting, DNS, CI, publishing or host-level redirects. It is outside this process. If asked, say so.

**If a case is not covered**, or two instructions seem to conflict: stop, say in one or two lines what is missing or contradictory, offer the most conservative reading, and ask one question. Do not improvise changes outside `src/` to get unblocked.

## 9. Verify: run it, never assume

```bash
python3 -B -m unittest discover tests
SITE_URL=https://example.com ./legible/build.sh
```

Expect `OK` from the tests and `CHECK PASSED` from the validator. Report the real output and inspect `dist/`, not only the sources.

- **Every phase except the last:** the strict build may fail on `[CONFIRM` markers, pages not yet adapted and sample values that `entity.json` does not yet replace (for example `Service 2` or `City 3` while it has fewer offers or cities than the pages use). Errors must be fixed. Warnings that come only from facts still pending may be reviewed with `CHECK_STRICT=FALSE ./legible/build.sh`; list each one in the plan as expected, with its reason.
- **Last phase (close):** run the strict build with no override. The plan is not `complete` until it passes, or until every remaining warning is a pending fact listed in the plan and the user has been told.
- **If you cannot run commands** (a chat without a shell), say so plainly, do not claim that anything passed, and list the exact commands the user must run.

## 10. Map

- `SITE_PLAN.md` (project root): the short plan, its status and, once finished, the final state. Present in execution and maintenance mode.
- `src/pages/`: one folder per page. `src/data/*.json`: business facts and texts. `src/layout.html` and `src/partials/`: shared shell. `src/css/site.css`: design tokens and styles.
- `legible/`: build, validator, dev server. `legible/locales/`: engine strings per language. Do not edit; to reword them for a site use `generated_content.locale_overrides` in `src/data/site.json` (`DOCUMENTATION.md` section 2.1).
- `tests/`: regression suite. Do not edit.
- `DOCUMENTATION.md`: section 5.0 (methodology), 3 (content model), 4.2 (other languages), 5 (guide for AIs), 7 (markers, validator, commands). It explains and references; if it ever differs from this file on a procedure, a number, a limit or a command, follow this file.
