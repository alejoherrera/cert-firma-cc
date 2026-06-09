# [feature] Slice 2 — GAS: matrícula + constantes → listado de hashes (acta)

> Primer slice del runtime Apps Script (ADR-0002). Genera la **información del acta**:
> nombre→hash por participante en una hoja. **No toca PDFs todavía** (eso es slice 3).

## Cumplimiento constitucional
- **§3 (stack):** usa Apps Script V8, ya admitido por la enmienda 2.0.0.
- **§7 + ADR-0001 + ADR-0003 (hash):** reutiliza `gas/canonical_hash.js`. String canónico **v2**
  = `nombre|curso|periodo|horas|modalidad|firmante|jefatura`, NFC+lower+trim, sin cédula
  (ADR-0001) ni `fecha_emision` (ADR-0003). `hash_version = 2`.
- **§4.1 (escritura a Drive):** este slice **solo escribe una hoja** dentro del Workspace
  `cgr.go.cr`. No escribe PDFs ni toca los originales. El estampado (escritura de PDFs) es slice 3.
- **Riesgo asumido (memoria `pivot-gas-riesgo-asumido`):** el hash sale de datos *reconstruidos*
  (matrícula + 7 constantes tipeadas), no del texto del PDF. Mitigación = gate del slice 5
  (`verificar.py`), fuera del alcance de esta spec pero condición de cierre del pivot.

## Problema
El componente GAS no existe (verificado 2026-06-09: ni repo ni Drive). Hoy solo está el slice 1
(`gas/canonical_hash.js` + paridad). Falta el primer eslabón del runtime: que un operador, desde un
Google Sheet, produzca el listado de hashes de una cohorte sin correr Python.

## Solución propuesta
Un proyecto Apps Script **ligado a un Google Sheet de control**, versionado en `gas/` vía `clasp`.
El Sheet tiene tres pestañas:

| Pestaña | Rol | Quién la llena |
|---|---|---|
| `Cohorte` | constantes tipeadas que entran al hash: `curso, periodo, horas, modalidad, firmante, jefatura` (6, celdas etiquetadas). `fecha_emision` ya **no** va al hash (ADR-0003); si se quiere mostrar en el acta, va como dato aparte. | operador |
| `Matricula` | CSV importado (ver "Contrato del CSV"); solo se listan filas con `Resultado = APROBADO` | operador (File→Import / pegar) |
| `Acta` | salida: `nombre · hash · hash_version`, con encabezado que repite las constantes para el registro | **la genera el script** |

Flujo: `onOpen()` agrega un menú "Acta CC → Generar listado". `generarListado()`:
1. lee las 6 constantes de `Cohorte`;
2. por cada fila de `Matricula` con `Resultado = APROBADO`, arma
   `nombre = "Nombre Primer Apellido Segundo Apellido"`;
3. construye los 7 campos v2 y llama `calcular()` de `gas/canonical_hash.js`;
4. escribe `nombre · hash · hash_version` en `Acta`, más el bloque de constantes como cabecera.

`gas/canonical_hash.js` ya es GAS-safe (el bloque `module.exports` se ignora cuando `module` es
`undefined`). En GAS, `Utilities.computeDigest(SHA_256, canon, UTF_8)` produce el hash.

### Contrato del CSV de matrícula (verificado 2026-06-09 contra `Matrícula (56).csv`)
- **Encoding `latin-1`**, **delimitador `;`**, 9 columnas:
  `Nombre · Primer Apellido · Segundo Apellido · Cédula · Institución · Siglas · Resultado · Email · Expediente`.
- Se usan **col 0–2**; el resto se ignora (incluida `Cédula`, ADR-0001).
- `nombre = "{Nombre} {Primer Apellido} {Segundo Apellido}"` (espacios simples) → luego `norm()`.

### Gotcha de encoding en el import (CRÍTICO para el hash)
El CSV es `latin-1` con `;`. Google Sheets, al importar, suele asumir UTF-8 y autodetectar `,`. Si
importa mal, las tildes/`ñ` se corrompen **en las celdas** → `nombre` corrupto → hash que **no
coincide con el papel**, en silencio (justo el riesgo de ADR-0002). Por eso:
- El operador debe importar con encoding correcto o convertir a UTF-8 antes, y **verificar
  visualmente** que tildes/`ñ` se ven bien en `Matricula` antes de generar.
- `generarListado()` puede incluir un chequeo barato: si detecta el carácter de reemplazo `�`
  o secuencias `Ã/Â` típicas de mojibake en `nombre`, aborta con alerta. (Detalle de impl., no
  contrato.)

## Archivos afectados
- `gas/slice2_acta.js` — **nuevo**. `onOpen()`, `generarListado()`, helpers de lectura del Sheet.
  Reutiliza `calcular()`/`stringCanonico()` de `canonical_hash.js` (globals en GAS).
- `gas/appsscript.json` — **nuevo**. Manifest (timeZone, scopes mínimos: `spreadsheets`).
- `.clasp.json` — **nuevo**. Config de clasp (scriptId, `rootDir: gas/`). scriptId no es secreto.
- `.claspignore` — **nuevo**. Excluye `test_parity.mjs` (test Node, no va a GAS) del push.
- `docs/architecture/app_map.md` — actualizar fila slice 2 a "listo" + punto de entrada GAS.
- `docs/architecture/adr-0002-pivot-google-apps-script.md` — marcar slice 2 hecho en el plan.

## Criterios de aceptación
- [ ] Importar la matrícula real + tipear las 7 constantes y correr "Generar listado" produce una
      fila por participante con su hash en `Acta`.
- [ ] **Paridad:** para los 2 certificados reales ya conocidos, el hash que calcula GAS coincide
      byte-a-byte con el de `scripts/calcular_hash.py` (mismos 7 campos de entrada v2). Reusar
      `gas/test_parity.mjs`.
- [ ] `hash_version = 2` y orden de campos idénticos a Python (sin cédula, sin fecha_emision).
- [ ] El script **no** escribe PDFs ni llama `DriveApp`/`files().update/delete` (solo la hoja).
- [ ] `clasp push` sube `slice2_acta.js` + `canonical_hash.js` + `appsscript.json`, y **no** sube
      `test_parity.mjs` (gracias a `.claspignore`).
- [ ] Fila con nombre vacío o constante faltante → error visible (toast/alert), no hash silencioso.

## Open questions (R40) — TODAS RESUELTAS 2026-06-09
1. ~~Encabezados del CSV~~ **RESUELTO**: contrato fijado arriba (latin-1, `;`, 9 cols, uso col 0–2).
2. ~~`fecha_emision` por participante~~ **RESUELTO**: el firmante decidió **sacar `fecha_emision`
   del hash** (v2, ADR-0003). Ya no es input del hash; el conflicto desaparece.
3. ~~Sheet por cohorte vs reutilizable~~ **RESUELTO**: **plantilla duplicable** por cohorte
   (historial por acta).
4. ~~Filtro por `Resultado`~~ **RESUELTO**: **solo aprobados** (`Resultado = APROBADO`,
   trim + case-insensitive). Único valor observado en el CSV real: `APROBADO`.

## Tipo
feature (mediana, ~4 archivos nuevos en `gas/` + 2 docs) — riesgo **BAJO**: no toca PDFs ni
originales, solo escribe una hoja. El riesgo real del pivot vive en slice 3 (estampado) y se cubre
con el gate del slice 5.

## Estado: PROPUESTA — pendiente de aprobación del firmante.
