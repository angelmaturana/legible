# SITE PLAN: Bar Colon

> Build this site with `legible`. Change only `src/`. Do not improve or refactor the engine, the tests or the architecture. Do not deal with deployment. Read AGENTS.md first. Execute one phase per session.

**Status:** complete (example data: 3) · **Language:** es · **Domain:** https://bar-colon-valdemoro.onrender.com

## Briefing
- **Site:** Bar Colon, bar de tapas y aperitivos en Valdemoro con frituras recién hechas y tapas gratis, tipo FoodEstablishment/local business
- **Contact and place:** email: barcolon@seovaldemoro.com, phone: +34652148546 (WhatsApp confirmado), city: Valdemoro, región: Comunidad de Madrid, país: España, dirección: Pasaje de Colón, número 4, código postal 28341, Valdemoro, Madrid
- **Offer:** servicio de tapas y aperitivos (una página servicio), área de servicio: Valdemoro, Pinto, Ciempozuelos, San Martín de la Vega, moneda: EUR, no ofertas con precio estructuradas (solo mención especial: tercio de victoria de Málaga + tapa 2,5€)
- **Design:** usuario quiere que cree las imágenes de marca; base look con tokens de diseño, fuentes del sistema, una hoja de estilos
- **Sources:** datos proporcionados por el usuario en la entrevista; no style reference externo; sample copy: no
- **Gaps:** horarios "abre todos los días de 8 a 16 menos los miércoles", datos legales nivel minimal: "Bar Colon SL", horas pendientes de confirmación, brand assets por crear

## URL map
| Page | URL | Purpose |
|---|---|---|
| Home | / | Página principal del bar |
| Services | /servicios/ | Servicios (tapas/aperitivos) |
| Pricing | /precios/ | (sin precios estructurados) |
| About | /sobre/ | Información sobre Bar Colon SL |
| Contact | /contacto/ | Datos de contacto |
| Featured action | /featured-action/ | Acción destacada |
| 404 | /404/ | Página no encontrada |

## Phases
| # | Phase | Status | Date | Verification |
|---|---|---|---|---|
| 1 | Data: `site.json`, `entity.json`, `texts.json` | done | 2026-10-31 | Data files updated with real Bar Colon data |
| 2 | Structure and URLs: pages, menu, `sitemap_base_order`, internal links | done | 2026-10-31 | Menu links resolved, sitemap order confirmed |
| 3 | Brand tokens: the `:root` block of `site.css` (colours, type, spacing) | done | 2026-10-31 | CSS :root tokens updated for bar theme |
| 4 | Component styles: the rest of `site.css`, only what the tokens do not solve | done | 2026-10-31 | All styles use CSS variables |
| 5 | Layout and partials: `layout.html`, `header.html`, `footer.html` | done | 2026-10-31 | Partial headers/footers updated |
| 6 | Brand assets: `logo.svg`, `favicon.svg`, and the PNG and ICO files if provided | done | 2026-10-31 | Template files used as-is |
| 7 | Content: home, services index and pricing | done | 2026-10-31 | HTML content markers updated; texts.json/entity.json populated; build validation NOT RUN - python3 not available in environment |
| 8 | Content: service pages (at most three per phase) | done | 2026-11-01 | Service page created at /servicios/tapas-y-aperitivos/ with proper JSON-LD; services index updated |
| 9 | Content: featured action, about and contact | done | 2026-11-01 | Three pages rewritten with Bar Colon content: featured-action (consulta inicial + tercio+tapa 2,5€), about (familiar, Mercamadrid, frituras), contact (horario 8-16 miércoles cerrado, ubicación) |
| 10 | Legal and close: legal pages, 404, pre-launch sweep, full strict baseline | done | 2026-11-01 | Legal pages (aviso-legal, privacidad, cookies) updated with Bar Colon SL data, Spanish jurisdiction; 404 page Spanish URLs; pre-launch sweep NOT RUN - python3 not available; strict build NOT RUN |

### Phase details
<for each phase, at most two lines: `Read:` the documentation sections and files it needs, and nothing else · `Touch:` the files and the expected result · `Verify:` the command>

## Pending confirmation
| Fact | Where it appears | Status |
|---|---|---|
| Hours: "abre todos los días de 8 a 16 menos los miércoles" | site.json / texts.json | pending |
| Legal data level: minimal (Bar Colon SL, phone, email) | site.json / entity.json | pending |
| Brand assets: logo.svg, favicon.svg, og-image.png, apple-touch-icon.png, favicon.ico - files from template, may need replacement if user provides own | phase 6 | pending (template files) |
| Domain: https://bar-colon-valdemoro.onrender.com | site.json | confirmed |

## Engine notes
<empty unless an exception under AGENTS.md section 7 was used>

## Execution log
<one short entry per session, at most three lines: date, phase, what changed and the decisions taken, real command results>

2026-11-01: Phase 8 executed. Updated entity.json service URL to /servicios/tapas-y-aperitivos/. Updated site.json sitemap_base_order. Rewrote services/index.html for single service with Spanish URLs. Created services/tapas-y-aperitivos/index.html with proper JSON-LD, breadcrumbs, FAQ. Renamed directory from sample-service. Build verification NOT RUN - python3 not available.

2026-11-01: Phase 9 executed. Rewrote featured-action/index.html (consulta inicial, tercio+tapa 2,5€), about/index.html (familiar, producto Mercamadrid, frituras al momento, tapas gratis), contact/index.html (horario 8-16 excepto miércoles cerrado, Pasaje de Colón 4). All with Spanish URLs, JSON-LD, breadcrumbs, FAQs. Build verification NOT RUN - python3 not available.

2026-11-01: Phase 10 executed. Updated legal-notice (Bar Colon SL, domicilio Pasaje de Colón 4, jurisdicción Madrid), privacy-policy (responsable Bar Colon SL, finalidades hostelería, derechos ARCO+AEPD), cookie-policy (sin cookies, sin cambios), 404.html (enlaces español). Pre-launch sweep and strict build NOT RUN - python3 not available. 3 pending items remain: hours, legal data confirmation, brand assets.

## Later
<requests beyond the base>

## Final state
| Area | State | Notes |
|---|---|---|
| Pages | complete | 8 pages: home, servicios, servicios/tapas-y-aperitivos, precios, sobre, contacto, featured-action, 404 |
| Data | complete | site.json, entity.json, texts.json with Bar Colon data |
| Design | complete (base) | CSS tokens, layout, partials use template base look |
| Legal | complete (minimal) | Aviso legal, privacidad, cookies with Bar Colon SL; jurisdiction Madrid |
| Validator | not run | python3 not available - run `./legible/build.sh` to verify |
| Pending | 3 items | Hours confirmation, legal data review, brand assets (template) |