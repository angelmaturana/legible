# AGENTS.md

`legible` is a lightweight static-site generator for local service businesses. It uses only the Python standard library and ships no client-side JavaScript. This file is the entry point for AI agents; the full contract and the reasoning behind it are in [`DOCUMENTATION.md`](DOCUMENTATION.md), section 5.0 (the methodology).

## 1. First step: look for the plan, then read the request

**Always start by looking for `SITE_PLAN.md` in the root of the project.** If only some `.md` files are attached and not the zip, ask for the zip before doing anything else.

**There is a `SITE_PLAN.md`.** The default is to **continue the plan**: go to execution mode (section 6), or to maintenance mode if the plan is complete (section 6). Do this when the user says nothing specific, or says anything that means "continue", such as `continue`, `keep going`, `resume`, `next phase`, `carry on with the plan`, `continúa`, `continúa con el plan`, `sigue`, `siguiente fase`, or the equivalent in their language, or any start command. Do not explain `legible` first. Only when the user clearly asks for something else (a question, an engine change, a deployment, something outside the base) handle that request as in the table below, and mention the state of the plan.

**There is no `SITE_PLAN.md`.** First check whether the site is still the sample base or has already been adapted, by reading `project_stage` in `src/data/site.json`. If the field is missing (an older zip), fall back to the sample values: the site is still the base only when `site_name` is `Your Business` and `site_url` is `https://YOUR-DOMAIN.com`; if it has been adapted, treat it as `in_progress`.
- **`project_stage` is `in_progress` (no plan).** The site was being built and the plan was lost or removed. Do not start the interview blindly: it would plan from zero over work that already exists. Say what you found and go to **recovery mode** (section 6), whatever the user asked. If the user asked for something unrelated (a question, an engine change), handle it as in the table below and mention that the plan is missing.
- **`project_stage` is `complete` (no plan).** The site is already built and in detailed work. Do **not** run the flow: no interview, no recovery, no continuing, no new plan. Go to **refinement mode** (section 6). This holds for a start command and for a continue phrase too: say in one line that the site is marked complete and needs no plan, and ask which part the user wants to work on.
- **Start command, sample base.** The user says `start site`, `new site` or `run legible`, or the equivalent in their language (for example `empezar sitio`, `nuevo sitio`, `ejecutar legible`). Go to **interview mode** (section 4), with no explanation of `legible` first.
- **Anything else, sample base.** Do not start working. First explain in a few lines, in the user's language:

  - What `legible` is: a generator that turns `src/` (HTML templates plus three JSON data files) into a static website in `dist/`, then validates it in strict mode.
  - What it already includes for SEO: minimal built-in checks. Every build generates page metadata, Schema.org JSON-LD, `sitemap.xml`, `robots.txt` and `llms.txt`, and a strict validator checks the result (metadata, headings, links, structured data, sitemap). A pre-launch sweep finds leftover sample values. It does **not** include analytics, Search Console, rank tracking or interactive features, and it promises no rankings or traffic.
  - What it fits: one local service business per site, one language per site, no client-side JavaScript, no external resources, no CMS, no catalogue or online store.
  - How it is used: the user says `start site`; you interview them and put a short plan (`SITE_PLAN.md`) inside their zip; each later session executes one phase and updates that plan. You adapt `src/`; you do not redesign the engine. Deployment is not part of this process.

Then answer the request as follows (the same table applies when a plan exists and the request is not to continue it):

| The user asks for | You do |
|---|---|
| A question about `legible` or the project | Answer it, mention the start command, and say whether a `SITE_PLAN.md` exists and what state it is in |
| A site for a business that fits only partly (large catalogue, bookings, several languages at once, several locations with their own pages) | Say exactly what does not fit, what would go to **Later** and what the options are; continue only after the user confirms |
| Something `legible` does not do (online store, CMS, user accounts, client-side JavaScript, external widgets, fonts, analytics or trackers, another framework) | Explain that it is outside the base and why (`DOCUMENTATION.md` section 1.1), offer the options (record it in **Later**, an explicit engine exception under section 7, or another tool), and wait for the decision |
| To improve, refactor or change the engine, the tests or the architecture | Explain that the engine is deliberately fixed, ask which need it would solve, check whether `src/` can meet it, and enter engine mode only if the user confirms |
| Deployment, hosting, DNS, CI or publishing | Say that it is outside this process and do not touch it. The human reference is `DOCUMENTATION.md` section 7.6 |
| A review, audit or explanation of the code or the site | Do it read-only and change nothing |

