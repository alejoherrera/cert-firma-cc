# ADR-0002 — Pivot a Google Apps Script (GAS-puro) para el pipeline de hash + acta

- **Fecha:** 2026-06-05
- **Estado:** Aceptado (con riesgo asumido explícito por el firmante)
- **Decisores:** Lic. Juan Alejandro Herrera López (Jefatura A.I, único firmante)
- **Reemplaza parcialmente:** app local Streamlit (v0.4.0) y motor Python como runtime de usuario.
- **Relacionado:** [adr-0001-hash-sin-cedula.md], CONSTITUTION §3/§4.1/§7,
  `docs/qa/analisis_google_sheets_vs_app_local_20260604.md`.

## Contexto

El responsable pidió correr el pipeline desde un Google Sheet (Apps Script), motivado por: no
instalar/correr Python, no usar Streamlit, y obtener el acta/listado como hoja compartible. Los
certificados PDF se producen con un **generador externo/manual** (no Apps Script, no controlado).
La matrícula (`Matrícula (NN).csv`) aporta solo identidad del participante; los 7 campos de
cohorte (curso, periodo, horas, modalidad, fecha_emision, firmante, jefatura) viven en el
generador.

## Decisión

Migrar el runtime a **Google Apps Script puro**: una hoja de control donde el operador carga la
matrícula y tipea las 7 constantes de cohorte; GAS reconstruye el string canónico, calcula el
SHA-256, estampa cada PDF (vía librería `PDFApp`/pdf-lib + QR como imagen) y publica el listado y
el acta a un Google Sheet compartible.

## Alternativas consideradas

1. **Motor PyMuPDF empaquetado como .exe** (recomendado por el análisis): extrae los 8 campos del
   PDF terminado ⇒ hash idéntico al papel por construcción; sin Python visible; sin Streamlit.
   **Rechazada por el firmante** (no quiere ejecutable; prefiere Apps Script).
2. **Híbrido** (Sheet = panel, Python local = motor). Rechazada: sigue requiriendo Python local.
3. **GAS-puro** (elegida).

## Riesgo asumido (CRÍTICO — decisión consciente del firmante)

CONSTITUTION §7 + ADR-0001 garantizan que un tercero recalcula el hash leyendo **solo el papel**.
En GAS-puro el hash se calcula desde datos **reconstruidos** (matrícula + 7 constantes tipeadas),
no desde el texto impreso. Si la reconstrucción difiere del texto del PDF aunque sea en un
carácter (espacio, punto, tilde), el hash estampado **no coincide con el papel** y **todos** los
certificados del lote fallan la verificación de terceros, en silencio.

El firmante fue advertido de este riesgo (ver análisis y diálogo 2026-06-05) y **decidió
asumirlo** para obtener la arquitectura Apps Script. Queda registrado aquí, en el commit y en
memoria del proyecto.

## Mitigación obligatoria (gate de auditoría con oráculo)

El estampado es un overlay: el PDF estampado **conserva el texto visible original**. Por lo tanto
`scripts/verificar.py` (motor PyMuPDF) puede correr como **auditor independiente** sobre los PDF
estampados por GAS y confirmar `hash_estampado == hash(texto visible)`. 

- Durante el piloto: por cada cohorte, correr `verificar.py` sobre una muestra (idealmente el
  100%) de los PDF estampados por GAS **antes de firmar el acta**. Si algún hash no coincide ⇒ la
  reconstrucción no reproduce el papel ⇒ corregir las 7 constantes y re-estampar.
- Este gate NO corre en el runtime del operador (no reintroduce Python en su flujo); es un control
  de QA del desarrollador/responsable, ejecutable periódicamente. Retirarlo requiere nueva ADR.

## Consecuencias

- **Stack (§3):** se agrega Apps Script (JavaScript V8) como runtime. Enmienda constitucional a
  2.0.0.
- **Escritura a Drive (§4.1):** GAS escribe PDF estampados + Sheet del acta en el Workspace
  `cgr.go.cr`. Enmienda §4.1 + scope OAuth (`drive`, `spreadsheets`). PII permanece dentro del
  Workspace institucional donde ya viven los originales.
- **Hash en dos lenguajes:** se reimplementa en JS (NFC+lowercase+trim+`|`+SHA-256). Se exige
  cross-validación byte-a-byte contra el Python actual (test de paridad) y el gate de oráculo de
  arriba.
- **El motor Python NO se borra:** queda como (a) oráculo de verificación/auditoría y (b)
  fallback. Es deuda viva intencional, documentada.

## Estado al cerrar sesión 2026-06-06 / punto de retomada

- HECHO: slice 1 (hash JS + paridad 2/2), gobernanza (este ADR, CONSTITUTION 2.0.0, memoria).
- **PRÓXIMO al retomar: slice 2** — proyecto Apps Script ligado a un Google Sheet de control que
  (a) lea la matrícula (`Nombre/Primer Apellido/Segundo Apellido` → `nombre`), (b) tome las 7
  constantes de cohorte tipeadas, (c) use `gas/canonical_hash.js` para el hash, (d) escriba el
  listado a una hoja. Sin estampado todavía (eso es slice 3 con `PDFApp`).
- Decisión abierta para slice 2: ¿el código GAS se versiona en `gas/` y se sube con `clasp`, o se
  edita directo en el editor de Apps Script? (sugerido: `clasp` para mantener trazabilidad en repo).

## Criterios de cierre del pivot

- [x] Test de paridad hash JS↔Python verde sobre los campos de los 2 certs reales (2026-06-05,
  `gas/test_parity.mjs` → 2/2 coinciden, canónico + SHA-256 idénticos).
- [ ] GAS estampa un PDF cuyo `verificar.py` da HASH COINCIDE.
- [ ] Acta publicada a Google Sheet compartible.
- [ ] Enmienda constitucional 2.0.0 aplicada + este ADR aceptado.
