# Legible — plan de puesta a punto

> Índice de las fases. Cada fase tiene su propio fichero en esta carpeta
> (`docs/plan/`) para poder trabajarlas, revisarlas o encargarlas por
> separado sin perder el hilo del conjunto.

## Qué es este proyecto

Un generador de sitios estáticos para negocios de servicios: HTML semántico,
cero JavaScript, datos estructurados (Schema.org `@graph`) y un validador
propio (`check_site.py`) que rompe el build si algo de SEO no cuadra. Una
sola fuente de verdad (`src/data/entity.json`) alimenta todas las páginas
por sustitución de `{{placeholders}}`.

Es una base sólida y bien pensada —la lógica de build, el minificador que
respeta `calc()/clamp()`, la fusión de JSON-LD y el validador estricto son
piezas de calidad—, pero se entrega **a medio terminar**: el pipeline
funciona, el contenido y el naming no. Ese es exactamente el hueco que
cierra este plan.

## Por qué "Legible"

El nombre de trabajo original (`seo-web-generic`) describe la técnica, no
el producto. "Legible" describe el resultado que importa: una web que
tanto una persona como un buscador o una IA puedan leer sin fricción. Es
el nombre que va a quedar en el repo, en los textos de cabecera del build
y del validador, y en el README.

## Fases

| # | Fichero | Qué resuelve | Depende de |
|---|---------|--------------|------------|
| 1 | [`01-diagnostico.md`](01-diagnostico.md) | Estado real del proyecto: qué funciona, qué está roto, con evidencia reproducible | — |
| 2 | [`02-identidad-legible.md`](02-identidad-legible.md) ✅ | Rebautizar el proyecto: nombre, metadatos, textos de marca del propio generador | 1 |
| 3 | [`03-correcciones-criticas.md`](03-correcciones-criticas.md) ✅ | Arreglar los bugs que hoy impiden pasar `check_site.py --strict` | 1 |
| 4 | [`04-contenido-y-datos.md`](04-contenido-y-datos.md) | Rellenar `entity.json` y el contenido real del negocio | 3 |
| 5 | [`05-arquitectura-y-limpieza.md`](05-arquitectura-y-limpieza.md) | Simplificar lo que sobra (README promocional, colecciones sin usar) para que el repo sea legible por sí mismo | 3 |
| 6 | [`06-validacion-y-despliegue.md`](06-validacion-y-despliegue.md) | Build limpio, checklist final y despliegue | 2, 4, 5 |

## Principio guía

**Sencillo pero elegante, a la escala del proyecto.** Esto es una web de
8–10 páginas para un solo negocio, no una plataforma editorial. El plan no
añade infraestructura nueva: usa el `docs/plan/` que ya veis para ordenar
el trabajo, y en la fase 5 *retira* complejidad (secciones de README que
venden el generador a terceros, colecciones de Guías/Blog sin contenido)
en vez de añadir más. La arquitectura ya existente (entity.json → build →
validador) es la correcta para este alcance; no hace falta tocarla, solo
terminarla y limpiarla.
