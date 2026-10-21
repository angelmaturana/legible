# Fase 5 — Arquitectura y limpieza

> Depende de: Fase 3. Esta fase no añade nada nuevo: quita lo que sobra
> para que el proyecto sea tan legible como su nombre. Es la fase que
> responde directamente a "sencillo pero elegante para el alcance que
> tiene".

## Por qué hace falta

El `README.md` actual (650+ líneas) está escrito para vender
`seo-web-generic` como producto de código abierto a terceros: badges de
"Kilo Agent", una tabla comparativa contra otros generadores (Pelican,
Nikola...), un prompt completo para convertirlo en la web de un taller
mecánico, instrucciones de despliegue en Render con `render.yaml`. Nada de
eso es necesario para que Legible sea la web de un negocio concreto, y
sobrecarga lo que debería ser la referencia rápida del propio repo.

## Qué retirar o reducir

1. **`README.md`**: quedarse con lo que sirve a quien mantenga *esta* web:
   qué es, cómo se construye (`./scripts/build.sh`), cómo se edita el
   contenido (`entity.json`, cómo añadir un servicio), cómo se despliega
   (el hosting real que se vaya a usar, no los cinco posibles). Fuera:
   sección "Competitive Landscape", el prompt para Kilo Agent, los badges
   que no aplican, el despliegue a plataformas que no se van a usar.
2. **Colecciones Guías/Blog**: si en la Fase 3 se optó por **retirar**
   las referencias a `/guias/` (opción B) en vez de crear contenido, esta
   es la fase donde además se documenta esa decisión en el propio README
   (una línea: "Guías y Blog son colecciones opcionales del generador;
   esta instancia no las usa") para que quien vuelva al proyecto en seis
   meses no se pregunte por qué el código las soporta y la web no las usa.
3. **`scripts/dev.py`, `check_site.py`**: no tocar la lógica; solo
   confirmar que los nombres/banners quedaron coherentes con la Fase 2.

## Qué se mantiene tal cual (porque ya es la arquitectura correcta)

- `entity.json` como fuente única de datos del negocio.
- El validador estricto como puerta de calidad antes de desplegar.
- La estructura `layout.html` + `partials/` + `pages/` — separar cabecera,
  pie y plantilla base del contenido de cada página es exactamente el
  nivel de abstracción que pide un sitio de 8–10 páginas: ni una plantilla
  monolítica ni un framework de componentes de más.
- Cero JavaScript y CSS con tokens — coherente con el objetivo de
  rendimiento y con el alcance (sitio de negocio, no aplicación).

## Criterio de hecho

- `README.md` se puede leer de principio a fin en menos de 3 minutos y
  cualquier sección restante describe *este* proyecto, no el generador
  como producto genérico.
- La decisión sobre Guías/Blog está tomada y escrita en una línea del
  README, no implícita en el código.
