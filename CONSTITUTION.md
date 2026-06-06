# Constitución — cert-firma-cc

**Versión:** 2.0.0
**Fecha:** 2026-06-05 (versión inicial 2026-05-26)
**Responsable institucional:** Lic. Juan Alejandro Herrera López, Jefatura A.I, Centro de Capacitación CGR

Documento fundacional del proyecto. Toda spec posterior debe declarar cumplimiento constitucional al inicio.

---

## 1. Propósito

Automatizar la emisión legalmente verificable de certificados de cursos del Centro de Capacitación de la CGR sin requerir firma digital por certificado. El centro emite N certificados; el jefe firma digitalmente **una sola acta** que contiene la lista de hashes de todos los certificados del lote.

Cada certificado lleva impreso su propio hash criptográfico, permitiendo verificación independiente contra el acta firmada.

## 2. Alcance institucional

- **Universo:** CGR institucional **en fase de prueba/piloto**. Por estar en piloto, repo en GitHub personal del responsable (`alejoherrera/cert-firma-cc`), no en `cgrcostarica/`. Al validarse, se planificará migración a infraestructura institucional.
- **Cuenta de Drive:** `alejandro.herrera@cgr.go.cr` (Workspace `cgr.go.cr`), readonly via OAuth token existente (`C:\Users\aleja\token_cgr.json` del proyecto GCP `loggin`).
- **Datos cubiertos:** Solo certificados emitidos por el Centro de Capacitación CGR. PII (cédulas, nombres) nunca abandona el equipo del responsable durante la fase piloto.

## 3. Stack tecnológico no-negociable

| Componente | Decisión | Razón |
|---|---|---|
| Lenguaje | Python 3.11+ | Ya en uso por el responsable; ecosistema PDF maduro |
| PDF read | PyMuPDF (`fitz`) | Lectura robusta y extracción de texto con posiciones |
| PDF overlay | PyMuPDF (overlay nativo) | Evita doble librería; reportlab solo si insuficiente |
| Hash | SHA-256 stdlib | Algoritmo no-negociable; misma familia que firma digital BCCR |
| Drive | `google-api-python-client` + OAuth token existente | Mismo mecanismo que `resoluciones_DCP` |
| Acta firmable | **Fuera del scope del sistema** | El responsable arma el acta y la firma con el cliente del BCCR |

**Enmienda 2.0.0 (2026-06-05, ADR-0002):** se incorpora **Google Apps Script (JavaScript, runtime
V8)** como runtime de producción del pipeline, en adición a Python. El motor Python/PyMuPDF **no se
elimina**: permanece como oráculo de verificación/auditoría y fallback (ver ADR-0002 §Mitigación).
El hash se reimplementa en JS con paridad byte-a-byte exigida contra la implementación Python.

## 4. Reglas de datos y seguridad

1. **Originales en Drive son intocables.** El sistema opera readonly desde Drive y escribe únicamente a `data/output/` local. Si en algún momento se necesita escribir a Drive, requiere enmienda constitucional.

   **Enmienda 2.0.0 (2026-06-05, ADR-0002):** se autoriza que el runtime Apps Script **escriba a
   Drive** dentro del Workspace `cgr.go.cr` — exclusivamente PDF estampados (overlay, no alteran el
   texto original) y la hoja/acta del lote en carpetas de salida; **nunca** sobre los PDF
   originales de matrícula (siguen intocables: solo `list`/`get`/copia). Scope OAuth ampliado a
   `drive` + `spreadsheets`. El PII permanece dentro del Workspace institucional donde ya residen
   los originales. **Riesgo de verificabilidad asumido** por el firmante: ver ADR-0002 §Riesgo.
2. **PII (cédulas, nombres) jamás se commitea.** `data/input/`, `data/output/` y `data/participantes*.csv` están en `.gitignore`. Auditar el repo previo a cada `git push`.
3. **Hash canónico SHA-256.** Algoritmo y formato del string canónico definidos en el spec del feature. Cambios al string canónico = nueva versión del campo de hash en el cert + ADR explicando migración.
4. **Trazabilidad del lote.** Cada ejecución produce: PDFs estampados, `listado_hashes.csv`, `listado_hashes.json`, y un `manifest.json` con timestamp, git commit, versión del string canónico, total de certificados, hash del propio listado.

## 5. Reglas de calidad

