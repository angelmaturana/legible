# ESTATUS del plan de robustez de `legible` (documento vivo)

> **Para la IA que ejecute la siguiente fase:** el punto de entrada es `PLAN_ROBUSTEZ_legible.md` (el plan completo); este fichero dice qué está hecho y qué falta. **`AGENTS.md` NO es tu guía de trabajo:** está escrito para una IA que usa `legible` para *crear un sitio* y ahí prohíbe editar `legible/` y `tests/`, que es justo lo que este plan manda hacer. Consúltalo solo como referencia de reglas del proyecto (no dependencias, no JS, no debilitar tests, no Git), y lee `DOCUMENTATION.md` secciones 0.1, 2 y 7.3 como pide el plan. **No modifiques `AGENTS.md`.** Al acabar tu fase, edita las secciones 1, 2, 3, 5 y 6 (no reescribas el historial: añade). Todo el código, tests y entradas del CHANGELOG, en inglés.

## 1. Resumen de fases

| Fase | Contenido | Hallazgos | Estado |
|---|---|---|---|
| 0 | Reconocimiento | – | ✅ Hecha |
| 1 | Marcadores y escapado en `build.py` | H1, H2, H7 | ✅ Hecha (sin commit, sin versión) |
| 2 | Fechas coherentes (`updated` vs `dateModified`) | H3 | ✅ Hecha (sin commit, sin versión) |
| 3 | Windows en `check_site.py` y vigilante de `dev.py` | H4, H8 | ✅ Hecha (sin commit, sin versión) |
| 4 | Barrido pre-lanzamiento y `bundle_price` | H5, H6 | ✅ Hecha (sin commit, sin versión) |
| 5 | `SITE_URL` (opcional) | H9 | ✅ Hecha: 5.1 sí, 5.2 opción **B** (solo avisar) |
| 6 | Cierre: DOCUMENTATION, README, CHANGELOG, verificación completa | – | ✅ Hecha (sin commit, sin versión) |

**Plan completado.** Solo quedan decisiones del propietario (sección 6): Git/versión y prueba en Windows.

## 2. Entorno y línea base (actualizar tras cada fase)

- Python usado: **3.13.17** (el plan se escribió con 3.12.3). Sintaxis comprobada compatible con 3.8 (`ast.parse(feature_version=(3,8))`) en `legible/*.py` y `tests/test_legible.py`.
- Línea base inicial (Fase 0): 119 tests `OK`; `SITE_URL=https://example.com ./legible/build.sh` → `PASSED`, 11 páginas, sin warnings. Coincide con la sección 2 del plan.
- **Estado actual (tras Fase 1): 124 tests `OK`**; build estricto `PASSED`, 11 páginas, `No issues`, `No warnings`; `bash -n legible/build.sh` OK.
- **Estado actual (tras Fase 2): 127 tests `OK`** (124 + 3); build estricto `PASSED`, `CHECK PASSED`, `No issues`, `No warnings`; `bash -n legible/build.sh` OK; `build.py` y `tests/test_legible.py` siguen siendo sintaxis compatible con 3.8 (`ast.parse(feature_version=(3,8))`). `sitemap.xml`: `sample-service` con `lastmod` 2026-10-20.
- **Estado actual (tras Fase 3): 127 tests `OK`** (sin tests nuevos, como indica el plan); build estricto `PASSED`, `CHECK PASSED`, `No issues`, `No warnings`; `bash -n legible/build.sh` OK; `check_site.py` y `dev.py` compatibles con sintaxis 3.8.
- **Estado actual (tras Fase 4): 127 tests `OK`** (sin tests nuevos: la fase es documentación y un dato de muestra); build estricto `PASSED`, `CHECK PASSED`, `No issues`, `No warnings`.
- **Estado final (tras Fases 5 y 6): 130 tests `OK`** (127 + 3); build estricto `PASSED`, `CHECK PASSED`, `No issues`, `No warnings`; `bash -n` OK; sintaxis 3.8 OK; `AGENTS.md` intacto; `src/` sin cambios en las Fases 5 y 6.
- Sin Git en el entorno (no es un repo): no se ejecutó ningún comando Git ni se cambió la versión.

