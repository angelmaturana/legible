# legible

Generador de webs estáticas para negocios de servicios locales. Python 3 sin dependencias, HTML semántico, sin JavaScript, con datos estructurados (Schema.org) y un validador SEO que corta el build si algo falla.

Hace tres cosas:

1. **Compone** las páginas de `src/` (layout + cabecera + pie + contenido) y las escribe en `dist/`.
2. **Genera** `sitemap.xml`, `llms.txt` y, si existen, los índices de `/guias/` y `/blog/`.
3. **Valida** el resultado con `check_site.py` y falla si hay errores o avisos.

Origen: plantilla de [seovaldemoro.com](https://seovaldemoro.com). Licencia MIT.

---

## Uso rápido

Requiere Python 3.10+. No hay nada que instalar.

```bash
./scripts/build.sh            # compila en dist/ y valida (modo estricto)
python3 scripts/dev.py        # servidor local en http://localhost:3001, recompila al guardar
```

Variables de entorno de `build.sh`:

| Variable | Por defecto | Efecto |
|---|---|---|
| `SITE_URL` | `https://TU-DOMINIO.com` | Dominio del sitio (canonicals, JSON-LD, sitemap, `robots.txt`, `llms.txt`) |
| `CSS_MINIFY` | `TRUE` | `FALSE` deja CSS y HTML sin minimizar (útil para depurar) |
| `CHECK_STRICT` | `TRUE` | `FALSE`: los avisos de `check_site.py` no hacen fallar el build (los errores siempre sí) |

Pruebas (solo librería estándar, unos 5 segundos):

```bash
python3 -m unittest discover tests
```

Validar una carpeta ya compilada:

```bash
python3 scripts/check_site.py --dir dist --strict
```

`dev.py` compila en `.dev-dist/` (no toca `dist/`) y acepta `--port` y `--minify`.

---

## Qué hay en el proyecto

```
scripts/
  build.py        Generador: plantillas, JSON-LD, minificadores, sitemap, llms.txt, colecciones
  check_site.py   Validador de la salida compilada
  dev.py          Servidor local con recompilado al detectar cambios en src/
  build.sh        build.py (sin validar) + check_site.py --strict
tests/
  test_legible.py Pruebas: humo, minificadores, guías/blog, dominio y marcadores
src/
  layout.html     Plantilla base (head, meta, Open Graph, JSON-LD)
  partials/       header.html y footer.html
  pages/          Una carpeta por página, cada una con su index.html (+ 404.html)
  data/entity.json  Datos del negocio en JSON-LD (ProfessionalService + WebSite)
  data/textos.json  Textos por defecto de las páginas (clave → texto), uno por marcador {{clave}}
  css/site.css    Una sola hoja de estilos
  static/         Imágenes, robots.txt y llms.txt (plantilla), se copian tal cual
```

Páginas incluidas: inicio, servicios (índice + un servicio de ejemplo), precios, sobre nosotros, contacto, acción destacada, aviso legal, privacidad, cookies (estas tres `noindex`) y 404.

---

## Cómo funciona

**Plantillas.** Cada página es un `.html` con *front matter* (`title`, `description`, y opcionalmente `robots`, `canonical`, `geo`, `active`) y su contenido. El build lo inserta en `layout.html`, marca el enlace activo del menú con `aria-current` y añade canonical y Open Graph.

**Marcadores `{{...}}`.** El texto de las páginas usa marcadores (`{{site_name}}`, `{{service_1_price}}`...). Se resuelven así: unos se calculan desde `entity.json` (nombre, email, teléfono, ciudades, precios, servicios, dominio) y el resto son textos que escribes en `src/data/textos.json`. Si algo calculado y un texto comparten clave, gana lo calculado. Si queda un `{{...}}` sin valor, el build se detiene y te dice cuál es y en qué página.

**JSON-LD.** Los nodos de `entity.json` se combinan con el JSON-LD de cada página en un único `@graph`. Si una página repite un `@id` ya definido en `entity.json`, el build la deja sin JSON-LD en lugar de duplicar el nodo.

**Minificado.** Minificadores propios para CSS (respeta `calc()`, `clamp()`, `min()`, `max()`) y HTML (protege atributos, `<pre>`, `<textarea>` y JSON-LD).

**Sitemap y `llms.txt`.** `sitemap.xml` incluye las páginas indexables, con `lastmod` tomado del `dateModified` del JSON-LD (o de `updated` en el front matter). `llms.txt` se genera desde `src/static/llms.txt`.

**Guías y blog.** Si creas `src/pages/guias/<slug>/index.html` o `src/pages/blog/<slug>/index.html` con el front matter requerido (`type`, `topic`, `published`, `updated`, `summary`, `service`; `related` opcional, máx. 2), el build genera el índice, lo añade al sitemap y a `llms.txt`.
- `/guias/` aparece con 1 guía o más.
- `/blog/` sale `noindex` con 1–2 artículos y pasa a indexable (y al menú y pie) con 3 o más.
- Los temas válidos son los de `COLLECTION_TOPICS` en `build.py`.

---

## Qué valida `check_site.py`

Con `--strict`, los avisos también hacen fallar.

- **Cabecera:** `lang`, `viewport`, `title` y `description` (con longitudes), `robots`, canonical (HTTPS y coherente con la URL), Open Graph y Twitter.
- **Contenido:** un solo `h1`, sin saltos de nivel, mínimo de 250 palabras en `<main>` en páginas indexables, sin `TODO`, `[CONFIRMAR` ni `{{...}}`.
- **Imágenes:** `alt`, `width` y `height`.
- **Enlaces:** internos con ruta absoluta, sin enlaces ni anclas rotas, `rel="noopener"` en `target="_blank"`, `mailto:` y `tel:` bien formados, sin páginas huérfanas (se pide al menos un enlace desde el `<main>` de otra página).
- **JSON-LD:** válido, con `@context`, sin `@id` duplicados ni referencias sin definir, con los nodos `ProfessionalService` y `WebSite`; las FAQ del JSON-LD deben coincidir con las visibles.
- **Sitio:** títulos y descriptions no duplicados, `sitemap.xml` completo y coherente, `robots.txt` sin `Disallow: /` y con el sitemap declarado, archivos obligatorios presentes.

---

## Personalizar para un negocio

1. Edita `src/data/entity.json` (nombre, email, teléfono, ciudades, servicios, precios).
2. Define el dominio con la variable `SITE_URL` (debe empezar por `https://`): `SITE_URL=https://midominio.es ./scripts/build.sh`. Si no la pones, se usa `https://TU-DOMINIO.com`. Es el único sitio donde se escribe: páginas, `entity.json`, `robots.txt` y `llms.txt` usan el marcador `{{site_url}}`.
3. Sustituye los textos genéricos de `src/data/textos.json` (no hace falta tocar Python), o escribe el texto directamente en cada página.
4. Reemplaza las imágenes de `src/static/images/` (logo, `og-image`, favicon).
5. Para un servicio nuevo, copia `src/pages/servicios/servicio-generico/`, ajusta su front matter, JSON-LD y contenido, y enlázalo desde `servicios/`, `precios/`, `header.html` y `footer.html`.

Nota: la etiqueta `geo.placename` de `render_geo()` está fijada a «Valdemoro» (`geo.region` = `ES-MD`) y las páginas siguen en español.

---

## Despliegue

Es una salida estática: sirve `dist/` desde cualquier hosting estático (Render Static Site, Netlify, Cloudflare Pages, GitHub Pages, S3, Nginx...).

```
Build command:     ./scripts/build.sh
Publish directory: dist
```

---

## Estado actual

`./scripts/build.sh` pasa en modo estricto con la plantilla tal cual (con y sin `CSS_MINIFY=FALSE`). El enlace a Guías del menú y del pie solo aparece cuando existe al menos una guía.

Lo que falta, por orden, está en [`mejoras/`](mejoras/). `python3 -m unittest discover tests` pasa; incluye seis errores conocidos marcados como «expected failure» (cinco de `minify_css` y el primer índice de Guías/Blog en modo estricto, detallados en [`mejoras/05-pruebas-minimas.md`](mejoras/05-pruebas-minimas.md)). Todavía no hay `render.yaml`.

Nota: `check_site.py` es el único validador; `build.py` lo llama al terminar (salvo con `--no-validate`, que usa `build.sh` para validar después con el modo que toque). `check_site.py` importa `SITE_URL` y `get_git_info` de `build.py`.

---

## Licencia

MIT. Ver [LICENSE](LICENSE).
