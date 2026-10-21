# Fase 2 — Identidad "Legible"

> Depende de: Fase 1 (diagnóstico). No depende de las correcciones de la
> Fase 3 — es puro renombrado, se puede hacer en paralelo.

## Objetivo

Que el proyecto se llame y se presente como **Legible** en todos los
sitios donde hoy dice `seo-web-generic`, `Generic Site Generator` o
`TU-DOMINIO.com`, sin tocar la lógica del build.

## Dónde aparece el nombre viejo

| Fichero | Qué cambiar |
|---|---|
| `README.md` | Título, badges, toda referencia a `seo-web-generic` / `your-org` |
| `scripts/build.py` → `print_report()` | `BANNER = 'TU-DOMINIO.com  •  Static Site Generator'` → `'Legible  •  Static Site Generator'` |
| `scripts/check_site.py` → banner equivalente | `'Generic Site Generator  •  Site Checker'` → `'Legible  •  Site Checker'` |
| `src/data/entity.json` | Valor por defecto de `name` cuando no hay dato real (ver Fase 4) |
| `LICENSE` | Mantener la autoría MIT original de la plantilla (Angel Maturana Clavero) tal cual exige la licencia; añadir, si se desea, una nota de "basado en seo-web-generic" |
| Carpeta raíz del proyecto | Renombrar a `legible/` (ya hecho en esta entrega) |

## Qué NO cambia

- La licencia MIT original y su autoría: **se respeta** (es la condición
  del propio MIT). Legible es un fork/instancia personalizada, no una
  apropiación de autoría.
- Nombres internos de funciones, variables y comentarios en `build.py` /
  `check_site.py`: no aportan nada al renombrado y tocarlos solo añade
  riesgo de romper algo que ya funciona.

## Criterio de hecho

- `grep -ri "seo-web-generic\|TU-DOMINIO\|Generic Site Generator" -r src scripts README.md`
  no devuelve nada que debiera haberse cambiado (los placeholders de
  `entity.json` destinados a la Fase 4 son la única excepción esperada en
  este punto).
- El banner de `./scripts/build.sh` y el de `check_site.py --strict`
  muestran "Legible".
