# Problemas e Impedimentos - TechFlow Blog
Fecha: 2026-11-01

## Tests Fallando (8 fallos, 7 omitidos)

### Causa Raíz
Los tests en `tests/test_legible.py` están diseñados para la **plantilla original** (negocio de servicios locales con precios), no para un blog. El motor `legible` no se adapta al tipo de sitio; los tests validan la plantilla base.

### Tests que Fallan

| Test | Qué Valida | Por Qué Falla en Blog |
|------|------------|------------------------|
| `TestTargetAudienceLocale.test_english_keeps_the_same_phrase` | Frase "We help businesses in..." en footer | Blog no usa `areaServed` en entidad Organization |
| `TestTargetAudienceLocale.test_spanish_site_gets_a_spanish_phrase` | Frase traducida al español | Idem |
| `TestTargetAudienceLocale.test_the_phrase_can_be_overridden_per_site` | Override de `target_audience` | Idem |
| `TestGeo.test_geo_comes_from_business_data_not_a_fixed_value` | Meta tags geo desde `city` en business | Blog no tiene `city` en Organization |
| `TestMarkers.test_missing_free_offer_points_to_entity_json` | Oferta precio 0 en `hasOfferCatalog` | Blog no tiene `hasOfferCatalog` |
| `TestSpecialCharactersAndWarnings.test_area_served_with_special_characters_is_escaped` | Escape de chars en `areaServed` | Blog no usa `areaServed` |
| `TestSpecialCharactersAndWarnings.test_empty_price_range_is_not_published_in_json_ld` | `priceRange` no se publica si vacío | Blog no tiene `priceRange` |
| `TestSampleFallbacks.test_strict_mode_fails_on_a_published_sample_value` | Valores sample en ofertas | Blog no tiene ofertas |

### Tests Omitidos (7)
- `@ONLY_TEMPLATE` marcados: solo válidos para plantilla original

---

## Impedimentos Actuales

### 1. Arquitectura del Motor (Fuera de Alcance)
- **Motor fijo:** `legible/` no se modifica (AGENTS.md sección 2, 7)
- **Tests fijos:** `tests/` no se modifican (AGENTS.md sección 8, regla 3)
- **Conclusión:** No se pueden adaptar tests al tipo de sitio sin entrar en "Engine mode" (requiere confirmación explícita y resolver necesidad real)

### 2. Datos Pendientes de Confirmar (Pending Confirmation)
| Dato | Dónde Aparece | Acción |
|------|---------------|--------|
| `phone_e164: +15550100` (sample) | site.json, entity.json | Sustituir por real o eliminar |
| `addressCountry: US` (sample) | entity.json | Ya corregido a ES |
| `priceCurrency: USD` (sample) | entity.json | Ya corregido a EUR |
| Legal name, tax ID, registered address | legal-notice.html | Valores inventados puestos como placeholder |
| Sample copy en páginas blog | category/*.html, index.html | Marcar `<!-- SAMPLE COPY -->` |

### 3. Funcionalidades en "Later" (Fuera del Base)
- Páginas de artículos individuales (blog posts)
- Búsqueda
- Newsletter signup
- RSS feed
- Sistema de comentarios (requiere backend)
- Imágenes reales (logo, favicon, og-image)

### 4. Configuración de Despliegue (Fuera del Proceso)
- Hosting, DNS, CI/CD no gestionados por legible
- `SITE_URL` debe configurarse en CI antes de publicar

---

## Posibles Mejoras Futuras (Si Se Decide Entrar en Engine Mode)

> **Nota:** Requiere confirmación explícita "engine mode" + cambio nombrado (AGENTS.md sección 7). Solo si la necesidad no se puede resolver desde `src/`.

1. **Soporte multi-tipo de entidad en tests**
   - Detectar `@type` en entity.json (Blog vs ProfessionalService vs Project)
   - Ejecutar subset de tests relevante al tipo

2. **Validador adaptable**
   - Checks condicionales según `@type` del negocio
   - No exigir `hasOfferCatalog` para Blog/Portfolio

3. **Colección Blog nativa**
   - Páginas `blog/<slug>/index.html` con front matter específico
   - Índice automático en `/blog/` (ya generado por motor)

4. **Tests parametrizados por fixture**
   - Fixture `site_type: blog|service|project|portfolio`
   - Tests compartidos + tests específicos por tipo

---

## Decisiones Tomadas

| Decisión | Justificación |
|----------|---------------|
| No modificar tests | AGENTS.md: "Never weaken tests or validator rules"; tests validan plantilla base |
| No entrar en Engine Mode | No hay necesidad que `src/` no resuelva; blog funciona y valida |
| Valores sample mantenidos | Usuario no los proporcionó; se listan en Pending Confirmation |
| Base look mantenido | Usuario dijo "base look"; fases 3,4,6 marcadas "not needed" |

---

## Próximos Pasos Recomendados

1. **Usuario proporciona datos reales** → Actualizar Pending Confirmation
2. **Usuario quiere artículos reales** → Crear `src/pages/blog/<slug>/index.html`
3. **Usuario quiere assets de marca** → Fase 6: generar logo.svg, favicon.svg, og-image.png
4. **Usuario quiere desplegar** → Configurar `SITE_URL` en CI, build command `./legible/build.sh`, publish dir `dist/`