"""Hash canonico v2 segun CONSTITUTION §7 + ADR-0001 + ADR-0003.

String canonico: concatenacion de los 7 campos visibles del PDF,
normalizados (NFC + lowercase + trim) y separados por '|' literal.
Sin cedula (ADR-0001) ni fecha_emision (ADR-0003) ni dato externo.

fecha_emision se sigue extrayendo y mostrando en el acta; solo NO entra al hash.
"""
import hashlib
import unicodedata

HASH_VERSION = 2

# Set canonico activo (v2, ADR-0003): 7 campos, sin fecha_emision.
CAMPOS_CANONICOS_V2 = [
    'nombre', 'curso', 'periodo', 'horas', 'modalidad',
    'firmante', 'jefatura',
]
CAMPOS_CANONICOS = CAMPOS_CANONICOS_V2  # alias del set activo

# Historico congelado (v1, ADR-0001): incluia fecha_emision. NO usar para hashear.
# Se conserva para auditar/identificar lotes v1 ya estampados (mayo 2026).
CAMPOS_CANONICOS_V1 = [
    'nombre', 'curso', 'periodo', 'horas', 'modalidad',
    'fecha_emision', 'firmante', 'jefatura',
]


def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()


def string_canonico(campos: dict) -> str:
    """Construye el string canonico v2 desde un dict (campos extra se ignoran)."""
    missing = [c for c in CAMPOS_CANONICOS if c not in campos]
    if missing:
        raise ValueError(f"Faltan campos canonicos: {missing}")
    return '|'.join(_norm(campos[c]) for c in CAMPOS_CANONICOS)


def calcular(campos: dict) -> str:
    """SHA-256 hex del string canonico v2."""
    return hashlib.sha256(string_canonico(campos).encode('utf-8')).hexdigest()
