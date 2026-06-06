# Mapa del pipeline — cert-firma-cc

**Última actualización:** 2026-06-05 (app v0.4.0 navega Curso→Sin Firma; pivot a Google Apps Script en construcción, ADR-0002)
**Creación original:** 2026-05-26

```mermaid
flowchart LR
    DriveCGR[Drive CGR<br/>Carpeta 'Firma/Sin Firma (PRUEBA)']
    Token[token_cgr.json<br/>readonly]
    Input[data/input/<br/>copias locales]
    Extractor[scripts/extraer_campos.py<br/>PyMuPDF: 8 campos visibles]
    Hash[scripts/calcular_hash.py<br/>SHA-256 v1 string canonico<br/>solo datos del PDF]
    Stamper[scripts/estampar.py<br/>overlay PyMuPDF: leyenda + hash + QR]
    Output[data/output/lote_TS/<br/>PDFs estampados + listado + manifest]
    ActaPDF[scripts/generar_pdf_acta.py<br/>acta.pdf firmable]
    ActaXlsx[scripts/generar_excel_acta.py<br/>acta.xlsx revision]
    QA[scripts/qa_suite.py<br/>8 casos PASS/FAIL]
    Verif[scripts/verificar.py<br/>recalcula hash del papel]
    Firmador[Firmador BCCR<br/>FUERA DE SCOPE]
    Acta[Acta firmada<br/>PAdES]

    DriveCGR -->|bajar_certificados.py| Input
    Token --> DriveCGR
    Input --> Extractor
    Extractor --> Hash
    Hash --> Stamper
    Stamper --> Output
    Output --> ActaPDF
    Output --> ActaXlsx
    Output --> QA
    ActaPDF -->|jefe firma| Firmador
    Firmador --> Acta
    Output -.verificacion.-> Verif
```

**Nota arquitectural:** el pipeline NO consume ningún CSV ni fuente externa de datos (PII). Cada cert es self-contained: el hash se calcula 100% desde los 8 campos visibles del PDF. Ver `adr-0001-hash-sin-cedula.md`.

**Orquestación end-to-end del lote** (mismo flujo en CLI y en la app):
`generar_acta.py` (extrae → hashea → estampa → listado + manifest) → `generar_pdf_acta.py` (acta.pdf) → `generar_excel_acta.py` (acta.xlsx). La app Streamlit (`app/app.py`) replica esta cadena en `_procesar_lote()` con un wizard de 4 pasos.

## Responsabilidades por componente

| Componente | Estado | Responsabilidad |
|---|---|---|
| `app/app.py` | piloto (v0.3.x) | UI Streamlit local, wizard 4 pasos: elegir cohorte del Drive → preview extracción → procesar lote → resultado/descarga. Para uso del jefe sin tocar CLI |
| `scripts/bajar_certificados.py` | piloto | Descarga readonly de PDFs originales a `data/input/` |
| `scripts/extraer_campos.py` | piloto | Parsea PDF con PyMuPDF (anchors) y devuelve los 8 campos canónicos |
| `scripts/smoke_extractor.py` | piloto | Valida `extraer_campos.py` contra 1 PDF real; falla loud si campo vacío. Acepta path como argumento |
| `scripts/calcular_hash.py` | piloto | Construye string canónico (NFC+lower+trim) y devuelve SHA-256 hex |
| `scripts/estampar.py` | piloto | Overlay sobre el PDF: leyenda "Acta firmada digitalmente" + hash + etiqueta (centro), y QR (esquina sup-izq) con `{v, nombre, hash}`. No modifica el original |
| `scripts/generar_acta.py` | piloto | Orquestador del lote: estampados + `listado_hashes.csv/json` + `manifest.json` + `run.log` |
| `scripts/generar_pdf_acta.py` | piloto | `acta.pdf` tabular (reportlab) listo para firmar en el BCCR |
| `scripts/generar_excel_acta.py` | piloto | `acta.xlsx` tabular para revisión administrativa |
| `scripts/verificar.py` | piloto | Verificación independiente: recalcula el hash de un PDF estampado y lo compara con el esperado. Rol del verificador con solo el papel |
| `scripts/qa_suite.py` | piloto | Suite de QA del mecanismo (8 casos PASS/FAIL). Ver `docs/qa/protocolo_qa_emision_certificados.md` |

