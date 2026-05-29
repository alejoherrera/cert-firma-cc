# Protocolo de QA — emisión de certificados con acta única

**Versión:** 1.0 · **Fecha:** 2026-05-29
**Aplica a:** mecanismo "1 acta firmada digitalmente + N certificados con hash SHA-256 impreso"
**Implementación:** `scripts/qa_suite.py`
**Última ejecución:** ver `docs/qa/reporte_qa_20260529.md`

Este protocolo define **qué debe verificarse**, **con qué criterio de aceptación** y **cómo correrlo** cada vez que se emite un lote de certificados, para que el mecanismo siga siendo confiable a lo largo del tiempo y de las cohortes. Es la materialización de Constitution §5 ("smoke con data real obligatorio", "tests mínimos por feature").

## Cuándo correr este protocolo

1. **Antes de firmar el acta de cada cohorte** (control de salida obligatorio).
2. Tras **cualquier cambio** en `extraer_campos.py`, `calcular_hash.py` o `estampar.py`.
3. Antes de **promover el piloto a producción institucional**, contra ≥2 cohortes de cursos distintos.

## Pre-requisito: smoke del extractor (Constitution §5)

Antes del pipeline completo, validar el extractor contra 1 PDF real de la cohorte:

```powershell
python scripts/smoke_extractor.py "data/input/<un_certificado>.pdf"
```

Debe imprimir los 8 campos canónicos no vacíos y `[OK] Smoke PASSED`. Si falla, **no continuar**: la plantilla del certificado cambió y el extractor por anchors necesita revisión.

## Casos de prueba

Cada caso indica su criticidad. Un **fallo crítico** bloquea la firma del acta hasta resolverse; un **warning** se documenta pero no bloquea.

| ID | Caso | Qué asegura | Criterio de aceptación | Criticidad |
|---|---|---|---|---|
| QA-01 | Cobertura del lote | Todos los certificados se procesaron | `procesados == nº de PDFs de input` y `errores == 0` | Crítico |
| QA-02 | Determinismo sobre campos | El hash guardado es reproducible desde los campos | `calcular(campos_listado) == hash_sha256` para los N registros | Crítico |
| QA-03 | Verificación por tercero | El papel se autoverifica contra el acta | Extraer del PDF **estampado** y recalcular == hash del acta, N/N | Crítico |
| QA-04 | Idempotencia entre lotes | Mismo input → mismo hash | Re-correr sobre input idéntico: 0 discrepancias en N hashes | Crítico |
| QA-05 | Integridad del listado | El sello del manifest cubre el listado real | `sha256(listado_hashes.json) == manifest.hash_listado_json_sha256` | Crítico |
| QA-06 | Originales intocables | El sistema no altera los PDF fuente | SHA-256 del original estable tras estampar; salida ≠ original | Crítico |
| QA-07 | Sensibilidad (avalancha) | El hash detecta cualquier cambio de contenido | Alterar 1 carácter de un campo cambia el hash | Crítico |
| QA-08 | Normalización NFC | Misma cadena en NFC/NFD → mismo hash | `calcular(NFC) == calcular(NFD)` | Crítico |
| QA-09 | Colisión de homónimos | El operador gestiona el riesgo de ADR-0001 | Si dos certs comparten nombre+curso+período: aplicar correlativo manual y re-verificar | Manual (ad-hoc) |

> **Nota sobre QA-04:** la idempotencia se prueba re-corriendo el pipeline sobre el **mismo** input, no comparando contra lotes históricos de inputs distintos. Dos hashes distintos para el mismo nombre en cohortes/fechas distintas son **correctos** si algún campo visible (p. ej. `fecha_emision`) cambió — el hash está atado al contenido del certificado por diseño (ver `reporte_qa_20260529.md`).

## Cómo ejecutar

```powershell
# 1. (pre) smoke del extractor con un PDF real de la cohorte
python scripts/smoke_extractor.py "data/input/<un_certificado>.pdf"

# 2. Generar el lote
python scripts/generar_acta.py --curso "<nombre del curso>"

# 3. Idempotencia: regenerar sobre el MISMO input (segundo lote)
python scripts/generar_acta.py --curso "<nombre del curso>"

# 4. Correr la suite (compara los dos lotes más recientes)
python scripts/qa_suite.py
```

`qa_suite.py` sale con **exit code 0** si todos los casos críticos pasan, **!= 0** si hay fallo crítico. Imprime PASS/FAIL/WARN por caso con su evidencia.

## Qué NO cubre este protocolo (límites explícitos)

- **Firma BCCR del acta.** Es un paso humano fuera de scope (Constitution §3). Control manual descrito en el procedimiento oficial.
- **Validez jurídica de la firma.** Depende del certificado digital del firmante y de la infraestructura del BCCR, no de este sistema.
- **Disponibilidad/backup del Drive origen.** Responsabilidad institucional CGR.

## Registro de ejecuciones

| Fecha | Lote | Resultado | Reporte |
|---|---|---|---|
| 2026-05-29 | `lote_20260529_220700` | 8/8 PASS | `docs/qa/reporte_qa_20260529.md` |

Agregar una fila por cada ejecución formal (antes de firmar cada cohorte).
