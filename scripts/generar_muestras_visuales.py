"""Genera la muestra visual del certificado con la leyenda
'Acta firmada digitalmente' + hash SHA-256 en el espacio encima del
bloque del firmante (entre 'San Jose, 25 de mayo, 2026' y 'Alejandro
Herrera Lopez').

Decision de diseno 2026-05-26: descartar variante QR; ubicar leyenda + hash
en el espacio existente entre fecha de emision y firmante.

Hash v1 segun ADR-0001: solo datos visibles del PDF (sin cedula).

Output: data/output/muestras_visuales/variante_acta_firmada.pdf
"""
import hashlib
import shutil
import unicodedata
from pathlib import Path

import fitz

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PDF = REPO_ROOT / 'data' / 'input' / 'CERTIFICADOS PRUEBA-6.pdf'
OUT_DIR = REPO_ROOT / 'data' / 'output' / 'muestras_visuales'

# Solo campos visibles del PDF (ADR-0001).
DATOS = {
    'nombre': 'Jonathan Carvajal Carvajal',
    'curso': 'Gestion de Fideicomisos Publicos para Auditorias Internas',
    'periodo': 'del 19 de febrero al 20 de abril de 2026',
    'horas': '4',
    'modalidad': 'Virtual',
    'fecha_emision': 'San Jose, 25 de mayo, 2026',
    'firmante': 'Alejandro Herrera Lopez',
    'jefatura': 'Jefatura A.I, Centro de Capacitacion',
}
HASH_VERSION = 1
CAMPOS_CANONICOS_V1 = ['nombre', 'curso', 'periodo', 'horas', 'modalidad',
                       'fecha_emision', 'firmante', 'jefatura']

# Color azul CGR aproximado (mismo tono del header del cert)
AZUL_CGR = (0.13, 0.18, 0.45)
GRIS_HASH = (0.30, 0.30, 0.30)


def normalizar(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()


def calcular_hash(d: dict) -> str:
    """SHA-256 del string canonico v1 (CONSTITUTION §7 + ADR-0001)."""
    canonico = '|'.join(normalizar(d[c]) for c in CAMPOS_CANONICOS_V1)
    return hashlib.sha256(canonico.encode('utf-8')).hexdigest()


def _ancho_helv(texto: str, fontsize: float, fontname: str = 'helv') -> float:
    return fitz.get_text_length(texto, fontname=fontname, fontsize=fontsize)


def variante_acta_firmada(doc_path: Path, out_path: Path, hash_hex: str):
    """Leyenda 'Acta firmada digitalmente' + hash SHA-256 centrados en el espacio
    entre la fecha de emision (termina ~y=485) y el firmante (empieza ~y=528).
    """
    doc = fitz.open(doc_path)
    page = doc[0]
    PAGE_W = page.rect.width  # 792

    leyenda = "Acta firmada digitalmente"
    etiqueta_hash = "Codigo de verificacion (SHA-256):"
    hash_texto = hash_hex

    # Linea 1: leyenda en azul CGR, 9pt, centrada en y=502
    w1 = _ancho_helv(leyenda, 9)
    page.insert_text(
        fitz.Point((PAGE_W - w1) / 2, 502),
        leyenda,
        fontsize=9,
        fontname='helv',
        color=AZUL_CGR,
    )

    # Linea 2: hash centrado, 6.5pt monoespaciado gris, en y=514
    w2 = _ancho_helv(hash_texto, 6.5, fontname='cour')
    page.insert_text(
        fitz.Point((PAGE_W - w2) / 2, 514),
        hash_texto,
        fontsize=6.5,
        fontname='cour',
        color=GRIS_HASH,
    )

    # Linea 3 (opcional): mini-etiqueta gris muy chica indicando que es el codigo de verificacion
    w3 = _ancho_helv(etiqueta_hash, 5.5)
    page.insert_text(
        fitz.Point((PAGE_W - w3) / 2, 522),
        etiqueta_hash,
        fontsize=5.5,
        fontname='helv',
        color=(0.45, 0.45, 0.45),
    )

    doc.save(out_path)
    doc.close()


def main():
    if not INPUT_PDF.exists():
        raise SystemExit(f"[ERROR] No existe {INPUT_PDF}. Corre primero scripts/bajar_certificados.py")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    h = calcular_hash(DATOS)
    canonico = '|'.join(normalizar(DATOS[c]) for c in CAMPOS_CANONICOS_V1)
    print(f"[OK] String canonico v1 (sin cedula):")
    print(f"     {canonico}")
    print(f"[OK] Hash SHA-256: {h}")
    print()

    out = OUT_DIR / 'variante_acta_firmada.pdf'
    try:
        variante_acta_firmada(INPUT_PDF, out, h)
        print(f"[OK] Muestra -> {out.name} ({out.stat().st_size:,} bytes)")
    except PermissionError:
        # Fallback: si el archivo esta abierto, escribir con sufijo timestamp
        from datetime import datetime
        ts = datetime.now().strftime('%H%M%S')
        out_fallback = OUT_DIR / f'variante_acta_firmada_{ts}.pdf'
        variante_acta_firmada(INPUT_PDF, out_fallback, h)
        print(f"[WARN] variante_acta_firmada.pdf esta abierto. Escribi a {out_fallback.name}")
    print(f"[OK] Carpeta: {OUT_DIR}")


if __name__ == '__main__':
    main()