## 3. Fase 1: qué se hizo exactamente

Solo se tocaron `legible/build.py` y `tests/test_legible.py`.

### `legible/build.py`
| Cambio | ID |
|---|---|
| Nuevo helper `_apply_markers(text, table, passes=5)`, definido justo antes de `_replace_placeholders_in_json`. Repite la sustitución hasta que el texto no cambia (máx. 5 pasadas). | H2 |
| Sustituidos por `_apply_markers` los 6 bucles `replace(placeholder, value)`: rama `str` de `_replace_placeholders_in_json`; `apply` en `replace_placeholders_in_content` (ahora `apply = _apply_markers`); `title_raw`/`description_raw` y `jsonld_str` en `compose_page` (este último con la tabla `{k: _json_str(v) ...}`); `robots_text` y `llms_text` en `build()`. | H2 |
| `'{{target_audience}}': target_audience` añadido al dict `derived` (primera entrada). Pasa por el escapado HTML y JSON como el resto. | H1 |
| Se **mantiene** el parámetro `target_audience` de `compose_page` y su `page.replace(...)` final (ahora redundante pero inofensivo; el plan prohíbe tocar la firma). | H1 |
| Comprobación tras `area_served = business.get('areaServed', [])`: si alguna entrada no es objeto → `sys.exit('✗ BUILD FAILED: src/data/entity.json: every areaServed entry must be an object such as {"@type": "City", "name": "Your City"}')`. | H7 |
| Mensaje de `check_unrendered` ampliado (la frase original queda intacta) con: `If it is a derived marker (DOCUMENTATION.md section 7.1), fix its source in src/data/entity.json or src/data/site.json instead.` | H7 |

### `tests/test_legible.py` (+5 tests, 119 → 124)
| Test | Clase | ¿Falla antes del arreglo? |
|---|---|---|
| `test_a_text_can_reference_an_earlier_text` | `TestMarkers` | Sí (`marker {{nest_a}} ... has no value`) |
| `test_circular_text_references_still_fail_cleanly` | `TestMarkers` | **No, pasa antes y después**: es un test de guarda (fija el comportamiento que el plan exige conservar), no de reproducción |
| `test_area_served_as_plain_strings_fails_with_a_clear_message` | `TestMarkers` | Sí (`AttributeError` / traceback) |
| `test_missing_free_offer_points_to_entity_json` | `TestMarkers` | Sí (faltaba `derived marker`) |
| `test_area_served_with_special_characters_is_escaped` | `TestSpecialCharactersAndWarnings` | Sí (el pie salía con `Rock & Roll <City>` sin escapar) |

Se añadieron 4 helpers privados a `TestMarkers` (`_write_texts`, `_use_marker_in_about`, `_edit_entity`, `_business`); los tests nuevos de `TestMarkers` los reutilizan. El de caracteres especiales edita `entity.json` directamente.

### Verificación realizada
1. Con los tests nuevos y el código **sin** arreglar: 4 fallos de 5 (ver tabla).
2. Con los arreglos: `python3 -B -m unittest discover tests` → `Ran 124 tests ... OK`.
3. `SITE_URL=https://example.com ./legible/build.sh` → `PASSED`, `No issues`, `No warnings`, 11 páginas.
4. Inspección de `dist/index.html`: el pie dice `We help businesses in City 1, City 2, City 3 get clear...` (sin cambios en la muestra).
5. Se borraron `dist/` y `__pycache__` antes de empaquetar.

## 3b. Fase 2: qué se hizo exactamente

Se tocaron `legible/build.py`, `tests/test_legible.py` y (única edición permitida en `src/` para esta fase) `src/pages/services/sample-service/index.html`.

| Cambio | ID |
|---|---|
| `build_sitemap` (`legible/build.py`): justo antes de `entries[rel] = lm`, `upd = front.get('updated')`; si `upd and upd != lm` → `ValueError` con el mensaje del plan (nombra la página y ambas fechas). `build()` ya captura `ValueError` de esta función: sin traceback. Las páginas generadas (índices) no llevan `updated` y quedan exentas. | H3 |
| `sample-service/index.html`: añadido `updated: 2026-10-20` al front matter (tras `canonical: auto`). Verificado antes: su `dateModified` es `2026-10-20`. | H3 |

