# ADR-0001 — El hash canónico NO incluye cédula

**Fecha:** 2026-05-26
**Estado:** Aceptada
**Versión:** 1
**Decisor:** Lic. Juan Alejandro Herrera López, Jefatura A.I, Centro de Capacitación CGR

## Contexto

Cuando se diseñó el esquema de "una acta firmada digitalmente que cubre N certificados, cada certificado lleva su propio hash impreso", surgió la pregunta de qué datos entran al string canónico que se hashea.

La propuesta inicial (en la primera ronda de spec, 2026-05-26) fue:

```
hash = SHA-256(cedula | nombre | curso | periodo | horas | modalidad |
               fecha_emision | firmante | jefatura)
```

con `cedula` como identificador único anti-colisión.

Esto presentaba dos problemas:

1. **El certificado actual del Centro de Capacitación NO trae cédula impresa.** Históricamente solo lleva nombre del participante. Agregar cédula implicaría:
   - Cambiar el diseño visual histórico.
   - Justificar institucionalmente el agregado de PII al documento.
   - Requerir un proceso adicional para obtener cédulas (cruzar con LMS/Excel/Moodle).

2. **Romper la verificabilidad por tercero solo con el papel.** Si la cédula entra al hash pero NO está visible en el cert, un verificador (RH externo, auditor) no puede recalcular el hash sin acceso a `participantes.csv` — que es PII y no se publica. El modelo de "el papel se autoverifica contra el acta firmada" deja de funcionar.

## Alternativas evaluadas

| Opción | Cédula visible en cert | Cédula en hash | Verificable por tercero | Privacidad |
|---|---|---|---|---|
| A | Sí, bajo el nombre | Sí | Sí | Cédula pública en cert |
| B | Solo últimos 4 dígitos | Sí (completa) | Solo por el dueño del cert | Mejor que A |
| C | No visible, embebida en QR | Sí | Sí escaneando QR | El QR es público |
| D ✅ | **No incluida** | **No incluida** | **Sí, solo con el papel** | **Sin PII en el sistema** |

## Decisión

**Opción D.** El string canónico v1 del hash es:

```
canonico = nombre_norm | curso_norm | periodo_norm | horas_norm |
           modalidad_norm | fecha_emision_norm | firmante_norm | jefatura_norm

hash = SHA-256(canonico encoded as UTF-8)
```

donde `_norm` significa: `NFC(lower(trim(campo)))` y `|` es el separador literal.

**Justificación del jefe del Centro** (quote 2026-05-26):
> "por ahora tomemos solo datos que estan en el certificado, es dificil un choque de nombre apellido curso y tiempo"

Es decir: en una cohorte específica (un curso, un período concreto, unas horas concretas) la combinación nombre+apellido+curso+período es prácticamente única. El riesgo de colisión existe pero es muy bajo y manejable caso por caso.

## Consecuencias

### Positivas

- El sistema NO necesita `participantes.csv` ni cruce externo. Cada PDF es self-contained.
- Un tercero puede verificar leyendo solo el cert + el acta firmada.
- No se introduce PII (cédula) al ecosistema del sistema, simplificando privacidad/cumplimiento.
- El diseño histórico del certificado se preserva sin cambios.

### Negativas / riesgos

- **Riesgo de homónimos** en el mismo curso/cohorte → hash idéntico para dos personas distintas. Si ocurre:
  - En el acta aparecerían dos entradas con el mismo hash y el mismo nombre. El acta sigue siendo válida criptográficamente, pero ambigua sobre a cuál persona corresponde cada cert.
  - **Mitigación caso-por-caso:** emitir certificado con un correlativo manual añadido al nombre (ej. "Juan Pérez Pérez (cédula terminada en 0242)") solo cuando se detecte la colisión real. Documentar en `data/output/lote_<ts>/no_match.csv` o nota del jefe.
- Si en el futuro se decide cambiar el modelo (agregar cédula, correlativo, etc.):
  - **Bumpear `hash_version` a 2.**
  - Crear ADR-0002 que documente la decisión.
  - Migrar los lotes nuevos al esquema v2; los lotes v1 firmados quedan inmutables.

## Vigencia

Esta ADR aplica a la fase piloto. Si al promover a producción institucional el área legal/auditoría exige identificador único, se revisita con ADR posterior.

## Referencias

- `CONSTITUTION.md` §7 (reglas de negocio codificadas — hash canónico v1).
- `docs/specs/2026-05-26_acta_hash_certificados.md` (spec inicial — actualizada para reflejar esta decisión).
- Hilo de decisión: sesión 2026-05-26 con asistente Claude Code.
