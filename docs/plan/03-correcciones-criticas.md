# Fase 3 — Correcciones críticas ✅ hecha

> Depende de: Fase 1 (diagnóstico). Es la fase con más prioridad: hasta que
> no esté cerrada, `check_site.py --strict` no pasa y no hay build
> desplegable.
>
> **Estado:** aplicada. `./scripts/build.sh` pasa con **0 errores**; quedan
> 8 avisos de contenido (longitud de `description`, palabras en `<main>`,
> enlaces contextuales), que son objeto de la Fase 4, no de esta.

Cada punto referencia el hallazgo correspondiente en `01-diagnostico.md`.

## 3.1 Cerrar la comilla del JSON-LD (4 ficheros) ✅

Cambiado en los 4 ficheros:

- `src/pages/accion-destacada/index.html`
- `src/pages/contacto/index.html`
- `src/pages/precios/index.html`
- `src/pages/sobre-nosotros/index.html`

```diff
- <script type="application/ld+json>
+ <script type="application/ld+json">
```

Era la corrección de mayor impacto del plan: un carácter por fichero que
provocaba "0 `<h1>`" y "sin JSON-LD" en 4 de las 11 páginas. Confirmado:
tras el fix esos errores desaparecieron del todo.

## 3.2 Destino de `/guias/`: retiradas (opción B) ✅

Se optó por **retirar las referencias** en vez de inventar contenido de
guías para pasar el validador. Quitado de:

- `header.html` / `footer.html`: el enlace "Guías" del menú y del pie.
- `header.html`: de paso, el submenú de Servicios tenía 4 enlaces
  apuntando los cuatro al mismo `/servicios/servicio-generico/`
  (duplicado de fábrica); se simplificó a un único enlace "Servicios"
  hasta que la Fase 4 cree páginas de servicio reales y distintas —
  evita el error de "4 elementos con `aria-current`" sin inventar URLs.
- `src/pages/index.html`: la sección completa "Guías para tu negocio" y
  la mención a "las guías" en el bloque de zona.
- `src/pages/servicios/servicio-generico/index.html`: la sección
  "Guías relacionadas".
- `src/pages/accion-destacada/index.html`: los dos enlaces a guías de
  ejemplo en "Si prefieres empezar por tu cuenta".

Si en el futuro se quiere activar la colección de verdad, el generador ya
la soporta (`src/pages/guias/<slug>/index.html` con el front matter que
pide `build.py`); solo haría falta volver a enlazarla desde estos mismos
puntos.

## 3.3 FAQ visible = FAQ del JSON-LD ✅

No era un desajuste de texto: `servicios/index.html` y `contacto/index.html`
tenían un bloque `FAQPage` en el JSON-LD **sin ninguna sección de FAQ
visible en la página** (gap estructural, no error de contenido). Se añadió
en ambas el bloque `<details><summary>` con el texto exacto del JSON-LD,
siguiendo el mismo patrón que ya usaban `accion-destacada` y
`servicio-generico`.

## 3.4 Anclas y duplicados rotos ✅

Las 4 anclas inexistentes reportadas en `servicio-generico` y las de
`accion-destacada`, `precios` y `sobre-nosotros` eran consecuencia de los
puntos 3.1 (parseo roto por la comilla) y 3.2 (enlaces a `/guias/`); no
quedó ninguna ancla rota tras resolver ambos.

## Resultado

```
./scripts/build.sh   →   0 errores
```

Quedan 8 **avisos** de contenido (descripciones demasiado cortas/largas,
"poco contenido en `<main>`", un enlace contextual que falta en
`sobre-nosotros`) — eso es exactamente el trabajo de la Fase 4, no de
esta. Con `CHECK_STRICT=TRUE` (el modo por defecto) los avisos siguen
contando como fallo del build, así que el build limpio del todo llega al
cerrar la Fase 4.