> **Componentes retirados:** `generar_muestras_visuales.py` y la opción `--variante A|B|C` existieron durante la elección del layout de estampado (sesión 2026-05-26); la variante fue elegida y consolidada en `estampar.py`. El QR se agregó en la misma fase como complemento.

## Dependencias externas

- **Drive CGR** (`alejandro.herrera@cgr.go.cr`, Workspace `cgr.go.cr`): único origen autorizado de PDFs. Solo lectura.
- **`token_cgr.json`**: en `C:\Users\aleja\`, scope `drive.readonly`. Refrescable con refresh_token.
- **Firmador BCCR**: cliente desktop oficial. Fuera de scope; aplica la firma PAdES sobre `acta.pdf`.
- **Librerías**: PyMuPDF (`fitz`), `qrcode`, `reportlab`, `openpyxl`, `google-api-python-client`, `streamlit`.

## Puntos de entrada

- **App (recomendada para el jefe):**
  - `python -m streamlit run app/app.py`  ·  o doble-click en `iniciar.bat`
- **CLI (operación / QA):**
  - `python scripts/bajar_certificados.py`
  - `python scripts/smoke_extractor.py <pdf>`
  - `python scripts/generar_acta.py --curso "<nombre>"`
  - `python scripts/generar_pdf_acta.py [lote_dir]`
  - `python scripts/generar_excel_acta.py [lote_dir]`
  - `python scripts/verificar.py <pdf_estampado> [<hash_esperado>]`
  - `python scripts/qa_suite.py [lote_dir] [--lote-previo <dir>]`
- No hay endpoints HTTP, ni cron jobs, ni MCP server en esta fase.

## Pivot a Google Apps Script (en construcción — ADR-0002, 2026-06-05)

Por decisión del firmante (CONSTITUTION 2.0.0), el runtime de producción migra a **Google Apps
Script puro**: hoja de control (matrícula + 7 constantes de cohorte) → hash en JS → estampado con
`PDFApp`/pdf-lib + QR → acta publicada a un Google Sheet compartible. El generador de certificados
es externo/manual, por eso GAS reconstruye los campos (riesgo de verificabilidad asumido, ADR-0002).

| Componente | Estado | Responsabilidad |
|---|---|---|
| `gas/canonical_hash.js` | en construcción | String canónico v1 + SHA-256 en JS, portable GAS/Node. Paridad probada con Python |
| `gas/test_parity.mjs` | listo | Test JS↔Python sobre el listado real (2/2 OK, 2026-06-05) |
| `scripts/verificar.py` (PyMuPDF) | **oráculo de auditoría** | Gate obligatorio: valida que el hash estampado por GAS coincide con el texto del papel, antes de firmar |

**Plan de slices:** (1) hash JS + paridad [HECHO] · (2) GAS lee matrícula+constantes → listado a
Sheet · (3) estampado en GAS (PDFApp + QR) → PDFs a Drive · (4) acta como Sheet compartible · (5)
gate de auditoría con `verificar.py` sobre PDFs estampados por GAS.

## Documentos de proceso y calidad

- **Procedimiento oficial:** `docs/procedimientos/procedimiento_oficial_emision_certificados.md`
- **Protocolo de QA:** `docs/qa/protocolo_qa_emision_certificados.md`
- **Último reporte de QA:** `docs/qa/reporte_qa_20260529.md` (8/8 PASS)
- **Decisión del hash:** `docs/architecture/adr-0001-hash-sin-cedula.md`