- **Smoke con data real obligatorio.** Cualquier extractor de campos del PDF debe validarse contra ≥1 PDF real antes de mergear (regla global del responsable, ver caso 2026-05-19 agentes_juridicos).
- **SDD obligatorio.** Cada feature funcional requiere spec light ≤ 10 líneas en `docs/specs/YYYY-MM-DD_<slug>.md` ANTES de codear (R36 del responsable).
- **Tests mínimos por feature:** smoke del happy path + 1 edge case (ej. nombre con tilde, doble apellido, modalidad "Presencial" vs "Virtual").
- **Lint:** `ruff` antes de commit.
- **Encoding seguro Windows:** logs/print sin emojis (`[OK]`, `[ERROR]`); regla R5 del responsable.
- **Versionamiento explícito:** semver en `pyproject.toml` + tag git por release.

## 6. Roles

- **Jefe del Centro / firmante:** Lic. Juan Alejandro Herrera López. Único firmante autorizado del acta. Decide cuándo el piloto pasa a producción.
- **Operador del pipeline (fase piloto):** el mismo jefe. Corre los scripts en su equipo.
- **Verificador (tercero):** auditor, RH externo, etc. En fase piloto la verificación es manual (recalcular hash y comparar contra acta firmada). Fase 2 considerará verificador automatizado.

## 7. Reglas de negocio codificadas

- **Alcance del acta:** una acta por curso/grupo terminado (decidido 2026-05-26).
- **String canónico del hash (v1):** `nombre_normalizado|curso|periodo|horas|modalidad|fecha_emision|firmante|jefatura`
  - Normalización: NFC, lowercase, trim por campo, separador `|` literal.
  - **Solo datos visibles en el certificado.** No incluye cédula ni ningún dato externo al PDF (ver `docs/architecture/adr-0001-hash-sin-cedula.md`).
  - `hash_version = 1`. Si en el futuro se altera la fórmula: nueva ADR + bump de `hash_version` en el cert y el listado.
- **Identificador único de persona:** no hay. Se asume que en un curso/cohorte la combinación nombre+curso+período es prácticamente única (justificación en ADR-0001). Si aparece colisión real, se gestiona caso por caso emitiendo un correlativo manual.
- **Mostrar el hash al lector:** sí (posición a definir en spec del feature inicial). El hash invisible (solo metadata) está prohibido en la fase piloto: el responsable quiere que un humano pueda leer el hash en papel.
- **Verificabilidad por tercero:** un tercero debe poder recalcular el hash leyendo únicamente el certificado en papel (sin acceso a bases externas). Por eso el string canónico solo usa datos visibles.

## 8. Operación

- **Observabilidad mínima:** cada corrida produce un log en `data/output/<timestamp>/run.log` con qué PDF entró, qué hash salió, errores.
- **Backups:** los originales viven en Drive (responsabilidad institucional CGR). Las salidas locales se respaldan según política del responsable.
- **Presupuesto:** $0 mientras corra local. Si en fase 2 se hospeda verificador web: nuevo ADR de hospedaje.

## 9. Gobernanza

- **Jerarquía de precedencia** (en caso de conflicto): esta Constitución > `CLAUDE.md` global > `CLAUDE.md` del proyecto > spec del feature > código.
- **Enmiendas:** modificación de este documento requiere bump de versión (`1.0.0` → `1.1.0` para adiciones, `2.0.0` para cambios incompatibles) + nota al final indicando fecha y razón.
- **Promoción a producción institucional:** cuando el piloto se valide, ADR específico planeará migración a `cgrcostarica/cert-firma-cc` y proyecto GCP institucional.

---

## Historial de enmiendas

- **1.0.0 — 2026-05-26** — Versión inicial. Proyecto greenfield, fase piloto.
- **1.1.0 — 2026-05-26** — §7 actualizado: el string canónico v1 NO incluye cédula. Decisión documentada en ADR-0001. Razón: mantener el diseño histórico del certificado intacto + verificabilidad por tercero con solo el papel.
- **2.0.0 — 2026-06-05** — Cambio incompatible. Pivot de runtime a Google Apps Script (ADR-0002):
  §3 incorpora Apps Script como runtime (Python queda como oráculo/fallback); §4.1 autoriza
  escritura a Drive (PDF estampados + acta Sheet) dentro del Workspace `cgr.go.cr` con scope OAuth
  ampliado. El firmante asume explícitamente el riesgo de verificabilidad de calcular el hash desde
  datos reconstruidos en vez del texto impreso, mitigado por auditoría con `verificar.py`.