### `tests/test_legible.py` (+3 tests, 124 → 127), nueva clase `TestSitemapDates`
| Test | ¿Falla antes del arreglo? |
|---|---|
| `test_updated_and_json_ld_date_mismatch_fails_the_build` | Sí (el build pasaba con sitemap desfasado) |
| `test_matching_dates_pass` | **No, pasa antes y después**: test de guarda (la plantilla tal cual construye y emite `lastmod`) |
| `test_sample_service_has_updated` (`ONLY_TEMPLATE`) | Sí (faltaba `updated`) |

### Verificación realizada
1. Copia con el código y la muestra originales + tests nuevos: 2 fallos de 3 (ver tabla).
2. Con los arreglos: `python3 -B -m unittest discover tests` → `Ran 127 tests ... OK`.
3. `SITE_URL=https://example.com ./legible/build.sh` → `PASSED`, `No issues`, `No warnings`.
4. Todas las páginas de la muestra con `updated` ya coincidían con su `dateModified` (el build estricto no falla).
5. Se borraron `dist/` y `__pycache__` antes de empaquetar.

## 3c. Fase 3: qué se hizo exactamente

Solo se tocaron `legible/check_site.py` y `legible/dev.py`. Sin tests nuevos (el plan dice que H8 no admite test razonable y H4 no se puede reproducir en Linux).

| Cambio | ID |
|---|---|
| `check_links` (`check_site.py`, líneas ~518 y ~522): las 2 claves `str(target.relative_to(out))` pasan a `target.relative_to(out).as_posix()`. La de `run_checks` (~641) ya usaba `.replace('\\', '/')` y no se toca. | H4 |
| `watch_src` (`dev.py`): el recorrido inicial protege cada fichero con `try/except OSError`; el cuerpo del `while True` (los tres recorridos) va dentro de `try/except OSError: pass`, con `callback()` y `sleep` fuera. Solo se captura `OSError` (no añade `except` genéricos: el grep de la Fase 6 sigue dando solo los 2 de `get_git_info`). | H8 |

### Verificación realizada
1. V1: `Ran 127 tests ... OK`; `SITE_URL=https://example.com ./legible/build.sh` → `PASSED`, `CHECK PASSED`, `No issues`, `No warnings`.
2. H4: simulación con `PureWindowsPath`: clave antigua `services\sample-service\index.html`, nueva `services/sample-service/index.html`. **No ejecutado en Windows.**
3. H8 (manual): `dev.py --port 3917`, 150 ciclos `touch`/`rm` de `src/pages/.xN.swp`, luego edición de `about/index.html` → el log muestra un segundo `Build OK`. Se restauró la página (diff contra el zip: solo difieren `check_site.py` y `dev.py`). Nota: el watcher también funcionaba antes en Linux en esta prueba; la carrera original es probabilística y no se reprodujo, así que esta prueba demuestra que el arreglo no rompe la recarga, no que cierre la carrera.
4. Se borraron `dist/`, `.dev-dist/` y `__pycache__` antes de empaquetar.

## 3d. Fase 4: qué se hizo exactamente

Sin cambios en el motor ni en los tests.

| Cambio | ID |
|---|---|
| `README.md` ("Before launch") y `DOCUMENTATION.md` 7.4: el comando de barrido pasa a ser **idéntico** en ambos, entre **comillas simples**, con `\$(49\|55\|99\|149\|229\|290\|299\|490)\b`, `09:00`, `19:00`, `9am`, `7pm`, `business day`, `business hours`, `addressCountry`, `priceCurrency`. | H5 |
| `DOCUMENTATION.md` 7.4: frase ampliada (horarios, plazos, límites, moneda y país; revisar todos a la vez; aviso de que con comillas dobles los patrones de precio no encuentran nada). | H5 |
| `DOCUMENTATION.md` 5.3 invariante 10: añadida la nota sobre horarios/plazos/límites repartidos por varios ficheros y `openingHoursSpecification`. | H5 |
| `src/data/texts.json`: `bundle_price` `$349` → `$229` (< $99 + $149 = $248). | H6 |

