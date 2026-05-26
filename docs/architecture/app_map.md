# Mapa del pipeline — cert-firma-cc

**Última actualización:** 2026-05-26 (creación)

```mermaid
flowchart LR
    DriveCGR[Drive CGR<br/>Carpeta 'Firma/Sin Firma (PRUEBA)']
    Token[token_cgr.json<br/>readonly]
    Input[data/input/<br/>copias locales]
    Extractor[scripts/extraer_campos.py<br/>PyMuPDF: 8 campos visibles]
    Hash[scripts/calcular_hash.py<br/>SHA-256 v1 string canonico<br/>solo datos del PDF]
    Stamper[scripts/estampar.py<br/>overlay PyMuPDF]
    Output[data/output/lote_TS/<br/>PDFs + listado + manifest]
    Firmador[Firmador BCCR<br/>FUERA DE SCOPE]
    Acta[Acta firmada<br/>PAdES o XAdES]

    DriveCGR -->|bajar_certificados.py| Input
    Token --> DriveCGR
    Input --> Extractor
    Extractor --> Hash
    Hash --> Stamper
    Stamper --> Output
    Output -->|jefe construye acta<br/>con listado_hashes.json| Firmador
    Firmador --> Acta
```

**Nota arquitectural:** el pipeline NO consume ningún CSV ni fuente externa de datos (PII). Cada cert es self-contained: el hash se calcula 100% desde los 8 campos visibles del PDF. Ver `adr-0001-hash-sin-cedula.md`.

## Responsabilidades por componente

| Componente | Estado | Responsabilidad |
|---|---|---|
| `scripts/bajar_certificados.py` | dev | Descarga readonly de PDFs originales a `data/input/` |
| `scripts/extraer_campos.py` | dev | Parsea PDF con PyMuPDF y devuelve dict con 8 campos canónicos |
| `scripts/smoke_extractor.py` | dev | Valida `extraer_campos.py` contra 1 PDF real; falla loud si campo vacío |
| `scripts/calcular_hash.py` | dev | Construye string canónico (NFC+lower+trim) y devuelve SHA-256 hex |
| `scripts/estampar.py` | dev | Overlay del hash sobre PDF, posición parametrizada (A/B/C) |
| `scripts/generar_muestras_visuales.py` | dev | Produce 3 variantes A/B/C para que el responsable elija |
| `scripts/generar_acta.py` | dev | Orquestador end-to-end del lote |

## Dependencias externas

- **Drive CGR** (`alejandro.herrera@cgr.go.cr`, Workspace `cgr.go.cr`, proyecto GCP `loggin`): único origen autorizado de PDFs. Solo lectura.
- **`token_cgr.json` + `credentials_cgr.json`**: en `C:\Users\aleja\`, scope `drive.readonly`. Refrescable con refresh_token.
- **Firmador BCCR**: cliente desktop oficial. Fuera de scope.

## Puntos de entrada

- CLI:
  - `python scripts/bajar_certificados.py`
  - `python scripts/smoke_extractor.py <pdf>`
  - `python scripts/generar_muestras_visuales.py`
  - `python scripts/generar_acta.py --variante <A|B|C>`
- No hay endpoints HTTP, ni cron jobs, ni MCP server en esta fase.
