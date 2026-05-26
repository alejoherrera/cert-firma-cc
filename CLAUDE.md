# cert-firma-cc — Reglas locales

Sistema que estampa hash SHA-256 en certificados de cursos del Centro de Capacitación CGR y produce el listado de hashes que el responsable firma digitalmente como acta única.

## Archivos protegidos (R0)
- `CONSTITUTION.md`
- `CLAUDE.md`
- `docs/specs/*.md` cerradas (no reducir contenido; solo agregar o cerrar criterios)

## Stack
- Python 3.11+ · PyMuPDF · google-api-python-client
- OAuth token CGR existente: `C:\Users\aleja\token_cgr.json` (scope `drive.readonly`)
- Carpeta Drive origen: `1U7aSbdtoPl3cYVWDzff5_LQwQ8Bjk_1T` (Firma → Sin Firma (PRUEBA))

## Estructura
```
cert-firma-cc/
  CONSTITUTION.md          # autoridad maxima del proyecto
  CLAUDE.md                # este archivo
  pyproject.toml           # dependencias + semver
  iniciar.bat              # launcher Windows de la app (doble-click)
  app/
    app.py                 # UI Streamlit (v0.3.0+) — wizard 4 pasos
  scripts/                 # motor CLI (la app los importa)
    bajar_certificados.py  # Drive readonly -> data/input/
    extraer_campos.py      # parser PyMuPDF por anchor strings
    smoke_extractor.py     # valida extractor contra 1 PDF real
    calcular_hash.py       # string canonico v1 + SHA-256
    estampar.py            # overlay leyenda+hash+QR sobre PDF
    generar_acta.py        # orquestador end-to-end del lote
    generar_pdf_acta.py    # PDF tabular del acta (firmable BCCR)
    generar_excel_acta.py  # xlsx tabular del acta (revision admin)
    verificar.py           # self-verifica un PDF estampado
  docs/
    specs/                 # spec por feature (R36)
    architecture/          # ADRs + app_map (R42)
  data/                    # gitignored todo lo que vive aca
    input/                 # copias locales de PDFs originales (NUNCA al git)
    output/                # PDFs estampados + listados + acta data
```

## Reglas operativas

1. **Nunca tocar originales en Drive.** Token scope es `drive.readonly`. Aun asi: no llamar `files().update()`, `files().delete()` ni equivalentes. Solo `files().list()` y `files().get_media()`.
2. **PII fuera del git.** Antes de cualquier commit: `git status` no debe mostrar `data/` ni `*.csv` con cedulas/nombres.
3. **String canonico del hash v1** (segun CONSTITUTION §7 + ADR-0001):
   `nombre_normalizado|curso|periodo|horas|modalidad|fecha_emision|firmante|jefatura`
   normalizado a NFC + lowercase + trim por campo. **NO incluye cedula** ni dato externo al PDF.
   Cambiar la formula = bump hash_version + nueva ADR.
4. **Smoke extractor obligatorio** antes de pipeline completo (regla global responsable).
5. **Encoding Windows:** sin emojis en print/log (`[OK]`, `[ERROR]`).
6. **Cuando este listo para commit:** verificar `.gitignore` cubre lo que corresponde; jamas `git add -A`.

## Referencias externas
- Token CGR + script de exploracion: `C:\Users\aleja\explorar_drive.py` (proyecto resoluciones_DCP)
- Memoria global: feedback `cgr_prueba_github_personal` justifica github personal en piloto
