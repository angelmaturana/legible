# Legible

> **A production-ready, zero-JS static site generator for professional service businesses** — built with Python stdlib, semantic HTML, structured data, and strict SEO validation. Deploy anywhere static files are served.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Static](https://img.shields.io/badge/Static-HTML%2FCSS%2FImages-2ea44f)](https://github.com/)
[![Zero JS](https://img.shields.io/badge/Zero-JS-ff6b6b?logo=javascript&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Schema.org](https://img.shields.io/badge/Schema.org-JSON--LD-1a73e8)](https://schema.org)
[![CI Ready](https://img.shields.io/badge/CI-Ready-brightgreen)]()
[![Deploy to Render](https://img.shields.io/badge/Deploy%20to-Render-46E3B7?logo=render&logoColor=white)](https://render.com/deploy)
[![Kilo Agent](https://img.shields.io/badge/Built%20with-Kilo%20Agent-7C3AED?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6bTAgMTNsMTAgNSAxMC01bC0xMC01LTEwIDV6bTAgMTNsMTggOS0xOCA5eiIvPjwvc3ZnPg==)](https://kilo.ai)

---

## Why This Exists

Most "static site generators" are over-engineered for simple business sites. You don't need React, a build pipeline, a headless CMS, or 500 npm packages to rank a local service business. You need:

- **Clean semantic HTML** that search engines *actually* understand
- **Complete structured data** (Schema.org `ProfessionalService` + `WebSite` + `WebPage` + `FAQPage` + `ItemList`)
- **Zero runtime dependencies** — Python 3 stdlib only
- **Strict validation** that fails the build on SEO errors
- **Instant deploys** to Netlify, Cloudflare Pages, Vercel, GitHub Pages, S3, or any static host

This is the generator I wish existed when I started building client sites. No magic. No lock-in. Just HTML that works.

---

## Quick Start

```bash
# 1. Clone & enter
git clone https://github.com/angelmaturana/legible.git
cd legible

# 2. One-command build + validation
./scripts/build.sh
# → dist/ ready to deploy

# 3. Local dev server with hot-rebuild
python3 scripts/dev.py
# → http://localhost:3001 (rebuilds on file save)
```

> **Pro tip:** `CSS_MINIFY=FALSE ./scripts/build.sh` keeps HTML/CSS readable for debugging.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUILD PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  src/                          dist/ (deploy this)              │
│  ├── layout.html               ├── index.html                   │
│  ├── partials/                 ├── servicios/                   │
│  │   ├── header.html           │   └── index.html              │
│  │   └── footer.html           ├── precios/                     │
│  ├── pages/                    │   └── index.html              │
│  │   ├── index.html            ├── ...                         │
│  │   ├── servicios/            ├── sitemap.xml                 │
│  │   │   └── index.html        ├── robots.txt                 │
│  │   └── ...                   ├── llms.txt                   │
│  ├── data/                     └── css/                        │
│  │   └── entity.json               └── site.css (minified)    │
│  ├── css/                                                                │
│  │   └── site.css                                                           │
│  └── static/                                                               │
│      ├── images/                                                           │
│      ├── robots.txt                                                        │
│      └── llms.txt                                                          │
│                                                                 │
│  build.py ──► 1. Load partials & entity.json                    │
│       │     2. Parse front matter from pages                     │
│       │     3. Replace {{placeholders}} from entity.json        │
│       │     4. Auto-generate collections (/guias/, /blog/)      │
│       │     5. Inject JSON-LD (@graph, no duplicate @id)        │
│       │     6. Minify CSS (custom, preserves calc/clamp)        │
│       │     7. Minify HTML (protects JSON-LD & attributes)      │
│       │     8. Generate sitemap.xml with lastmod                │
│       │     9. Generate llms.txt for AI crawlers                │
│       │     10. Run check_site.py --strict                      │
│       │                                                         │
│       ▼                                                         │
│  [OK]      → dist/ ready                                        │
│  [FAIL]    → Detailed report, exit 1                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Python stdlib only** | Zero supply-chain risk, trivial auditing, runs anywhere Python runs | No Jinja2/Markdown — templates are raw HTML with front matter |
| **Single `@graph` per page** | Schema.org best practice; avoids duplicate entities, enables cross-references | Slightly more complex merge logic in `render_jsonld()` |
| **No client-side JS** | Eliminates hydration, execution risk, CSP complexity, TBT | No progressive enhancement — acceptable for content sites |
| **Custom CSS minifier** | Preserves `calc()`, `clamp()`, `min()`, `max()` that standard minifiers break | ~150 lines of minifier code to maintain |
| **HTML minifier protects attributes** | Prevents `alt="a  b"` → `alt="a b"` corruption | More complex than regex-only approaches |
| **Validator fails on warnings** | CI gate prevents SEO regressions reaching production | Requires clean codebase; no "I'll fix it later" |
| **Entity.json as single source** | DRY — business data defined once, injected everywhere | Upfront modeling effort; schema changes require rebuild |
| **Collections auto-generate** | Zero config for guides/blog; indexes, sitemap, llms.txt emerge | Less control than manual curation; opinionated structure |
| **CSS-only responsive nav** | No JS dependency for core UX; works without JS | Checkbox hack has focus/accessibility edge cases |
| **System font stack** | Zero font downloads, instant FCP, no CLS from font swap | No brand typography — pragmatic for service businesses |

---

## Features That Matter

### SEO-First by Default

| Feature | Implementation |
|---------|----------------|
| **Semantic HTML5** | `<main>`, `<section>`, `<article>`, `<nav>`, `<aside>` — proper hierarchy |
| **Single H1 per page** | Enforced by validator (build fails otherwise) |
| **Canonical + OG + Twitter** | Auto-generated, HTTPS, validated |
| **JSON-LD `@graph`** | Merged site-wide `ProfessionalService` + `WebSite` + per-page nodes |
| **FAQPage = Visible FAQ** | Text must match character-for-character (validator enforces) |
| **Sitemap.xml** | Auto-generated, `lastmod` = JSON-LD `dateModified` |
| **robots.txt** | Permissive, declares sitemap, no `Disallow: /` |
| **llms.txt** | Structured for LLM crawlers (guides, blog, services) |
| **Geo tags** | Optional per-page via front matter |

### Content Collections (Zero Config)

```markdown
# Add a guide → auto-appears in /guias/ index, sitemap, llms.txt
src/pages/guias/mi-guia/index.html
---
type: guia
topic: "SEO Local"
published: 2026-10-20
updated: 2026-10-20
summary: Cómo optimizar tu ficha de Google Business Profile
service: /servicios/seo-local/
related: /blog/auditoria-seo/, /guias/palabras-clave/
---

# Add an article → /blog/ appears automatically at ≥3 posts
src/pages/blog/mi-articulo/index.html
---
type: articulo
topic: "IA y SEO"
published: 2026-10-20
updated: 2026-10-20
summary: Por qué el contenido generado por IA necesita supervisión humana
service: /servicios/consultoria-seo/
related: /guias/contenido-ia/, /servicios/redaccion/
---
```

> **Smart indexing:** `/guias/` renders if ≥1 guide exists. `/blog/` renders `noindex` at 1-2 posts, becomes indexable at ≥3.

### CSS: Modern, Minimal, Maintainable

- **CSS Custom Properties** (design tokens: colors, spacing, radii, typography)
- **Mobile-first** fluid typography with `clamp()`
- **Container queries** ready (`@container` for component-level responsiveness)
- **No animations/transitions** — respects `prefers-reduced-motion`, zero CLS
- **System font stack** — zero font downloads, instant render
- **Custom minifier** — preserves `calc()`, `clamp()`, `min()`, `max()`, attribute values, JSON-LD

### Accessibility Built-In

- Skip link (first focusable element)
- `aria-current` on active nav item (auto-injected)
- `aria-label` on icon-only buttons/links
- Semantic heading hierarchy (h1→h2→h3, no skips)
- Focus-visible outlines (`2px solid var(--accent)`)
- Sufficient contrast ratios (≥4.5:1 text, ≥3:1 UI)
- `prefers-reduced-motion` respected (no transitions exist anyway)

### Validation That Actually Catches Things

`check_site.py --strict` fails the build on **any** error or warning:

```
╔══════════════════════════════════════════════════════════════╗
║  Legible  •  Site Checker                            ║
╠══════════════════════════════════════════════════════════════╣
║  ✗  CHECK FAILED                                             ║
╠══════════════════════════════════════════════════════════════╣
║  ✗  Errors                                                   ║
║  • servicios/index.html → título duplicado con index.html    ║
║  • contacto/index.html → <img> sin alt: /images/logo.svg     ║
║  • blog/articulo-1/index.html → ancla inexistente: #faq      ║
╚══════════════════════════════════════════════════════════════╝
```

**Checks performed:**
- HTML structure (`lang`, `viewport`, `title`, `description`, `robots`, `canonical`, `og:*`, `twitter:*`)
- Heading hierarchy (1 H1, no level skips, no empty headings)
- Images (`alt`, `width`, `height` — CLS prevention)
- Links (absolute internal, no broken refs, valid anchors, `rel="noopener"` on `target="_blank"`)
- JSON-LD validity, `@context`, unique `@id`, defined references, required nodes
- FAQ visible = FAQ schema (exact text match)
- Content minimums (≥250 words in `<main>` for indexable pages)
- Duplicate titles/descriptions across indexable pages
- Orphan pages (indexable pages without contextual inbound links from `<main>`)
- Sitemap validity, completeness, `lastmod` consistency
- `robots.txt` sanity
- `llms.txt` placeholder resolution
- Unrendered `{{placeholders}}`, `TODO`, `[CONFIRMAR]`

---

## Project Structure

```
legible/
├── scripts/
│   ├── build.py           # Core generator (stdlib only, ~1100 lines)
│   ├── check_site.py      # Strict validator (~750 lines)
│   ├── dev.py             # Dev server + file watcher + hot rebuild
│   └── build.sh           # Wrapper: build --minify + check --strict
├── src/
│   ├── layout.html        # Base template (head, meta, OG, JSON-LD slot)
│   ├── partials/
│   │   ├── header.html    # Responsive nav (CSS-only checkbox hack)
│   │   └── footer.html    # Contact, 3 nav columns, copyright
│   ├── pages/             # 11 core pages + empty guias/blog dirs
│   │   ├── index.html
│   │   ├── servicios/
│   │   ├── precios/
│   │   ├── sobre-nosotros/
│   │   ├── contacto/
│   │   ├── accion-destacada/
│   │   ├── aviso-legal/ (noindex)
│   │   ├── politica-de-privacidad/ (noindex)
│   │   ├── politica-de-cookies/ (noindex)
│   │   └── 404.html
│   ├── data/
│   │   └── entity.json    # Single source of truth for business data
│   ├── css/
│   │   └── site.css       # ~660 lines, tokens + components
│   └── static/
│       ├── images/        # Placeholders (logo, og-image, favicon)
│       ├── robots.txt
│       └── llms.txt       # Template with {{markers}}
└── dist/                  # Generated output (gitignored)
```

---

## Customization: The 5-Minute Setup

All business data lives in **one file**: `src/data/entity.json`. Edit it, rebuild, done.

```json
{
  "@type": "ProfessionalService",
  "@id": "https://TU-DOMINIO.com/#business",
  "name": "Tu Negocio",
  "description": "Descripción corta (1 frase)",
  "url": "https://TU-DOMINIO.com",
  "email": "hola@tu-negocio.com",
  "logo": "https://TU-DOMINIO.com/images/logo-schema-placeholder.jpg",
  "image": "https://TU-DOMINIO.com/images/og-placeholder.jpg",
  "contactPoint": {
    "telephone": "+34600123456"
  },
  "address": {
    "addressLocality": "Madrid",
    "addressRegion": "Madrid",
    "addressCountry": "ES"
  },
  "areaServed": [
    { "@type": "City", "name": "Madrid" },
    { "@type": "City", "name": "Alcobendas" },
    { "@type": "City", "name": "San Sebastián de los Reyes" },
    { "@type": "City", "name": "Las Rozas" }
  ],
  "knowsAbout": [
    "Servicio Principal",
    "Servicio Secundario",
    "Tema 3", "Tema 4", "Tema 5", "Tema 6"
  ],
  "priceRange": "0 € - 299 €/mes",
  "hasOfferCatalog": {
    "itemListElement": [
      { "name": "Servicio 1", "price": "99", "url": "/servicios/servicio-1/" },
      { "name": "Servicio 2", "price": "149", "url": "/servicios/servicio-2/" },
      { "name": "Mantenimiento Mensual", "price": "49", "url": "/servicios/mantenimiento/" },
      { "name": "Acción Destacada", "price": "0", "url": "/accion-destacada/" }
    ]
  }
}
```

**The build extracts everything from here:** site name, domain, email, phone, WhatsApp link, cities, service categories, prices, featured action — no scattered placeholders to hunt down.

---

## Adding a New Service (30 Seconds)

```bash
# 1. Duplicate the template
cp -r src/pages/servicios/servicio-generico/ src/pages/servicios/mi-nuevo-servicio/

# 2. Edit front matter + JSON-LD + content
#    - Change @id, name, serviceType, offers.price, URLs
#    - Write your content (h1, sections, FAQ)

# 3. Register in entity.json → hasOfferCatalog.itemListElement

# 4. Add card in src/pages/servicios/index.html + src/pages/precios/index.html

# 5. Add nav links in header.html (submenu) + footer.html (Servicios list)

# 6. Build
./scripts/build.sh
```

---

## Deploy Anywhere Static

```bash
# Netlify / Vercel / Cloudflare Pages
# Build command: ./scripts/build.sh
# Output dir: dist

# GitHub Pages
# Push dist/ to gh-pages branch (or use Actions)

# AWS S3 + CloudFront
aws s3 sync dist/ s3://your-bucket --delete --cache-control "public, max-age=31536000, immutable" --exclude "*.html"
aws s3 sync dist/ s3://your-bucket --delete --cache-control "no-cache" --include "*.html"

# Any VPS (Nginx/Caddy/Apache)
# Point document root to dist/
```

**Recommended headers:**
```nginx
# Static assets (CSS, images) — 1 year, immutable
location ~* \.(css|js|jpg|jpeg|png|webp|avif|svg|ico|woff2)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
}

# HTML — no cache (always fresh)
location ~* \.html$ {
    add_header Cache-Control "no-cache, must-revalidate";
}

# 404 custom page
error_page 404 /404.html;

# Compression
gzip on; gzip_types text/css application/json application/javascript text/xml;
brotli on; brotli_types text/css application/json application/javascript text/xml;
```

---

## Performance Profile

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **HTML size** | < 15 KB gzipped | Fast TTFB, instant parse |
| **CSS size** | < 8 KB gzipped | Single critical file, no render-blocking |
| **JS size** | **0 bytes** | No hydration, no execution, no vulnerabilities |
| **Requests** | 3-5 (HTML + CSS + 1-3 images) | Minimal waterfall |
| **LCP** | < 1.5s (typical) | Hero is text + inline SVG, no image dependency |
| **CLS** | 0 | Explicit `width`/`height` on all images, no font swap |
| **TBT** | 0 ms | No main-thread JS |

> Run `./scripts/build.sh && npx lighthouse http://localhost:3001 --view` to verify.

---

## Development Workflow

```bash
# Hot-reload dev server
python3 scripts/dev.py
# → Serves .dev-dist/ on :3001
# → Rebuilds on any src/ change (~200ms)

# Debug build (readable output)
CSS_MINIFY=FALSE ./scripts/build.sh

# Skip validation (fast iteration)
CHECK_STRICT=FALSE ./scripts/build.sh

# Validate existing dist/
python3 scripts/check_site.py --strict --dir dist
```

---

## Architectural Patterns Used

### Single Source of Truth
`entity.json` is the canonical data model. The build pipeline treats it as a **database** — every placeholder in every template resolves from here. This eliminates the class of bugs where phone numbers, prices, or service names drift between pages.

### Compile-Time Validation Over Runtime Checks
The validator runs at **build time**, not runtime. A broken canonical, missing `alt`, or malformed JSON-LD never reaches production. This shifts left the entire SEO quality gate.

### `@graph` Merging With Deduplication
`render_jsonld()` merges site-wide entities (`ProfessionalService`, `WebSite`) with page-specific nodes (`WebPage`, `FAQPage`, `CollectionPage`). It tracks `@id` collisions and drops duplicates — ensuring each entity exists exactly once in the final graph, referenceable by `@id` from any node.

### Placeholder System With Fail-Fast
`{{placeholder}}` syntax is intentional: the build **aborts** on any unrendered marker. No silent failures where `{{site_name}}` ships to production. The `_unwrap_placeholder()` helper provides defaults only for optional fields.

### Collection Discovery By Convention
Guides and articles are discovered by filesystem structure (`src/pages/guias/*/index.html`). No registry, no config file. The build validates front matter schema, enforces slug format, cross-references `related` links, and generates indexes/sitemap/llms.txt automatically.

### CSS Minifier Preserving Modern Features
Standard minifiers (cssnano, lightningcss) break `calc(100% - 2rem)`, `clamp(1rem, 2vw, 2rem)`, or `min(50%, 400px)`. The custom minifier extracts math functions, minifies the rest, then restores them — keeping fluid typography and responsive spacing intact.

### HTML Minifier Protecting Attribute Values
Aggressive whitespace collapsing breaks `alt="Screen reader text"` → `alt="Screen reader text"`. The minifier protects quoted attribute values **before** collapsing, then restores them — preserving accessibility semantics.

---

## Extending the Generator

### Add a New Collection Type
1. Add to `COLLECTION_DIRS` and `COLLECTION_TOPICS` in `build.py`
2. Implement `render_{type}_index()` returning `(front, content)`
3. Add to `build_sitemap()` order and `render_llms_*()` functions
4. Update `blog_state()` logic if indexable threshold differs

### Add a New JSON-LD Node Type
1. Define node in `entity.json` or page front matter
2. Ensure `@id` follows pattern: `{SITE_URL}#{entity-name}`
3. Reference from other nodes using `{"@id": "..."}`
4. Validator will enforce `@context`, uniqueness, reference integrity

### Custom Validation Rules
Add functions to `check_site.py` following the `E(msg)` / `W(msg)` pattern. Register in `run_checks()` — they run for every page with full parser access.

---

## Deploy on Render

Zero-config **Static Site** hosting with auto-deploys, custom domains, and free TLS.

**One-click deploy:**
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/angelmaturana/legible)

**Manual setup (2 minutes):**

1. **New → Static Site** (not "Web Service") → Connect your GitHub repo
2. **Settings:**
   ```
   Build Command: ./scripts/build.sh
   Publish Directory: dist
   ```
   > **Important:** Select **Static Site** as the service type. Render will run the build command, then serve the `dist/` folder directly via its global CDN — no runtime, no server process, zero cold starts.

3. **Environment Variables** (Settings → Environment):
   | Key | Value | Purpose |
   |-----|-------|---------|
   | `SITE_URL` | `https://your-domain.onrender.com` | Used by build.py for canonical URLs, JSON-LD `@id`, sitemap, OG tags |
   | `CHECK_STRICT` | `TRUE` | Fails build on any validation warning (recommended for production) |
   | `CSS_MINIFY` | `TRUE` | Minifies CSS (default: TRUE, set FALSE for debug) |

   > The build reads `SITE_URL` at compile time. If omitted, it falls back to `https://TU-DOMINIO.com` (placeholder). Set it to your actual Render URL or custom domain **before first deploy** so generated HTML has correct absolute URLs.

4. **Custom Domain** → Settings → Custom Domains → Add (auto-provisions TLS via Let's Encrypt)

**Why Render Static Site for this project:**
- Native static file serving — no Node/Python runtime in production
- `render.yaml` support for IaC (see below)
- Free tier: unlimited static sites, custom domains, DDoS protection, global CDN
- Auto-deploys on push to main
- Preview environments for every PR (unique subdomain per PR)
- Edge cache with `Cache-Control` headers respected

**`render.yaml` (Infrastructure as Code):**
```yaml
services:
  - type: static
    name: legible
    buildCommand: ./scripts/build.sh
    staticPublishPath: ./dist
    pullRequestPreviewsEnabled: true
    envVars:
      - key: CHECK_STRICT
        value: "TRUE"
      - key: SITE_URL
        value: "https://your-domain.onrender.com"
    domains:
      - your-domain.com
```
Commit this file → Render detects it on next push (or import via "New → Blueprint").

---

## AI Agent Prompt: Generic → Mechanic Shop

Use **Kilo Agent** (free, includes Nemotron 3 Ultra) to transform this template into a production-ready mechanic shop site in one session.

### Copy-Paste Prompt for Kilo Agent

> **Context:** You have a generic static site generator template (`legible`) for professional service businesses. Convert it into a complete website for **"Taller Mecánico García"**, a car repair shop in **Madrid, Spain**.
>
> **Business Data:**
> - Name: `Taller Mecánico García`
> - Domain: `tallermecanicogarcia.com`
> - Email: `hola@tallermecanicogarcia.com`
> - Phone: `+34912345678`
> - WhatsApp: `https://wa.me/34912345678?text=Hola,%20quiero%20pedir%20cita%20en%20Taller%20Mec%C3%A1nico%20Garc%C3%ADa`
> - Address: `Calle de la Industria 12, 28005 Madrid, España`
> - Area served: Madrid, Alcobendas, San Sebastián de los Reyes, Las Rozas, Pozuelo de Alarcón, Majadahonda
> - Services: Mecánica general, Diagnóstico electrónico, Neumáticos, Frenos, Aire acondicionado, Pre-ITV, Mantenimiento programado
> - Price range: `30 € - 800 €`
> - Featured action: `Diagnóstico gratis` (0 €, entrega en 2h, 1 por cliente/semana)
>
> **Deliverables:**
> 1. Update `src/data/entity.json` with all business data (single source of truth)
> 2. Create 6 service pages under `src/pages/servicios/`:
>    - `mecanica-general/`, `diagnostico-electronico/`, `neumáticos/`, `frenos/`, `aire-acondicionado/`, `pre-itv/`, `mantenimiento-programado/`
>    - Each with proper JSON-LD (`Service` + `Offer`), FAQ, pricing, content ≥250 words
> 3. Update `src/pages/servicios/index.html` (grid + situation table) and `src/pages/precios/index.html`
> 4. Update `src/pages/accion-destacada/index.html` for "Diagnóstico gratis"
> 5. Update `src/pages/contacto/index.html`, `src/pages/sobre-nosotros/index.html`
> 6. Update nav in `src/partials/header.html` and footer in `src/partials/footer.html`
> 7. Replace placeholder images in `src/static/images/` (logo, og-image, favicon)
> 8. Run `./scripts/build.sh` — **must pass with CHECK PASSED**
>
> **Constraints:**
> - Zero JS, semantic HTML, strict SEO validation
> - All JSON-LD `@id` unique, `@graph` merged correctly
> - FAQ visible text = FAQ schema text (character-for-character)
> - No unrendered `{{placeholders}}`, no `TODO`, no `[CONFIRMAR]`
> - Each indexable page: ≥1 contextual inbound link from `<main>` of another page
> - Images have `alt`, `width`, `height`
> - Sitemap.xml and llms.txt generated correctly
>
> **Work Mode:**
> - **Plan Mode**: First, analyze the codebase, list all files to change, present a task list
> - **Code Mode**: Execute the plan, file by file, running build after each logical group
> - If build fails: read error, fix, re-run — zero tolerance for warnings in strict mode

### Why This Works With Kilo Agent

| Kilo Feature | Value for This Task |
|--------------|---------------------|
| **Plan Mode** | Maps the 50+ file changes before touching code — no missed updates |
| **Code Mode** | Executes with full repo context, runs `./scripts/build.sh` iteratively |
| **Nemotron 3 Ultra (free)** | 550B parameter model, strong at code + reasoning, no API key needed |
| **Agent Manager** | Spawns sub-agents for parallel work (e.g., services pages in batch) |
| **Board** | Coordinates multi-step plan across tool calls — persistent task list |
| **Built-in Tools** | `grep`/`glob`/`read`/`edit`/`bash` — no context switching |

> **Tip:** Open Kilo → `kilo agent` → paste prompt → watch it plan → approve → watch it code → `./scripts/build.sh` passes → deploy.

---

## Contributing

This is a **template**, not a framework. Fork it, customize it, ship it.

If you find a bug in the generator/validator or have a genuinely useful improvement:

1. Fork
2. Create a branch: `git checkout -b fix/validator-edge-case`
3. Make the change + add a test case if applicable
4. `./scripts/build.sh` must pass
5. PR with clear description

---

## License

**MIT** — Copyright (c) 2024 Angel Maturana Clavero / seovaldemoro.com.  
Legible está basado en la plantilla original `seo-web-generic`; se conserva su autoría y licencia MIT.  
Use freely for your projects or client work. No attribution required (appreciated though).

See [LICENSE](LICENSE) for full text.

---

## Author

**Angel Maturana Clavero**  
*Principal Software Architect — 26+ Years Core Banking • GenAI Agent Builder • Zero-JS SEO Tooling*

- **LinkedIn:** [linkedin.com/in/angelmaturana](https://linkedin.com/in/angelmaturana)
- **Agency:** [seovaldemoro.com](https://seovaldemoro.com) — Web Development + AI + Technical SEO
- **GitHub:** [github.com/angelmaturana](https://github.com/angelmaturana)

After 26 years architecting zero-downtime core banking systems at Santander (global security framework, Gravity migration, 40-ATM lab, first e-commerce), I now build **GenAI agents** and **zero-JS static site generators** with strict SEO validation baked in.

**This project (since 2025)** ships a zero-JS SEO tooling stack: semantic HTML, complete Schema.org `@graph`, sitemap, `llms.txt`, and a validator that fails the build on warnings — all in Python stdlib, zero runtime dependencies. Zero-JS isn't a constraint; it's the advantage.

---

## Competitive Landscape (Research: 2026-10-21)

| Project | Stars | Last Commit | Lang/Deps | Zero-JS | Schema.org @graph | Strict Validator | Collections | llms.txt | Minifiers | Target | Match /10 |
|---------|-------|-------------|-----------|---------|-------------------|------------------|-------------|----------|-----------|--------|-----------|
| [lintc](https://github.com/lintc/lintc) | ~50 | 2025 | Python 3.9+, **stdlib only** | ◉ | Basic (shortcodes) | ◉ `lintc check` (plugins) | Manual (YAML/MD) | ◌ | Std | General | 5/10 |
| [Pelican](https://github.com/getpelican/pelican) | 11.2k | 2025 | Python + **Jinja2, deps** | ◉ | Via plugins | ◌ | Auto (blog) | ◌ | Std | Blog | 3/10 |
| [Nikola](https://github.com/getnikola/nikola) | 3.1k | 2024 | Python + **Mako/Jinja2, deps** | ◉ | Via plugins | ◌ | Auto | ◌ | Std | Blog/Docs | 3/10 |
| [staticpipes](https://pypi.org/project/staticpipes/) | ~20 | 2023 | Python + **Jinja2 opt.** | ◉ | No native | ◑ "checks output" | Manual | ◌ | Std | General | 2/10 |
| [stattic](https://pypi.org/project/stattic/) | ~100 | 2024 | Python + **Jinja2, Mistune** | ◉ | SEO metadata | ◌ | Auto (blog) | ◉ `--llms` | Std | Blog | 4/10 |
| **Legible** (this) | — | 2025 | Python 3.10+, **stdlib only** | ◉ | Full `@graph` merge | ◉ fails on warnings | Auto (fs convention) | ◉ built-in | Custom (calc/clamp) | Business | **10/10** |

**Scoring:** ◉ = 1, ◑ = 0.5 (rounded down). Criteria: Zero-JS, Python stdlib only, Schema.org `@graph` merge, strict build validator (fails on warnings), `lastmod` from JSON-LD `dateModified`, auto `llms.txt`, filesystem collections, single JSON source, custom minifiers preserving `calc`/`clamp`, business-site focus.

**Verdict:** No project scores 8/10 or higher. The closest is **lintc (5/10)** — the only Python stdlib-only SSG with a validator — but it lacks merged `@graph`, `lastmod` from JSON-LD, `llms.txt`, custom minifiers, and business-service focus. Legible occupies a unique intersection: **Python stdlib + zero-JS + strict validator + Schema.org `@graph` merge + JSON-LD-sourced `lastmod` + auto `llms.txt` + custom minifiers + business-service templates**.

---

### Closest Competitors — Deep Dive (Top 3)

#### 1. [lintc](https://github.com/lintc/lintc) — 5/10
- **Why it's close:** Only Python stdlib-only SSG (single file, zero deps). Has `lintc check` with configurable plugins for post-build validation. Uses YAML/JSON for data, partials for layout.
- **Key gaps:** No Schema.org `@graph` merging (shortcodes only). No `lastmod` derived from JSON-LD `dateModified`. No `llms.txt` generation. No custom minifiers preserving `calc`/`clamp`. Target is general sites, not professional services.
- **License/Status:** MIT • Active (v0.10.0, 2025) • ~50 stars

#### 2. [stattic](https://pypi.org/project/stattic/) — 4/10
- **Why it's close:** Python SSG with built-in `llms.txt` generation (`--llms public`), sitemap.xml, SEO metadata, RSS. Jinja2 + Mistune.
- **Key gaps:** Requires Jinja2/Mistune (not stdlib). No strict validator failing on warnings. No `@graph` Schema.org merge. No `lastmod` from JSON-LD. No custom minifiers. Blog-focused.
- **License/Status:** MIT • Active (2024) • ~100 stars

#### 3. [Pelican](https://github.com/getpelican/pelican) — 3/10
- **Why it's close:** Mature Python SSG, huge ecosystem, auto blog collections, themes.
- **Key gaps:** Requires Jinja2 + dependencies. No strict validator. No Schema.org `@graph` merge. No `llms.txt`. No `lastmod` from JSON-LD. Blog-centric, not business services.
- **License/Status:** AGPL-3.0 • Active (2025) • 11.2k stars

---

## Credits & Inspiration

- **Schema.org** — For the vocabulary that makes structured data actually useful
- **HTML Living Standard** — For semantic elements that just work
- **Every SEO who told me "just use WordPress"** — You motivated this
- **The `check_site.py` validator** — The strictest linter I've ever written, and I'm proud of it

---

## Questions?

- **Issues**: [GitHub Issues](https://github.com/angelmaturana/legible/issues)
- **Discussions**: [GitHub Discussions](https://github.com/angelmaturana/legible/discussions)

---

<p align="center">
  <strong>Built for developers who respect the platform.</strong><br>
  <em>No frameworks. No bloat. Just HTML that ranks.</em>
</p>

<p align="center">
  <a href="https://github.com/angelmaturana/legible/stargazers">
    <img src="https://img.shields.io/github/stars/angelmaturana/legible?style=social" alt="Stars">
  </a>
  <a href="https://github.com/angelmaturana/legible/fork">
    <img src="https://img.shields.io/github/forks/angelmaturana/legible?style=social" alt="Forks">
  </a>
</p>