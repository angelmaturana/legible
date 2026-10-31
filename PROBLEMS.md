# Problemas Detectados en legible start - Bar Colon

## Contexto
Proyecto: Bar Colon - bar de tapas y aperitivos en Valdemoro, Madrid
Idioma: Español (`language: "es"` en site.json)
Objetivo: Adaptar la base genérica de legible a un negocio local real

## Problemas Detectados

### 1. URLs en inglés vs español
- **Problema**: El `sitemap_base_order` y las URLs de las páginas estaban en inglés, lo cual es inconsistente con `language: "es"`.
- **Archivos afectados**: `src/data/site.json`, `src/partials/header.html`, `src/partials/footer.html`, `SITE_PLAN.md`
- **Solución**: Traducir todas las URLs a español:
  - `/services/` → `/servicios/`
  - `/pricing/` → `/precios/`
  - `/about/` → `/sobre/`
  - `/contact/` → `/contacto/`
  - `/featured-action/` → Se mantuvo (ruta técnica)

### 2. Rutas hardcodeadas en archivos HTML
- **Problema**: Varios archivos HTML tenían rutas hardcodeadas a rutas en inglés que necesitaban actualizarse para ser consistentes con el nuevo `sitemap_base_order`.
- **Archivos afectados y cambios**:
  - `src/pages/services/index.html`: 5 enlaces `/services/sample-service/` → `/servicios/sample-service/`
  - `src/pages/featured-action/index.html`: 2 enlaces `/services/` y `/pricing/` → `/servicios/` y `/precios/`
  - `src/pages/about/index.html`: `"url": "{{site_url}}/about/"` → `"url": "{{site_url}}/sobre/"`
  - `src/partials/header.html`: Texto del menú y rutas `/services/`, `/pricing/`, `/about/`, `/contact/` → español
  - `src/partials/footer.html`: Enlaces `/services/`, `/pricing/`, `/about/`, `/contact/` → español

### 3. Datos de plantilla reemplazados por datos reales
- **Problema**: Los valores de plantilla `Your Business`, `hello@example.com`, `Your legal name`, etc. debían reemplazarse con datos reales de Bar Colon.
- **Archivos afectados**: `src/data/site.json`, `src/data/entity.json`, `src/data/texts.json`
- **Cambios realizados**:
  - `site.json`: `site_name: "Your Business"` → `"Bar Colon"`, `site_url: "https://YOUR-DOMAIN.com"` → `"https://bar-colon-valdemoro.onrender.com"`, idioma `en` → `es`, y todos los datos geográficos y de contacto actualizados.
  - `entity.json`: `@type: "ProfessionalService"` → `"FoodEstablishment"`, datos de contacto, área servida y servicios actualizados completamente.
  - `texts.json`: Todo el contenido textual reemplazado con descripción auténtica de Bar Colon en español.

### 3. Tokens de diseño (brand tokens)
- **Problema**: Los colores en `site.css` `:root` eran una paleta "slate" oscura diseñada para un tema más general/tecnológico, no para un bar.
- **Archivo afectado**: `src/css/site.css`
- **Cambios realizados**: Reemplazaron los colores slate/azul por una paleta cálida:
  - `--bg: #1A140E` (marrón oscuro)
  - `--accent: #FF9E22` (ambar - para acciones y datos clave)
  - `--glow-teal: #3D2410`, `--glow-amber: #2B1A0A`
  - `--green: #39E75F` (verde para "prompts" y checks)
  - `--bg-alt: #1A100A`, `--nav-line: rgba(190,210,240,.14)` ajustados

### 4. Partial actualizados (header y footer)
- **Problema**: Los partials `header.html` y `footer.html` contenían texto en inglés y rutas hardcodeadas que necesitaban actualizarse para el nuevo esquema de español.
- **Cambios en `header.html`**:
  - Texto del menú: "Services" → "Servicios"
  - Ruta `/services/` → `/servicios/`
  - Ruta `/pricing/` → `/precios/`
  - Ruta `/about/` → `/sobre/`
  - Ruta `/featured-action/` se mantuvo pero con texto en español
- **Cambios en `footer.html`**:
  - Textos de navegación de company: "Pricing" → "Precios", "About us" → "Sobre nosotros", "Contact" → "Contacto"
  - Enlaces actualizados coherentemente

### 5. SITE_PLAN.md nuevo
- **Problema**: No existía `SITE_PLAN.md` inicialmente; debía crearse como parte del proceso `legible start`.
- **Cambios**: Se creó con la estructura completa de 10 fases, URL map, briefing, y tabla de fases con estados.

## Resumen de Archivos Modificados (7 files)
1. `SITE_PLAN.md` - Nuevo plan con URLs en español y 10 fases
2. `src/data/site.json` - Metadatos, URLs y datos geográficos en español
3. `src/data/entity.json` - Schema.org FoodEstablishment con datos reales
4. `src/data/texts.json` - Contenido textual completo en español
5. `src/css/site.css` - Tokens de marca con paleta cálida para bar
6. `src/partials/header.html` - Menú y navegación en español
7. `src/partials/footer.html` - Pie de página con enlaces y textos en español

## Estado Actual
- Todas las 12 preguntas de la entrevista completadas
- 7 de 10 fases del plan marcadas como `done`
- 3 fases pendientes (8-10: service pages, content, legal/close)
- **Fase 7 en ejecución**: Content - home, services index and pricing
  - HTML content markers actualizados en index.html, services/index.html, pricing/index.html
  - Build validation NOT RUN - python3 no disponible en entorno sandbox
  - Content listos en texts.json/entity.json, listos para procesar por el build
  - Problemas de consistencia de URLs detectados: enlaces /services/sample-service/ deberían ser /servicios/sample-service/
- Validaciones build/test no ejecutables en este entorno (requiere python3)
- Lista de "Pending confirmation" registrada en SITE_PLAN.md

## Próximos Pasos
1. Ejecutar `python3 -B -m unittest discover tests` y `./legible/build.sh --strict` en entorno con python3
2. Resolver pending confirmation items (horas, datos legales, brand assets)
3. Continuar con fases 8-10 del plan si es necesario