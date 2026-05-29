# [DOC] Documentación del proceso oficial de emisión + QA para adopción institucional

**Fecha:** 2026-05-29
**Tipo:** documentación (feature grande, sin cambio de código de pipeline)
**Solicitante:** Lic. Juan Alejandro Herrera López (Jefatura A.I, Centro de Capacitación CGR)

## Cumplimiento constitucional

- **§1 Propósito** — Este trabajo documenta y respalda el mecanismo ya construido (1 acta firmada + N certificados con hash impreso). No altera el propósito.
- **§3 Stack** — No introduce dependencias nuevas obligatorias al pipeline. `qa_suite.py` usa solo lo ya instalado (PyMuPDF, stdlib).
- **§5 Calidad** — Materializa la regla "smoke con data real" y "tests mínimos por feature" en un protocolo de QA reproducible y ejecutado.
- **§7 Reglas de negocio** — No cambia el string canónico ni `hash_version`. Documenta el modelo de verificabilidad por tercero (§7 último punto) como procedimiento.
- **ADR-0001** — La justificación institucional se apoya en (no contradice) la decisión "hash sin cédula".

## Problema

El proyecto tiene Constitution, ADR-0001 y specs por feature, pero falta:

1. Un **procedimiento oficial** end-to-end legible por auditoría/jerarquía CGR que permita **adoptar** el mecanismo como forma oficial de emisión de certificados del Centro.
2. Un **protocolo de QA reproducible** y su **ejecución con evidencia**, que asegure que el mecanismo es confiable (gate R44: no se recomienda adopción con QA diseñado pero no ejecutado).
3. `docs/architecture/app_map.md` está **desactualizado**: no refleja el QR, la app Streamlit, los generadores de acta (PDF/Excel) ni `verificar.py`; aún menciona `--variante` y `generar_muestras_visuales.py`.

## Solución propuesta

Producir, en este orden:

1. **Spec** (este documento).
2. **`scripts/qa_suite.py`** — harness reproducible que valida el mecanismo contra un lote real y emite un reporte PASS/FAIL por caso.
3. **Ejecución del QA** contra `lote_20260529_183128` (16 certificados reales) → evidencia capturada.
4. **`docs/qa/protocolo_qa_emision_certificados.md`** — definición de los casos, criterios de aceptación, cómo correrlo en cada cohorte futura.
5. **`docs/qa/reporte_qa_20260529.md`** — resultados ejecutados (resuelve gate R44).
6. **`docs/procedimientos/procedimiento_oficial_emision_certificados.md`** — procedimiento institucional con justificación técnico-legal embebida (audiencia: CGR auditoría/legal/jerarquía).
7. **`docs/architecture/app_map.md`** actualizado (solo agregar/actualizar, R0).

### Casos de QA (diseño)

| ID | Caso | Qué asegura |
|---|---|---|
| QA-01 | Cobertura del lote | Todos los PDFs del lote se procesan sin error (16/16) |
| QA-02 | Determinismo sobre campos registrados | `calcular()` sobre los campos del listado reproduce el hash registrado |
| QA-03 | Verificación por tercero (papel) | Extraer del PDF **estampado** y recalcular reproduce el hash del acta |
| QA-04 | Idempotencia entre lotes | Mismo input → mismo hash, independiente del timestamp del lote |
| QA-05 | Integridad del listado | `sha256(listado_hashes.json)` == `manifest.hash_listado_json_sha256` |
| QA-06 | Originales intocables | Estampar no modifica el PDF de entrada (hash de input estable) |
| QA-07 | Sensibilidad (avalancha) | Alterar 1 carácter de un campo cambia el hash |
| QA-08 | Normalización NFC | Acento precompuesto vs combinado → mismo hash |

## Archivos afectados

- **Nuevos:** `scripts/qa_suite.py`, `docs/qa/protocolo_qa_emision_certificados.md`, `docs/qa/reporte_qa_20260529.md`, `docs/procedimientos/procedimiento_oficial_emision_certificados.md`, este spec.
- **Actualizado (solo expandir, R0):** `docs/architecture/app_map.md`.
- **No se toca:** código del pipeline (`extraer_campos`, `calcular_hash`, `estampar`, generadores de acta), Constitution, ADR-0001.

## Criterios de aceptación

- [x] `qa_suite.py` corre sin error y emite reporte PASS/FAIL por caso. (ruff limpio)
- [x] Los 8 casos QA pasan contra el lote real. **8/8 PASS, 0 críticos** (`lote_20260529_220700`).
- [x] Reporte de QA con evidencia (hashes, conteos) persistido en disco → `docs/qa/reporte_qa_20260529.md`.
- [x] Protocolo de QA reproducible para cohortes futuras → `docs/qa/protocolo_qa_emision_certificados.md`.
- [x] Procedimiento oficial legible por no-técnico, con justificación y pasos de verificación por tercero → `docs/procedimientos/procedimiento_oficial_emision_certificados.md`.
- [x] `app_map.md` refleja el sistema actual (QR, app, actas, verificación, QA) sin perder contenido previo.

## Cierre

**Estado: CERRADA — 2026-05-29.** Todos los criterios cumplidos. Gate R44 resuelto (QA diseñado y ejecutado, evidencia en `docs/qa/reporte_qa_20260529.md`). Hallazgo de idempotencia (cambio de `fecha_emision` entre reemisiones, no es fallo) documentado en el reporte. Sin cambios al código del pipeline ni a documentos protegidos.

## Notas

- Audiencia del procedimiento/justificación: **institucional CGR** (decisión del solicitante 2026-05-29).
- QA: **diseñar y ejecutar ahora** (decisión del solicitante 2026-05-29), para habilitar la recomendación de adopción sin violar R44.
- La firma digital del acta con la tarjeta BCCR queda **fuera de scope** del sistema (Constitution §3) y, por tanto, fuera del QA automatizado; el procedimiento sí la describe como paso humano.
