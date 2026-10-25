# AGENTS.md

`legible` is a lightweight static-site generator for local service businesses. It uses only the Python standard library and ships no client-side JavaScript. This file is the entry point for AI agents; the full contract is in [`DOCUMENTATION.md`](DOCUMENTATION.md).

## Choose your task

- **Generate or adapt a site** (the usual case): change only `src/`. Read `DOCUMENTATION.md` section 5 (AI guide) and section 6.1 (prompt), plus section 3 (content model) and section 4.2 if the site is not in English. Do not edit `legible/` or `tests/`.
- **Change the engine** (`legible/`, `tests/`): read section 0.1 (ground rules) and section 2 (architecture) first. Keep the change small, update tests and keep the baseline green.

## Rules that never bend

1. No new dependencies, frameworks, client-side JavaScript or external resources.
2. Never invent business facts: hours, reviews, awards, certifications, years in business, figures. Missing data stays as a visible `[CONFIRM …]` marker, or you ask.
3. Never weaken tests or validator rules to get a green result; fix the content instead.
4. Every page must pass the strict validator (rules in section 7.2).
5. Replace every sample value before publishing and run the pre-launch sweep (section 7.4).
6. Do not run Git commands (commit, tag, push) unless the user asks.

## Verify: run it, never assume

```bash
python3 -B -m unittest discover tests
SITE_URL=https://example.com ./legible/build.sh
```

Expect `OK` from the tests and `CHECK PASSED` with no warnings from the validator. Report the real output and inspect `dist/`, not only the sources.

## Map

- `src/pages/`: one folder per page. `src/data/*.json`: business facts and texts. `src/layout.html` and `src/partials/`: shared shell.
- `legible/`: build, validator, dev server. `legible/locales/`: engine strings per language.
- `tests/`: regression suite.
