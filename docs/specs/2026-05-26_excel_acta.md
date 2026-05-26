# 2026-05-26 — Generar acta tabular en Excel

## Cumplimiento constitucional
Cumple §1 (propósito) y §7 (trazabilidad). Scope expansion menor de la spec `2026-05-26_pdf_acta.md`: el mismo lote produce ahora dos formatos del acta (PDF firmable + Excel editable), no uno.

## Problema
El acta en PDF es firmable digitalmente con BCCR, pero no editable. Para revisión humana previa, archivo administrativo o reuso en otros sistemas (RRHH, control de capacitaciones), un formato Excel resulta más cómodo: filtrable, ordenable, copiable a portapapeles, manipulable sin software especial.

## Solución propuesta
Nuevo script `scripts/generar_excel_acta.py`:

```
python scripts/generar_excel_acta.py [lote_dir]
```

- Default `lote_dir`: el más reciente bajo `data/output/lote_*/`
- Lee `listado_hashes.json` + `manifest.json` del lote
- Genera `acta.xlsx` dentro del mismo lote con UNA hoja "Acta":
  1. Bloque metadata (filas superiores): curso, fecha emisión, total, hash version, hash del listado JSON, lote_id
  2. Tabla principal: Nº | Nombre del participante | Fecha emisión | Hash SHA-256
  3. Pie con info del firmante institucional
- Estilos: encabezado azul CGR, filas alternadas, columna de hash en fuente monoespaciada
- Anchos de columna ajustados para legibilidad

## Archivos afectados
- `docs/specs/2026-05-26_excel_acta.md` (este archivo)
- `scripts/generar_excel_acta.py` (nuevo)
- `pyproject.toml` (agregar `openpyxl>=3.0`)

## Criterios de aceptación
1. `python scripts/generar_excel_acta.py` (sin args) genera `data/output/lote_<ultimo>/acta.xlsx`.
2. El xlsx se abre en Excel/LibreOffice sin advertencias.
3. La tabla contiene los N hashes del listado en formato monoespaciado, legibles a simple vista.
4. La metadata del header cita el `hash_listado_json_sha256` del manifest.

## Tipo
feature (scope expansion en sesión piloto — decidido 2026-05-26 con el responsable).

## Out of scope
- Firma digital sobre el xlsx (BCCR firmador trabaja con PDF/XML, no con xlsx directamente — para firmar va el PDF).
- Macros o automatización dentro del xlsx.