## 2. Your job: build a site with `legible`

The zip is the **generic base**. Your job is to adapt it into a website for one business, changing **only `src/`**.

Your job is **not** to improve, refactor, optimize or "fix" the engine (`legible/`), the tests (`tests/`) or the architecture. Do not open them for editing on your own initiative, even if you see something you would do differently. The only exception is section 7. Deployment is not your job either (section 8, rule 7).

## 3. Modes

| Situation | Mode |
|---|---|
| No `SITE_PLAN.md` and a start command | **Interview mode** (section 4) |
| A `SITE_PLAN.md` with phases not `done`, and a continue or start command or no specific request | **Execution mode** (section 6) |
| No `SITE_PLAN.md` and `project_stage` is `in_progress` | **Recovery mode** (section 6): rebuild the plan from the project state, then continue |
| No `SITE_PLAN.md` and `project_stage` is `complete` | **Refinement mode** (section 6): no plan and no flow; work on the part the user names |
| A `SITE_PLAN.md` whose status is `complete`, and a continue or start command or no specific request | **Maintenance mode** (section 6): report the final state and work only on the part the user names |
| The user explicitly says "engine mode" or asks to change `legible/` or `tests/` (with or without a plan) | **Engine mode**: read `DOCUMENTATION.md` sections 0.1 and 2 first; keep the change small, update the tests and keep the baseline green |
| The user explicitly asks to build the whole site in one session without a plan (`DOCUMENTATION.md` section 6.3) | **One-session mode**: skip the interview and the plan, follow stages S0 to S6 in `DOCUMENTATION.md` section 5.4, and obey sections 8 and 9 of this file |

## 4. Interview mode

**Goal:** collect just enough to write a short plan for the base of the site. The only thing you add to the project is `SITE_PLAN.md`; you change no other file.

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

## 5. The plan: `SITE_PLAN.md`

The plan covers the **base of the site only**: the structure and the basics. It is a short map, not a task list. It has at most **five phases**, each small enough to execute in one session.

**Size limits.** A later session reads `SITE_PLAN.md` in full, so keep it small:
- The whole file fits in about 120 lines. If it does not, cut it; do not compress it.
- The briefing is one short line per item, not paragraphs.
- Each phase has **at most four lines** of detail: files to touch, expected result, verification command.
- No per-page outlines, no copy, no keyword lists, no checklists of small tasks. What each page says is decided in phase 4, with the data already in the plan.
- The URL map has one row per page, with a purpose of a few words.
- Each **Later** item is one line.
- Detail is decided when a phase runs, not before. If a phase seems to need more than one session, split it, up to the limit of five phases; if it still does not fit, move part of it to **Later**.
- The execution log is at most three lines per session. When the log gets long, summarize the old entries into one line.

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
- **Gaps:** hours, legal data, existing URLs to keep, everything unknown as [CONFIRM …].

## URL map
| Page | URL | Purpose |
|---|---|---|

## Phases
| # | Phase | Status | Date | Verification |
|---|---|---|---|---|
| 1 | Data: `site.json`, `entity.json`, `texts.json` | pending | | |
| 2 | Structure and URLs: pages, menu, `sitemap_base_order`, internal links | pending | | |
| 3 | Design and brand: tokens in `site.css`, layout and partials, assets | pending | | |
| 4 | Content: write every page | pending | | |
| 5 | Legal, final checks and close: legal pages, pre-launch sweep, full strict baseline | pending | | |

### Phase details
<for each phase, at most four lines: files to touch, expected result, verification command>

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

## 6. Execution, completion, maintenance, recovery and refinement

**Execution mode**

