/**
 * Test de paridad hash JS <-> Python (ADR-0002, criterio de cierre 1).
 *
 * Lee el listado_hashes.json del lote mas reciente (generado por el motor
 * Python) y verifica que la implementacion JS produce, para cada registro:
 *   - el mismo string_canonico, y
 *   - el mismo hash_sha256.
 *
 * Uso: node gas/test_parity.mjs
 * Exit 0 si todos coinciden; 1 si alguno difiere.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { stringCanonico, calcular, HASH_VERSION } = require('./canonical_hash.js');

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const outBase = join(repoRoot, 'data', 'output');

const lotes = readdirSync(outBase)
  .filter((n) => n.startsWith('lote_'))
  .sort()
  .reverse();
if (!lotes.length) {
  console.error('[ERROR] No hay lotes en data/output');
  process.exit(2);
}
const listado = join(outBase, lotes[0], 'listado_hashes.json');
const registros = JSON.parse(readFileSync(listado, 'utf8'));

// Guard: el lote leido debe ser de la version de hash actual. Un listado viejo
// (p.ej. v1, con fecha_emision en el hash) daria falsos FAIL silenciosos.
const verLote = registros[0] && registros[0].hash_version;
if (verLote !== HASH_VERSION) {
  console.error(`[ERROR] El lote ${lotes[0]} es hash_version=${verLote}, ` +
    `pero la implementacion es v${HASH_VERSION}. Regenera el lote con generar_acta.py.`);
  process.exit(2);
}

let fallos = 0;
for (const r of registros) {
  // v2 (ADR-0003): sin fecha_emision en el hash.
  const campos = {
    nombre: r.nombre, curso: r.curso, periodo: r.periodo, horas: r.horas,
    modalidad: r.modalidad, firmante: r.firmante, jefatura: r.jefatura,
  };
  const canonJs = stringCanonico(campos);
  const hashJs = calcular(campos);
  const okCanon = canonJs === r.string_canonico;
  const okHash = hashJs === r.hash_sha256;
  const estado = okCanon && okHash ? '[OK]  ' : '[FAIL]';
  console.log(`${estado} ${r.nombre}`);
  if (!okHash) {
    console.log(`        py : ${r.hash_sha256}`);
    console.log(`        js : ${hashJs}`);
    fallos++;
  } else if (!okCanon) {
    console.log(`        canon difiere`);
    fallos++;
  }
}

console.log(`\nParidad: ${registros.length - fallos}/${registros.length} coinciden`);
process.exit(fallos ? 1 : 0);
