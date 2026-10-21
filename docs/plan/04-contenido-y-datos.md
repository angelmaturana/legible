# Fase 4 — Contenido y datos del negocio

> Depende de: Fase 3 (sin eso, cualquier contenido que se escriba se sigue
> validando contra un build roto).

## Objetivo

`src/data/entity.json` es la única fuente de verdad: nombre, dominio,
email, teléfono, ciudades, catálogo de servicios y precios. Rellenarlo con
los datos reales del negocio y dejar que el build los propague —así es
como está diseñado el generador, no hay que tocar plantillas para esto.

## Pasos

1. **`entity.json`**: sustituir cada placeholder (`{{site_name}}`,
   `Ciudad 1`...`4`, `Servicio 1`...`6`, precios, `priceRange`,
   `contactPoint.telephone`, dirección) por el dato real. El build
   (`_unwrap_placeholder`) usa estos valores para rellenar `{{site_name}}`,
   `{{contact_email}}`, `{{whatsapp_link}}`, las categorías de servicio,
   etc. en todas las páginas y en `llms.txt` automáticamente.
2. **Página de precios y de servicios**: una vez el catálogo de
   `entity.json` refleja los servicios reales, actualizar las tarjetas de
   `src/pages/servicios/index.html` y la tabla de
   `src/pages/precios/index.html` para que coincidan 1:1 (el validador
   compara duplicados de título/descripción entre páginas indexables, así
   que conviene revisar que cada texto sea distinto).
3. **Servicio genérico → servicios reales**: por cada servicio del
   catálogo, duplicar `src/pages/servicios/servicio-generico/` en
   `src/pages/servicios/<slug-del-servicio>/` y escribir su contenido
   (`@id`, `name`, `serviceType`, `offers.price`, FAQ, ≥250 palabras en
   `<main>` tal como exige el validador).
4. **Navegación**: añadir los nuevos servicios al submenú de
   `header.html` y a la lista de `footer.html`.
5. **Imágenes**: sustituir los placeholders de `src/static/images/`
   (logo, `og-image`, favicon) por los activos reales del negocio,
   manteniendo las mismas dimensiones para no romper `width`/`height`
   (CLS).
6. **Textos cortos del front matter**: revisar `description` en cada
   página — el validador ya ha señalado descripciones demasiado cortas
   (`index.html`, `servicio-generico`) o demasiado largas
   (`precios`, `servicios`, `sobre-nosotros`); el rango objetivo es
   ~120–160 caracteres.
7. **Contenido mínimo**: las páginas que el validador marcó con "poco
   contenido en `<main>`" (`accion-destacada`, `contacto`, `precios`,
   `sobre-nosotros`) necesitan ≥250 palabras reales una vez resuelto el
   bug de la Fase 3 — antes del fix, el validador ni siquiera llegaba a
   contarlas bien.
8. **Enlaces contextuales**: `sobre-nosotros` no tiene ningún enlace de
   entrada desde el `<main>` de otra página indexable; añadir al menos
   uno (por ejemplo desde `index.html` o `servicios/index.html`).

## Criterio de hecho

- `grep -r "{{" src/data/entity.json` no devuelve nada.
- `./scripts/build.sh` pasa sin avisos de contenido (no solo sin errores).
- Cada servicio del catálogo tiene su propia página, enlazada desde nav,
  footer, `servicios/index.html` y `precios/index.html`.
