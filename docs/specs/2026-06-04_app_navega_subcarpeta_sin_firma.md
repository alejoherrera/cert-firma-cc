# [feature] App navega Curso → subcarpeta "Sin Firma"

## Cumplimiento constitucional
- §1/§4.1: sigue readonly sobre Drive (solo `files().list` y `get_media`). No toca originales.
- §7: no altera el string canónico ni el hash. Cambio solo de navegación/UX.

## Problema
La estructura real en Drive ahora tiene 3 niveles:
`Firma (ROOT) → <Curso>/ → "Sin Firma"/ → PDFs`.
La app lista subcarpetas **directas** del ROOT y cuenta PDFs **directos**, así que ve cada
curso con 0 PDFs y no permite bajar el lote (caso real 2026-06-04, carpeta
"Gestión de Fideicomisos Públicos para Auditorías Internas").

## Solución propuesta
En el Paso 1, para cada carpeta de curso bajo el ROOT, ubicar la subcarpeta cuyo nombre
contenga "sin firma" (case-insensitive) y usar **sus** PDFs como cohorte (count + descarga).
Si el curso no tiene esa subcarpeta, fallback a PDFs directos del curso (compat con estructura
vieja de prueba). Nunca se procesan subcarpetas tipo "Con Firma"/"Firmados".

## Archivos afectados
- `app/app.py` — helper `_resolver_carpeta_pdfs()`; `_subcarpetas_con_count()` cuenta sobre la
  carpeta resuelta y guarda `pdf_folder_id`; el botón "Bajar PDFs" usa `pdf_folder_id`.

## Criterios de aceptación
- [x] Con la carpeta real de 3 niveles, el Paso 1 muestra el curso con count = 2 PDFs.
- [x] "Bajar PDFs" descarga exactamente los 2 PDFs de "Sin Firma" (pdf_folder_id != curso_id).
- [x] Una subcarpeta "Con Firma" hermana (si existiera) NUNCA se descarga (solo match 'sin firma').
- [x] Estructura vieja (PDFs directos bajo la subcarpeta) sigue funcionando (fallback a curso_id).
- [x] Smoke real 2026-06-04 contra ROOT: "Gestión de Fideicomisos" -> 2 PDFs; otro curso -> 24 PDFs.

## Estado: CERRADA (2026-06-04). App v0.4.0.

## Tipo
feature (mediana, 1 archivo) — riesgo BAJO, sin cambio de contrato.
