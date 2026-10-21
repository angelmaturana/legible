# Fase 6 — Validación y despliegue

> Depende de: Fases 2, 4 y 5. Es el cierre: confirmar que todo lo anterior
> encaja y publicar.

## Checklist final

- [ ] `./scripts/build.sh` termina con `✓ BUILD SUCCESS` y
      `✓ CHECK PASSED`, sin errores ni avisos.
- [ ] `grep -ri "seo-web-generic\|TU-DOMINIO\|Generic Site Generator"` en
      `src/`, `scripts/` y `README.md` no devuelve nada (Fase 2).
- [ ] `grep -r "{{" src/data/entity.json` vacío (Fase 4).
- [ ] Cada página indexable tiene su `<h1>` único, su JSON-LD y al menos
      un enlace contextual de entrada desde otra página (Fase 3 + 4).
- [ ] `dist/sitemap.xml` solo contiene páginas reales, sin `/guias/` si se
      optó por retirarlas (Fase 3.2).
- [ ] Revisión visual rápida con el servidor de desarrollo:
      `python3 scripts/dev.py` → `http://localhost:3001`.
- [ ] Lighthouse (opcional pero recomendado, dado que el propio proyecto
      se compromete a LCP < 1.5s, CLS 0, TBT 0):
      `npx lighthouse http://localhost:3001 --view`.

## Despliegue

1. Elegir **un** destino de hosting estático (Netlify, Cloudflare Pages,
   GitHub Pages o el que corresponda) — no hace falta dejar documentadas
   las cinco opciones que trae el README original (ver Fase 5).
2. Configurar la variable `SITE_URL` del build con el dominio real antes
   del primer deploy: todas las URLs absolutas (canonical, JSON-LD,
   sitemap, OG) se generan a partir de ahí.
3. Comando de build: `./scripts/build.sh`. Carpeta a publicar: `dist/`.
4. Tras el primer deploy: validar en Google Search Console
   (`sitemap.xml`) y en el [Rich Results Test](https://search.google.com/test/rich-results)
   que el `@graph` de JSON-LD se interpreta sin errores.

## Hecho el plan

Cuando este checklist esté completo, Legible es una web de negocio real,
desplegable, sin huecos entre lo que promete el validador y lo que
contienen las páginas, y con un repo que cualquiera puede entender leyendo
`README.md` + `docs/plan/00-resumen.md` en diez minutos.
