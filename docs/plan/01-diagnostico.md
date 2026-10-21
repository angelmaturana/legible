# Fase 1 — Diagnóstico

> Resultado de ejecutar el proyecto tal cual se entregó. Todo lo de aquí es
> reproducible con `./scripts/build.sh` desde la raíz del proyecto.

## 1. El motor funciona

`python3 scripts/build.py --minify true` genera las 11 páginas, el CSS
minificado (respetando `calc()/clamp()`), `sitemap.xml` y `llms.txt` sin
errores. El pipeline en sí —parseo de front matter, fusión de JSON-LD
`@graph`, minificadores, generación de sitemap— está bien construido y no
necesita cambios de fondo.

Lo que falla es **el validador estricto** (`check_site.py --strict`), que
es justamente la pieza diseñada para detectar que el contenido todavía no
está listo para producción. Está haciendo su trabajo correctamente.

## 2. Bug de verdad: JSON-LD roto en 4 páginas

En `src/pages/accion-destacada/`, `contacto/`, `precios/` y
`sobre-nosotros/`, la etiqueta de apertura del bloque de datos
estructurados le falta la comilla de cierre:

```html
<script type="application/ld+json>   <!-- falta la comilla final -->
```

en vez de

```html
<script type="application/ld+json">
```

Efecto en cadena: la expresión regular de `build.py` que busca
`<script type="application/ld+json">...</script>` no reconoce el bloque,
así que **no lo extrae del contenido**. El JSON-LD se cuela como texto
dentro de `<main>`, lo que rompe el parseo de `check_site.py` en esas
páginas: por eso reporta "0 `<h1>`" y "página indexable sin JSON-LD"
aunque el `<h1>` y el JSON-LD sí existen en el fichero fuente. Un único
carácter por fichero, cuatro ficheros.

## 3. Enlaces a `/guias/` que no existen

`header.html`, `footer.html` y `src/pages/index.html` enlazan de forma
permanente a `/guias/` y a tres guías de ejemplo
(`/guias/guia-ejemplo-1/`, `-2/`, `-3/`). El proyecto, tal como se
entrega, **no trae `src/pages/guias/`**: la carpeta no existe. Resultado:
10 enlaces internos rotos repartidos por casi todas las páginas. Esto no
es contenido por rellenar, es una referencia a algo que el generador
soporta (la colección de Guías) pero que la plantilla no incluye.

## 4. Otros tres problemas puntuales

- **`servicios/index.html`**: el texto visible de las preguntas frecuentes
  no coincide carácter a carácter con el `FAQPage` del JSON-LD (el
  validador lo exige así porque Google penaliza el *FAQ cloaking*).
- **`servicios/servicio-generico/index.html`**: 4 anclas (`href="#algo"`)
  apuntan a secciones que no existen en la página.
- **`accion-destacada/`, `precios/`, `sobre-nosotros/`**: anclas internas
  rotas (mismo tipo de problema, consecuencia parcial del bug del punto 2).

## 5. Lo que no es un bug: contenido pendiente

`entity.json` todavía tiene los placeholders de fábrica
(`{{site_name}}`, `Ciudad 1`, `Servicio 1`...). Es intencionado —es la
plantilla genérica tal como la documenta el propio README— y se resuelve
en la fase 4, no aquí.

## Resumen para quien venga después

| Hallazgo | Tipo | Bloquea el build estricto |
|---|---|---|
| Comilla que falta en 4 `<script type="application/ld+json">` | Bug | Sí |
| Enlaces a `/guias/` sin colección creada | Gap estructural de la plantilla | Sí |
| FAQ visible ≠ FAQ en JSON-LD (servicios) | Bug de contenido | Sí |
| Anclas rotas (servicio-generico y 3 páginas más) | Bug de contenido | Sí |
| `entity.json` con placeholders | Pendiente de configurar, no bug | Sí (indirectamente) |