### Verificación realizada
1. Reproducido antes: `grep -rIlE "\$(99|149|290)" dist` (comillas dobles) → sin ficheros; con comillas simples → `featured-action`, `services`, `sample-service`.
2. `grep -n "349"` en tests, README, DOCUMENTATION: nada dependía del valor (solo coincidencia en `logo.svg`, datos de un path).
3. V1: `Ran 127 tests ... OK`; build estricto `PASSED`, `No issues`, `No warnings`.
4. Barrido nuevo sobre `dist src`: hay hits para `$229`, `$55`, `$299`, `$490`, `9am` y `addressCountry`. El comando literal de 7.4 extraído del fichero y ejecutado con `eval` da 194 líneas; ya no queda ninguna versión con comillas dobles.
5. `dist/services/index.html` muestra el paquete a `$229`.

## 3e. Fases 5 y 6: qué se hizo exactamente

| Cambio | ID |
|---|---|
| `build.py`: `SITE_URL = (os.environ.get('SITE_URL') or SITE_CONFIG.get('site_url', '')).strip().rstrip('/')`: un `SITE_URL` vacío usa `site.json`. | H9 (5.1) |
| `build.sh`: tras la validación, si `dist/robots.txt` contiene `YOUR-DOMAIN`, imprime `WARNING` por stderr y sigue (exit 0). Sin variables nuevas. | H9 (5.2 B) |
| Tests nuevos (+3, 127 → 130): `TestDomain.test_empty_site_url_falls_back_to_site_json` (falla antes), `TestCommandLine.test_build_script_warns_when_the_sample_domain_is_used` (`ONLY_TEMPLATE`, falla antes), `test_build_script_does_not_warn_with_a_real_domain` (guarda: pasa antes y después). | H9 |
| `DOCUMENTATION.md`: 2.4 (SITE_URL vacío; marcadores en hasta 5 pasadas, circulares fallan), 2.5 y 3.2 (`target_audience` derivado escapado, usable en `robots.txt`/`llms.txt`, `areaServed` = objetos), 3.3 (`updated`/`dateModified`/`last_update`), 7.5 (aviso de `YOUR-DOMAIN`). | Fase 6 |
| `README.md`: 130 tests; nota de `SITE_URL` vacío y aviso. | Fase 6 |
| `CHANGELOG.md`: decisión del propietario = **corregir 1.0.0**: entradas `### Fixed` **dentro de la sección `[1.0.0]`**, sin `**Breaking:**` (nadie usó aún 1.0.0); recuento de tests 130. `[Unreleased]` queda vacío. | Fase 6 |

Verificación de la Fase 6: tests, build estricto, `bash -n`, `grep` de `except` (solo los 2 de `get_git_info`), `target="_blank"` sin salida, `check_site.py --dir /nonexistent` → `exit=1`, inspección de `dist/` (lastmod 2026-10-20 en `sample-service`, pie, `robots.txt`, `llms.txt` con el dominio pasado).
**Nota sobre V3:** el grep de la Fase 6 *no* queda sin salida: da `PerplexityBot` en `src/static/robots.txt`, `{{geo}}` en `layout.html` y `geo: true/false` en el front matter de las páginas. Son funcionalidades del motor (documentadas) y ya estaban antes; no se tocaron.

## 4. Lo que NO se ha tocado (para que la siguiente fase no lo dé por hecho)

