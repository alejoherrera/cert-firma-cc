/**
 * String canonico v1 + SHA-256 en JavaScript, paridad exacta con
 * scripts/calcular_hash.py (CONSTITUTION 7 + ADR-0001).
 *
 * Portable: corre en Google Apps Script (runtime V8) y en Node.
 * - Construccion del string canonico: identica en ambos.
 * - SHA-256: en GAS via Utilities.computeDigest; en Node via crypto.
 *
 * El hash debe coincidir byte-a-byte con la implementacion Python; ver
 * gas/test_parity.mjs y ADR-0002 (gate de auditoria).
 */

// Orden NO-negociable de los 8 campos (igual que CAMPOS_CANONICOS_V1 en Python).
var CAMPOS_CANONICOS_V1 = [
  'nombre', 'curso', 'periodo', 'horas', 'modalidad',
  'fecha_emision', 'firmante', 'jefatura',
];

var HASH_VERSION = 1;

/** NFC -> trim -> lowercase, igual que _norm() en Python (normalize, strip, lower). */
function norm(s) {
  return String(s).normalize('NFC').trim().toLowerCase();
}

/** Construye el string canonico desde un objeto con los 8 campos. */
function stringCanonico(campos) {
  var missing = CAMPOS_CANONICOS_V1.filter(function (c) {
    return !(c in campos);
  });
  if (missing.length) {
    throw new Error('Faltan campos canonicos: ' + missing.join(', '));
  }
  return CAMPOS_CANONICOS_V1.map(function (c) {
    return norm(campos[c]);
  }).join('|');
}

function _toHex(bytes) {
  // bytes: array de enteros con signo (GAS) o Uint8Array/Buffer (Node).
  var hex = '';
  for (var i = 0; i < bytes.length; i++) {
    var b = bytes[i] & 0xff;
    hex += (b < 16 ? '0' : '') + b.toString(16);
  }
  return hex;
}

/** SHA-256 hex del string canonico. Detecta entorno (GAS vs Node). */
function calcular(campos) {
  var canon = stringCanonico(campos);
  if (typeof Utilities !== 'undefined' && Utilities.computeDigest) {
    // Google Apps Script
    var raw = Utilities.computeDigest(
      Utilities.DigestAlgorithm.SHA_256, canon, Utilities.Charset.UTF_8);
    return _toHex(raw);
  }
  // Node / otro
  var crypto = require('crypto');
  return crypto.createHash('sha256').update(canon, 'utf8').digest('hex');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CAMPOS_CANONICOS_V1, HASH_VERSION, norm, stringCanonico, calcular };
}
