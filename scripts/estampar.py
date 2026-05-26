"""Estampa el hash SHA-256 + leyenda 'Acta firmada digitalmente' sobre un PDF.

Ubicacion fija (decidida 2026-05-26 sesion piloto): centrada en el espacio
entre la fecha de emision (~y=485) y el bloque del firmante (~y=528).

NO modifica el PDF de entrada. Escribe a out_path.
"""
from pathlib import Path

import fitz

# Color azul CGR aproximado (mismo tono del header del cert)
AZUL_CGR = (0.13, 0.18, 0.45)
GRIS_HASH = (0.30, 0.30, 0.30)
GRIS_ETIQUETA = (0.45, 0.45, 0.45)


def _ancho(texto: str, fontsize: float, fontname: str = 'helv') -> float:
    return fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)


def estampar_acta_firmada(in_path: Path, out_path: Path, hash_hex: str) -> None:
    """Estampa leyenda + hash + etiqueta en 3 lineas centradas (y=502, 514, 522)."""
    doc = fitz.open(in_path)
    try:
        page = doc[0]
        PAGE_W = page.rect.width  # 792 en este layout

        leyenda = "Acta firmada digitalmente"
        etiqueta = "Codigo de verificacion (SHA-256):"

        # Linea 1: leyenda
        w = _ancho(leyenda, 9)
        page.insert_text(
            fitz.Point((PAGE_W - w) / 2, 502),
            leyenda, fontsize=9, fontname='helv', color=AZUL_CGR,
        )

        # Linea 2: hash
        w = _ancho(hash_hex, 6.5, fontname='cour')
        page.insert_text(
            fitz.Point((PAGE_W - w) / 2, 514),
            hash_hex, fontsize=6.5, fontname='cour', color=GRIS_HASH,
        )

        # Linea 3: etiqueta
        w = _ancho(etiqueta, 5.5)
        page.insert_text(
            fitz.Point((PAGE_W - w) / 2, 522),
            etiqueta, fontsize=5.5, fontname='helv', color=GRIS_ETIQUETA,
        )

        doc.save(out_path)
    finally:
        doc.close()