1. Read `SITE_PLAN.md`. Take the first phase that is not `done`. Execute **only that phase**, unless the user asks for more.
2. Work only in `src/`. Respect anything the user changed by hand since the last session; note it in the log instead of reverting it. If a new instruction from the user contradicts the plan, say so and ask which one wins. If `project_stage` disagrees with the plan, trust the plan, fix the field and note it in the log.
3. Verify the phase (section 9) and run the baseline when the phase says so. Do not mark a phase `done` without a real check.
4. Update `SITE_PLAN.md`: phase status and date, verification result, the execution log with the decisions taken, the pending-confirmation table, the Later list and the overall status (`in progress`). When phase 1 starts, set `project_stage` in `src/data/site.json` to `in_progress`. If the phase failed or stopped halfway, set `blocked` or `in_progress` and write where it stopped.
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
3. Write `SITE_PLAN.md` from the evidence, within the size limits of section 5: the briefing from the data files, the URL map from the pages that exist, and the pending table from the `[CONFIRM` and sweep hits. Mark a phase `done` only when the evidence supports it (data with no sample values; pages and menu consistent with `sitemap_base_order`; design tokens and assets replaced; every page free of sample content and passing the validator; legal pages with no sample values and a clean sweep). Otherwise mark it `pending` or `in_progress` and say what is missing. Never guess a fact that is not in the files: it goes to the pending table.
4. Ask at most three questions, only about what the files cannot tell (for example what was meant for **Later**). Show the reconstructed plan and ask the user to confirm it.
5. Return the zip with `SITE_PLAN.md` inside (section 5), with one log line saying the plan was reconstructed from the project state on that date. Set `project_stage` to match: `complete` and a filled **Final state** if every phase is `done`, otherwise `in_progress`, and the next session continues with the first phase that is not `done`.

## 7. The engine exception

The engine adapts only when there is no other way. Before touching `legible/` or `tests/`:

1. Confirm that the need cannot be met from `src/`.
2. Make the smallest possible change, with no new dependencies and no client-side JavaScript.
3. Keep the tests and the strict validator green. Never weaken a test or a validator rule.
4. Record it in the plan under **Engine notes** (what and why) and in your final message. Never change the engine silently.

If the change is large or would break the rules in section 8, stop and ask the user.

## 8. Rules that never bend

1. No new dependencies, frameworks, client-side JavaScript or external resources.
2. Never invent business facts. Missing data stays as a visible `[CONFIRM …]` marker, or you ask.
3. Never weaken tests or validator rules to get a green result; fix the content instead.
4. Every page must pass the strict validator (rules in `DOCUMENTATION.md` section 7.2).
5. Replace every sample value and run the pre-launch sweep (`DOCUMENTATION.md` section 7.4) before the plan is closed.
6. Do not run Git commands (commit, tag, push) unless the user asks.
7. Do not deal with deployment: no hosting, DNS, CI, publishing or host-level redirects. It is outside this process. If asked, say so.

## 9. Verify: run it, never assume

```bash
python3 -B -m unittest discover tests
SITE_URL=https://example.com ./legible/build.sh
```

Expect `OK` from the tests and `CHECK PASSED` from the validator. Report the real output and inspect `dist/`, not only the sources.

- **Phases 1 to 4:** the strict build may fail on `[CONFIRM` markers and pages not yet adapted. Errors must be fixed. Warnings that come only from facts still pending may be reviewed with `CHECK_STRICT=FALSE ./legible/build.sh`; list each one in the plan as expected, with its reason.
- **Last phase:** run the strict build with no override. The plan is not `complete` until it passes, or until every remaining warning is a pending fact listed in the plan and the user has been told.
- **If you cannot run commands** (a chat without a shell), say so plainly, do not claim that anything passed, and list the exact commands the user must run.

## 10. Map

- `SITE_PLAN.md` (project root): the short plan, its status and, once finished, the final state. Present in execution and maintenance mode.
- `src/pages/`: one folder per page. `src/data/*.json`: business facts and texts. `src/layout.html` and `src/partials/`: shared shell. `src/css/site.css`: design tokens and styles.
- `legible/`: build, validator, dev server. `legible/locales/`: engine strings per language. Do not edit.
- `tests/`: regression suite. Do not edit.
- `DOCUMENTATION.md`: section 5.0 (methodology), 3 (content model), 4.2 (other languages), 5 (guide for AIs), 7 (markers, validator, commands).
