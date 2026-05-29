# Reporte de QA ejecutado — mecanismo de emisión de certificados

**Fecha de ejecución:** 2026-05-29
**Ejecutor:** pipeline + `scripts/qa_suite.py` (sesión Claude Code)
**Lote bajo prueba:** `lote_20260529_220700` (16 certificados, curso "Gestión de Fideicomisos Públicos para Auditorías Internas")
**Lote de comparación (idempotencia):** `lote_20260529_183128` (mismo input)
**Versión del hash:** v1 · **Commit:** 230064b
**Protocolo:** `docs/qa/protocolo_qa_emision_certificados.md`

> **Resolución del gate R44:** el protocolo de QA fue **diseñado y ejecutado**. Esta evidencia habilita recomendar la adopción del mecanismo. No quedan casos críticos sin correr.

## Resultado global

**8/8 casos PASS · 0 fallos críticos.**

```
[PASS] QA-01 Cobertura del lote            procesados=16, errores=0, cobertura=OK
[PASS] QA-02 Determinismo                   16 registros, 0 discrepancias
[PASS] QA-03 Verificacion por tercero       verificados=16/16, fallos=0
[PASS] QA-04 Idempotencia entre lotes       comunes=16, discrepancias=0
[PASS] QA-05 Integridad del listado         manifest==real (e4b0b7f6c85b5318...)
[PASS] QA-06 Originales intocables          input estable=True, salida!=input=True
[PASS] QA-07 Sensibilidad (avalancha)       hash cambia al alterar 'curso'
[PASS] QA-08 Normalizacion NFC              NFC==NFD hash, prueba significativa
```

## Evidencia por caso

| ID | Caso | Evidencia | Veredicto |
|---|---|---|---|
| QA-01 | Cobertura del lote | 16 PDFs de `data/input/` → 16 registros, 0 errores en `manifest.json` | PASS |
| QA-02 | Determinismo sobre campos registrados | Para los 16 registros, `calcular(campos_del_listado)` == `hash_sha256` guardado. 0 discrepancias | PASS |
| QA-03 | Verificación por tercero (PDF estampado) | Extraer los 8 campos del PDF **estampado** (con leyenda + QR) y recalcular reproduce el hash del acta en 16/16. El estampado no rompe la extracción | PASS |
| QA-04 | Idempotencia entre lotes | Re-correr el pipeline sobre el **mismo input** produce `listado_hashes.json` con SHA-256 idéntico (`e4b0b7f6…`); 16/16 hashes coinciden con el lote previo | PASS |
| QA-05 | Integridad del listado | `sha256(listado_hashes.json)` == `manifest.hash_listado_json_sha256` | PASS |
| QA-06 | Originales intocables | Estampar un original a archivo temporal no altera el SHA-256 del original; la salida sí difiere del original | PASS |
| QA-07 | Sensibilidad (avalancha) | Alterar 1 carácter del campo `curso` cambia el hash por completo (`bd7f635a…` → `767c6e87…`) | PASS |
| QA-08 | Normalización NFC | El mismo texto en forma NFD produce el mismo hash que en NFC; la prueba es significativa (los datos traen acentos) | PASS |

## Hallazgo relevante durante la ejecución (idempotencia)

La **primera** ejecución de QA-04 comparó `lote_20260529_183128` contra `lote_20260526_164140` y reportó 14/14 discrepancias. La investigación mostró que **no era un fallo de idempotencia**, sino un cambio real en el dato origen:

```
26-may:  ...|san josé, 25 de mayo, 2026|...
29-may:  ...|san josé, 26 de mayo de 2026.|...
```

Los certificados fuente fueron **reemitidos con otra `fecha_emisión`** entre ambas fechas. Como `fecha_emision` es parte del string canónico (Constitution §7), el hash cambió **correctamente**. Esto confirma —no contradice— el diseño: el hash está atado al contenido visible del certificado.

La prueba de idempotencia válida re-corre el pipeline sobre **input idéntico** (QA-04 final): 16/16 hashes coinciden. **Conclusión:** el mecanismo es determinista; dos hashes distintos para "la misma persona" siempre implican un certificado con contenido distinto, que es exactamente la propiedad que se busca.

## Comando para reproducir

```powershell
# 1. Generar (o regenerar) un lote
python scripts/generar_acta.py --curso "<nombre del curso>"

# 2. Correr la suite contra el lote más reciente (idempotencia vs el anterior)
python scripts/qa_suite.py

# o explícito:
python scripts/qa_suite.py data/output/lote_<TS> --lote-previo data/output/lote_<TS_previo>
```

Exit code `0` = todos los casos críticos pasan; `!= 0` = hay fallo crítico.

## Limitaciones de este QA (alcance honesto)

- **No cubre la firma BCCR.** La firma digital del `acta.pdf` con la tarjeta del BCCR es un paso humano fuera de scope (Constitution §3); no se valida automáticamente aquí. El procedimiento oficial la describe como control manual.
- **No cubre colisión real de homónimos.** El riesgo está documentado en ADR-0001 con su mitigación caso-por-caso; no se forzó un homónimo en este lote porque no existe en la cohorte. Si se requiere, agregar un caso QA-09 con dos certificados de nombre+curso+período idénticos y verificar que el operador aplica el correlativo manual.
- **PDFs de prueba.** El lote es la cohorte real "Fideicomisos Públicos" en fase piloto (16 participantes). Para promoción a producción, repetir el QA sobre ≥1 cohorte adicional de otro curso (distinta plantilla/largo de nombre de curso) para estresar el extractor por anchors.
