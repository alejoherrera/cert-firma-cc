"""Hash canonico v1 segun CONSTITUTION §7 + ADR-0001.

String canonico: concatenacion de los 8 campos visibles del PDF,
normalizados (NFC + lowercase + trim) y separados por '|' literal.
Sin cedula ni dato externo.
"""
import hashlib
import unicodedata

HASH_VERSION = 1
CAMPOS_CANONICOS_V1 = [
    'nombre', 'curso', 'periodo', 'horas', 'modalidad',
    'fecha_emision', 'firmante', 'jefatura',
]


def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()


def string_canonico(campos: dict) -> str:
    """Construye el string canonico desde un dict con los 8 campos."""
    missing = [c for c in CAMPOS_CANONICOS_V1 if c not in campos]
    if missing:
        raise ValueError(f"Faltan campos canonicos: {missing}")
    return '|'.join(_norm(campos[c]) for c in CAMPOS_CANONICOS_V1)


def calcular(campos: dict) -> str:
    """SHA-256 hex del string canonico v1."""
    return hashlib.sha256(string_canonico(campos).encode('utf-8')).hexdigest()