- `AGENTS.md` sin modificar (es para sitios, no para este plan).
- `CHANGELOG.md` sin modificar; `README.md` y `DOCUMENTATION.md` solo tocados en el barrido y 5.3 (Fase 4). El resto es Fase 6. En concreto:
  - Falta la entrada `### Fixed` de la Fase 4 (H5, H6) en el CHANGELOG, en inglés.
  - README ("Features at a glance") y CHANGELOG siguen diciendo **119 tests**; ahora son **127**.
  - Falta la entrada `### Fixed` de la Fase 1 en `## [Unreleased]` (H1, H2, H7), en inglés.
  - Falta la entrada `### Fixed` de la Fase 2 (H3), en inglés, con prefijo **`**Breaking:**`**: un sitio con `updated` distinto del `dateModified` que antes compilaba ahora falla.
  - Falta en DOCUMENTATION 3.3: el `lastmod` sale del `dateModified` del JSON-LD si existe, o de `updated` si no; si existen ambos deben coincidir o el build falla; `last_update` de `texts.json` es un tercer valor independiente que se actualiza a mano.
  - Falta documentar en DOCUMENTATION 2.4/3.1 (textos que referencian textos, hasta 5 pasadas, circulares fallan) y 2.5/3.2 (`{{target_audience}}` ya es derivado escapado y usable en `llms.txt`/`robots.txt`).
- `src/` solo tocado en `sample-service/index.html` (Fase 2) y `texts.json` `bundle_price` (Fase 4). No quedan más ediciones permitidas en `src/`.
- Versión sin cambiar.

## 5. Notas para las siguientes fases

- **Fase 2 (hecha):** `dateModified` real de `sample-service` = `2026-10-20`, coincide con el plan. Recuerda anotar `**Breaking:**` en el CHANGELOG (Fase 6).
- Los tests de la Fase 4 que toquen `bundle_price` no deben depender de `$349` (el plan comprueba con `grep -n "349" tests/test_legible.py README.md DOCUMENTATION.md`).
- **Fase 3 (hecha):** pedir al propietario que ejecute V1 en Git Bash/Windows (H4 sin probar allí).
- **Fase 4 (hecha):** el comando de barrido es idéntico en README y DOCUMENTATION 7.4. En Fase 6 no lo reformatees (comillas simples). El nº de tests de README sigue pendiente (127).
- Los tests nuevos usan `ONLY_TEMPLATE` solo si dependen de los datos de muestra; los de la Fase 1 no lo necesitan porque editan `entity.json` en una copia temporal (si en el futuro el sitio deja de ser plantilla, la búsqueda de la oferta a precio 0 y de `areaServed` sigue funcionando mientras existan esos campos).
- Tests con salida enorme: si un `assertIn` sobre `index.html` falla, el mensaje vuelca todo el HTML. Para depurar usa `-k nombre_del_test` y redirige a fichero.

## 6. Decisiones pendientes del propietario (acumulado)

1. **Fase 5 (H9):** ¿se hace? Si sí, ¿opción A, B o C para `YOUR-DOMAIN.com` (ver plan)?
2. **Versión a publicar** (Fase 6): corregir 1.0.0, publicar 1.0.1 o 2.0.0. El cambio de la Fase 2 hace fallar sitios que antes compilaban (MAJOR según las reglas del CHANGELOG).
3. Si publica como parte de 1.0.0, actualizar el recuento de tests del CHANGELOG (hoy 127, no 119).

## 7. Hallazgos extra

**Resueltos tras el cierre (a petición del propietario):** mensaje de `check_unrendered` ahora dice "first found on page …" (el marcador está de verdad en `/404.html`, pero puede estar en más páginas); eliminados el `page.replace('{{target_audience}}', …)` redundante y el parámetro `target_audience` de `compose_page` (y de sus 2 llamadas). CHANGELOG: el grupo pasa a `### Added`.

Histórico (ya no pendiente):

- El mensaje de `check_unrendered` para `{{featured_action_name}}` cita la página `/404.html` (la primera que se compone), no necesariamente donde el propietario lo usa. Es cosmético y no está en el plan.
- Tras la Fase 1, la línea `page.replace('{{target_audience}}', target_audience)` de `compose_page` es código muerto en la práctica; se deja por la instrucción de no cambiar la firma.

## 8. Limitaciones de verificación (acumulado)

- H4 (`as_posix`) solo simulado con `PureWindowsPath`; H8 (carrera de ficheros) no reproducible, solo comprobado que la recarga sigue funcionando.
- No ejecutado en Windows ni en Python 3.8–3.12 / 3.14 (solo 3.13.17 real; 3.8 solo por análisis de sintaxis).
- No probado en navegador.
