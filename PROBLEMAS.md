# PROBLEMAS E IMPEDIMENTOS - Bar Colon (legible)

## Estado actual
- **Rama**: test1 (origin/test1)
- **Estado del plan**: complete (example data: 3)
- **Fases completadas**: 10/10
- **Python3**: NO DISPONIBLE en el entorno - no se pueden ejecutar tests ni build

---

## 1. IMPEDIMENTOS CRÍTICOS (Bloquean verificación)

### 1.1 Python3 no disponible
- **Problema**: El entorno no tiene Python3 instalado
- **Impacto**: No se puede ejecutar:
  - `./legible/build.sh` (validación estricta, JSON-LD, sitemap, robots.txt, llms.txt)
  - `python3 -m unittest discover tests` (suite de regresión)
  - `python3 legible/dev.py` (servidor de desarrollo)
- **Solución**: Instalar Python3 en el entorno o usar un entorno con Python

### 1.2 Tests no ejecutados
- **Problema**: Sin Python, no se sabe si los tests pasan
- **Riesgo**: Los tests del template (@ONLY_TEMPLATE) pueden fallar con los datos adaptados
- **Acción pendiente**: Ejecutar tests cuando Python esté disponible y analizar fallos

---

## 2. PROBLEMAS CONOCIDOS EN EL SITIO (Pendientes de confirmación)

### 2.1 Horarios sin confirmar (Pendiente #1)
- **Dato**: "abre todos los días de 8 a 16 menos los miércoles"
- **Ubicación**: `site.json`, `texts.json`, `contact/index.html`, `entity.json` (openingHoursSpecification)
- **Estado**: Valor de ejemplo del usuario, no verificado oficialmente
- **Riesgo**: Si el horario real difiere, hay que actualizar en 4+ archivos

### 2.2 Datos legales nivel minimal (Pendiente #2)
- **Dato**: "Bar Colon SL" como razón social
- **Ubicación**: `legal-notice/index.html`, `privacy-policy/index.html`, `entity.json`
- **Estado**: Usuario dijo "nivel minimal" pero no confirmó CIF/NIF, escritura, registro mercantil
- **Riesgo**: Aviso legal incompleto si falta CIF o datos de inscripción registral

### 2.3 Brand assets de template (Pendiente #3)
- **Archivos**: `logo.svg`, `favicon.svg`, `og-image.png`, `apple-touch-icon.png`, `favicon.ico`
- **Estado**: Se usan los archivos del template base (genéricos)
- **Usuario**: Dijo "crea las imágenes de marca" pero no se generaron (falta herramienta de generación)
- **Riesgo**: Logo/favicon genéricos en producción

---

## 3. ADAPTACIONES NECESARIAS EN TESTS (Probables)

### 3.1 Tests @ONLY_TEMPLATE que fallarán
Basado en `DOCUMENTATION.md` sección 7.3, los tests marcados `@ONLY_TEMPLATE` leen datos de muestra del template y se saltan en sitios adaptados. Probables fallos:

| Test | Motivo probable de fallo |
|---|---|
| Tests que esperan "Your Business" | `site_name` ahora es "Bar Colon" |
| Tests que esperan "hello@example.com" | Email ahora es "barcolon@seovaldemoro.com" |
| Tests que esperan URLs /services/ | URLs ahora son /servicios/ (español) |
| Tests que esperan 5 servicios | Solo hay 1 servicio real |
| Tests que esperan USD | Moneda ahora es EUR |
| Tests que esperan precios > 0 | Servicios sin precio estructurado (precio 0) |

### 3.2 Tests de estructura de URLs
- `sitemap_base_order` cambió: URLs en español (/servicios/, /sobre/, /contacto/, /featured-action/)
- Tests que validan menú/navegación pueden esperar URLs en inglés

### 3.3 Tests de JSON-LD
- `entity.json`: `@type` FoodEstablishment (no LocalBusiness genérico)
- URLs de servicios: `/servicios/tapas-y-aperitivos/` vs `/services/sample-service/`
- `priceCurrency`: EUR vs USD
- `areaServed`: 4 ciudades específicas vs genéricas

---

## 4. PROBLEMAS DE CONTENIDO / ARQUITECTURA

### 4.1 Página de precios (/precios/)
- **Problema**: La página usa marcadores de 5 servicios + bundle + planes avanzados
- **Realidad**: Solo 1 servicio, sin precios estructurados, mención especial "tercio + tapa 2,5€"
- **Marcadores vacíos**: `service_2_price`, `service_3_price`, `bundle_price`, `growth_plan_price`, etc.
- **Build warning**: El build avisará por cada `Service N` sin reemplazar

