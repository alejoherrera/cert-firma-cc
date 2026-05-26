"""Estampa sobre el PDF original:
1. Leyenda 'Acta firmada digitalmente' + hash + etiqueta tecnica,
   en 3 lineas centradas encima del bloque del firmante (~y=502-522).
2. QR en esquina superior-izquierda (60x60pt) con payload JSON
   {nombre, hash, hash_version} para verificacion visual rapida.

NO modifica el PDF de entrada. Escribe a out_path.

Decisiones de diseno (sesion piloto 2026-05-26):
- Layout central (leyenda + hash + etiqueta) en azul CGR + gris discreto.
- QR agregado posteriormente en la misma sesion como complemento.
"""
import io
import json
from pathlib import Path

import fitz
import qrcode

AZUL_CGR = (0.13, 0.18, 0.45)
GRIS_HASH = (0.30, 0.30, 0.30)
GRIS_ETIQUETA = (0.45, 0.45, 0.45)

QR_SIZE_PT = 60     # tamano del QR en puntos PDF
QR_MARGIN_PT = 15   # margen desde esquina superior-izquierda


def _ancho(texto: str, fontsize: float, fontname: str = 'helv') -> float:
    return fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)


def construir_qr_png(payload: str) -> bytes:
    """Genera QR PNG (formato bytes) con correccion media."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def construir_payload_qr(campos: dict, hash_hex: str, hash_version: int) -> str:
    """Payload compacto: solo nombre + hash + version. JSON estable."""
    payload = {
        'v': hash_version,
        'nombre': campos.get('nombre', ''),
        'hash': hash_hex,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def estampar_acta_firmada(
    in_path: Path,
    out_path: Path,
    hash_hex: str,
    campos: dict,
    hash_version: int = 1,
) -> None:
    """Estampa leyenda+hash en el centro + QR en esquina superior-izquierda."""
    doc = fitz.open(in_path)
    try:
        page = doc[0]
        PAGE_W = page.rect.width  # 792 en este layout

        # --- Bloque central: leyenda + hash + etiqueta ---
        leyenda = "Acta firmada digitalmente"
        etiqueta = "Codigo de verificacion (SHA-256):"

        w = _ancho(leyenda, 9)
        page.insert_text(fitz.Point((PAGE_W - w) / 2, 502),
                         leyenda, fontsize=9, fontname='helv', color=AZUL_CGR)

        w = _ancho(hash_hex, 6.5, fontname='cour')
        page.insert_text(fitz.Point((PAGE_W - w) / 2, 514),
                         hash_hex, fontsize=6.5, fontname='cour', color=GRIS_HASH)

        w = _ancho(etiqueta, 5.5)
        page.insert_text(fitz.Point((PAGE_W - w) / 2, 522),
                         etiqueta, fontsize=5.5, fontname='helv', color=GRIS_ETIQUETA)

        # --- QR esquina superior-izquierda ---
        payload = construir_payload_qr(campos, hash_hex, hash_version)
        png = construir_qr_png(payload)
        rect_qr = fitz.Rect(
            QR_MARGIN_PT,
            QR_MARGIN_PT,
            QR_MARGIN_PT + QR_SIZE_PT,
            QR_MARGIN_PT + QR_SIZE_PT,
        )
        page.insert_image(rect_qr, stream=png)

        doc.save(out_path)
    finally:
        doc.close()
