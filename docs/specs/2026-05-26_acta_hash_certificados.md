# 2026-05-26 — Acta única + hash en certificados

## Cumplimiento constitucional
Cumple §1 (propósito), §3 (stack), §4 (PII off-git, originales intocables), §7 (string canónico + cédula como ID). Esta es la primera spec del proyecto: define el flujo base.

## Problema
El jefe del Centro de Capacitación CGR firma decenas/cientos de certificados de cursos. Firmar cada uno con tarjeta BCCR es inviable. Necesita: un solo acto de firma digital (sobre una "acta") que cubra todo el lote, sin perder verificabilidad individual de cada certificado.

## Decisión actualizada en sesión (2026-05-26)

Tras presentar 4 opciones al jefe del Centro, se decidió **no incluir cédula en el hash ni en el certificado** (ver ADR-0001). El string canónico v1 usa solo datos visibles en el PDF: `nombre|curso|periodo|horas|modalidad|fecha_emision|firmante|jefatura`. Esto elimina la necesidad de `participantes.csv`.

## Solución propuesta (actualizada con ADR-0001)

**Re-estampado + hash + listado, sin PII externa:**

1. **Bajar** los N PDFs originales del Drive a `data/input/` (readonly, copias).
2. **Extraer** los 8 campos canónicos del PDF original con PyMuPDF: `nombre, curso, periodo, horas, modalidad, fecha_emision, firmante, jefatura`.
3. **Calcular** hash canónico v1 (todos los campos `NFC + lower + trim`, separador `|`):
   ```
   hash = SHA-256("nombre|curso|periodo|horas|modalidad|fecha_emision|firmante|jefatura")
   ```
4. **Re-estampar** el PDF original con el hash visible en posición a definir (3 variantes a presentar al usuario antes de decidir). Output a `data/output/<slug-nombre>.pdf`. **NO se modifica el original.**
5. **Generar** `data/output/listado_hashes.csv` y `.json` con columnas `nro, nombre, curso, periodo, horas, modalidad, fecha_emision, firmante, jefatura, hash_sha256`. Más `manifest.json` con metadata del lote (timestamp, git commit, hash_version=1, total).
6. **El jefe arma el acta y la firma con el firmador del BCCR** (fuera de scope).

## Archivos afectados (nuevos)
- `pyproject.toml` — dependencias + semver inicial `0.1.0`
- `scripts/bajar_certificados.py` — Drive readonly → `data/input/`
- `scripts/extraer_campos.py` — parser PyMuPDF (extrae los 8 campos canónicos visibles)
- `scripts/smoke_extractor.py` — valida extractor contra 1 PDF real, falla si campo vacío
- `scripts/calcular_hash.py` — string canónico v1 + SHA-256
- `scripts/estampar.py` — overlay PyMuPDF en posición elegida
- `scripts/generar_acta.py` — orquestador (lee input, extrae, hashea, estampa, escribe listado + manifest)
- `scripts/generar_muestras_visuales.py` — produce 3 variantes (A/B/C) sobre un PDF para elegir posición del hash
- `docs/architecture/app_map.md` — mapa del pipeline
- `docs/architecture/adr-0001-hash-sin-cedula.md` — decisión de no incluir cédula

## Criterios de aceptación

1. `python scripts/bajar_certificados.py` descarga los 15 PDFs a `data/input/` sin tocar Drive.
2. `python scripts/smoke_extractor.py data/input/CERTIFICADOS_PRUEBA-6.pdf` imprime los 8 campos extraídos y **falla con exit code ≠ 0 si alguno viene vacío**.
3. `python scripts/generar_muestras_visuales.py` produce 3 PDFs en `data/output/muestras_visuales/` (variantes A/B/C) sobre el PDF de Jonathan Carvajal con hash real (v1, sin cédula). Visualmente comparables.
4. Tras elegir variante: `python scripts/generar_acta.py --variante <A|B|C>` procesa los 15 PDFs y produce:
   - `data/output/lote_<timestamp>/<slug-nombre>.pdf` × 15
   - `data/output/lote_<timestamp>/listado_hashes.csv`
   - `data/output/lote_<timestamp>/listado_hashes.json`
   - `data/output/lote_<timestamp>/manifest.json` (con `hash_version: 1`)
   - `data/output/lote_<timestamp>/run.log`
5. **Verificación independiente:** un script aislado que reciba el PDF re-estampado y solo el PDF (sin acceso a `data/` ni a CSV externo) debe poder recalcular el hash leyendo los 8 campos visibles del cert y obtener el mismo hash listado en el acta. Es decir: self-verificación con solo el papel.
6. **PII off-git verificado:** `git status` no muestra ningún archivo bajo `data/` ni archivos con cédulas/nombres.

## Tipo
feature (greenfield) — primera spec del proyecto.

## Out of scope (explícito)
- Generación de PDFs desde plantilla (los originales vienen pre-hechos).
- Construcción y firma del acta PDF (lo hace el jefe con el firmador BCCR).
- Verificador automatizado para terceros (queda para fase 2 — depende de hospedaje).
- Subida de archivos de vuelta al Drive.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| PDF de origen no tiene el nombre estructurado de forma extraíble | Smoke obligatorio falla loud; si falla, ajustar extractor + agregar fixture |
| Homónimos en el mismo curso (dos "Juan Pérez Pérez") | Aceptado como riesgo bajo (ver ADR-0001). Si ocurre: se gestiona caso por caso con correlativo manual |
| Variante visual del hash mal elegida y hay que rehacer el lote | El re-estampado es idempotente sobre los originales; rehacerlo es barato |
| Política institucional cambia y exige cédula u otro identificador | Bumpear `hash_version` a 2, crear ADR-0002, lotes nuevos al esquema v2; lotes v1 firmados quedan inmutables |

## Próximos pasos
1. Aprobar esta spec.
2. Generar 3 muestras visuales → elegir variante.
3. Implementar resto del pipeline.
4. Correr smoke + lote completo.
5. Entregar al jefe para que arme y firme el acta.