### 4.2 Página home (index.html)
- **Marcadores de template**: `service_2_name`, `service_3_name`, `service_4_name`, `service_5_name`, `bundle_price`, `situation_2-5`
- **Contenido genérico**: `home_description` aún dice "Reliable, fairly priced local services..."
- **FAQ genéricas**: `faq_1_answer`, `faq_3_answer`, etc. hablan de "servicios para negocios" no de bar

### 4.3 texts.json - Marcadores huérfanos
Muchos campos de `service_2` a `service_5` vacíos pero referenciados en páginas:
- `service_2_short_description` through `service_5_short_description`
- `service_2_short_includes` through `service_5_short_includes`
- `bundle_price`, `bundle_description`
- `growth_plan_price`, `partner_plan_price`

### 4.4 entity.json - hasOfferCatalog
- Solo 1 offer en el catálogo (correcto)
- Pero `price`: "0" y `priceSpecification.price`: "0" - puede parecer precio gratis vs "consultar en bar"

### 4.5 Páginas legales - Placeholder legal name
- `legal-notice`: "Bar Colon SL" pero sin CIF/NIF, sin datos registrales
- `privacy-policy`: "Bar Colon SL" como responsable pero sin número de identificación fiscal

---

## 5. MEJORAS FUTURAS (Later - fuera del base)

### 5.1 Funcionalidades solicitadas en entrevista
- Blog/guías
- Calculadoras
- Reservas/booking
- Formularios con backend
- Mapas

### 5.2 Mejoras de contenido
- Fotos reales del local, tapas, frituras
- Carta completa con precios
- Testimonios/reseñas reales
- Horarios por temporada (verano/invierno)

### 5.3 SEO / Técnico
- Sitemap.xml y robots.txt se generan en build (verificar)
- llms.txt se genera en build (verificar)
- Meta tags Open Graph / Twitter cards (verificar en build)

---

## 6. ACCIONES REQUERIDAS PARA SIGUIENTE SESIÓN

### Prioridad ALTA (bloqueantes)
1. [ ] Instalar Python3 en el entorno
2. [ ] Ejecutar `./legible/build.sh` - ver errores/warnings reales
3. [ ] Ejecutar `python3 -m unittest discover tests` - ver tests que fallan
4. [ ] Corregir tests adaptados (NO debilitar tests, corregir contenido del sitio)

### Prioridad MEDIA (datos pendientes)
5. [ ] Confirmar horarios reales con el usuario
6. [ ] Confirmar datos legales completos (CIF, registro mercantil) o documentar que es "minimal"
7. [ ] Generar/reemplazar brand assets (logo, favicon, og-image)

### Prioridad BAJA (limpieza)
8. [ ] Limpiar `texts.json`: eliminar marcadores `service_2`-`service_5` no usados
9. [ ] Actualizar `index.html` (home) con contenido real de bar (no genérico de servicios)
10. [ ] Simplificar `/precios/` para reflejar realidad: 1 servicio + mención especial

---

## 7. COMANDOS DE VERIFICACIÓN (para cuando Python esté disponible)

```bash
# Build completo con validación estricta
./legible/build.sh

# Tests de regresión
python3 -m unittest discover tests

# Servidor de desarrollo (ver visualmente)
python3 legible/dev.py
# Abrir http://localhost:3001/

# Pre-launch sweep (busca valores de ejemplo, [CONFIRM], SAMPLE COPY)
python3 legible/build.py --sweep

# Validar JSON-LD específicamente
python3 -c "
import json, sys
with open('dist/entity.jsonld') as f: data = json.load(f)
print('JSON-LD válido:', len(data['@graph']), 'nodos')
"
```

---

## 8. NOTAS PARA EL MANTENEDOR

- **FLOW_OFF.lock**: No existe (flujos ON)
- **SITE_PLAN.md**: Actualizado con todas las fases, execution log y final state
- **site.json**: `project_stage: "complete"`
- **Commits en test1**: 3 commits nuevos (a5df93e, 3ad1f94, be86980)
- **No hay cambios sin commitear**: working tree clean

**Regla de oro**: Nunca debilitar tests ni validador. Si un test falla por contenido del sitio, corregir el contenido (texts.json, entity.json, páginas) no el test.