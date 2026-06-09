# ADR-0003 — Hash v2: el string canónico NO incluye `fecha_emision`

- **Fecha:** 2026-06-09
- **Estado:** Aceptado (decisión consciente del firmante, con trade-off advertido)
- **Decisor:** Lic. Juan Alejandro Herrera López (Jefatura A.I, único firmante)
- **Versión de hash:** v1 (8 campos) → **v2 (7 campos)**
- **Relacionado:** [adr-0001-hash-sin-cedula.md], [adr-0002-pivot-google-apps-script.md],
  CONSTITUTION §7, `docs/specs/2026-06-09_gas_slice2_listado_acta.md`.

## Contexto

Al especificar el slice 2 del runtime Apps Script (matrícula CSV + constantes de cohorte → hash),
se constató que:

1. El CSV de matrícula real (`Matrícula (NN).csv`, verificado 2026-06-09) **no tiene columna de
   fecha**. Sus 9 columnas son `Nombre · Primer Apellido · Segundo Apellido · Cédula · Institución ·
   Siglas · Resultado · Email · Expediente`.
2. El firmante indicó que `fecha_emision` **varía por participante**, de modo que no es una
   constante de cohorte y tampoco viene en el CSV.
3. En GAS-puro el hash se reconstruye desde datos tipeados/importados, no desde el texto del PDF
   (riesgo central de ADR-0002). `fecha_emision` es además el campo más propenso a divergir del
   texto impreso (formato libre: "San José, 25 de mayo, 2026" vs "25/05/2026" vs …), lo que
   dispararía hash que **no coincide con el papel** en silencio.

Mantener `fecha_emision` en el hash exigiría una fuente per-participante fiable e idéntica al PDF,
que hoy no existe sin volver a parsear el PDF (lo que GAS no hace).

## Decisión

Remover `fecha_emision` del string canónico. **Hash v2 = 7 campos:**

```
canonico_v2 = nombre_norm | curso_norm | periodo_norm | horas_norm |
              modalidad_norm | firmante_norm | jefatura_norm

hash = SHA-256(canonico_v2 encoded UTF-8)        hash_version = 2
```

`_norm` = `NFC(lower(trim(campo)))`, separador `|` literal (igual que v1).

`fecha_emision` **se sigue extrayendo y mostrando** en el acta/listado y en el certificado; solo
**deja de entrar al hash**.

## Trade-off (advertido y asumido por el firmante)

- **A favor:** elimina el campo más difícil de reconstruir/parear con el papel ⇒ de-riesga
  directamente el problema de verificabilidad de ADR-0002. Resuelve que el CSV no traiga fecha y que
  la fecha varíe por participante.
- **En contra:** el hash **deja de atestiguar la fecha de emisión**. Un tercero podría alterar la
  fecha impresa en un certificado sin romper su hash. `periodo` sigue atando parcialmente la ventana
  temporal del curso, pero no la fecha exacta de emisión.
- **Unicidad (ADR-0001):** la combinación anti-colisión pierde un campo. Sigue siendo
  `nombre+curso+periodo+horas+modalidad`; el riesgo de homónimos exactos en la misma cohorte se
  gestiona caso por caso como ya prevé ADR-0001.

## Consecuencias

- **Incompatibilidad v1↔v2:** los hashes de un mismo certificado difieren entre versiones. Los lotes
  v1 ya estampados (mayo 2026, piloto, **ninguno firmado oficialmente**) quedan inmutables y marcados
  como v1; los lotes nuevos son v2. El `manifest.json` y el cert llevan `hash_version` para
  desambiguar.
- **Paridad JS↔Python:** se re-valida sobre v2 (`gas/test_parity.mjs`). El oráculo `verificar.py`
  recalcula con v2; correrlo sobre PDFs v1 dará NO COINCIDE (esperado).
- **Gobernanza:** enmienda CONSTITUTION §7 → bump **3.0.0**; actualización de la regla 3 del
  `CLAUDE.md` del proyecto.
- **Nota de numeración:** ADR-0001 anticipó "bump a v2 + ADR-0002" para un cambio de fórmula; ADR-0002
  terminó siendo el pivot a Apps Script, así que **este** cambio de fórmula es ADR-0003.

## Alternativa considerada y rechazada

- **`fecha_emision` como constante por cohorte (mantener v1):** sin enmienda, el hash sigue
  atestiguando la fecha. Rechazada por el firmante: la fecha varía por participante, así que una
  constante única por lote no representaría el papel.

## Criterios de cierre

- [x] `calcular_hash.py` y `canonical_hash.js` en v2 (7 campos), paridad byte-a-byte verde
      (`gas/test_parity.mjs` → 2/2, 2026-06-09).
- [x] CONSTITUTION §7 enmendada (3.0.0) + regla 3 del CLAUDE.md del proyecto actualizada.
- [x] Lote regenerado bajo v2 (`lote_20260609_222044`) + `verificar.py` da HASH COINCIDE sobre un
      PDF v2 (oráculo OK). QA suite 7/8 PASS, 0 críticos (el WARN QA-04 es la diferencia v1↔v2,
      esperada). Ruff verde.

## Estado: ACEPTADO Y CERRADO (2026-06-09).
