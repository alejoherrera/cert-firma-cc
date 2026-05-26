"""Smoke test del extractor de campos contra UN PDF real.

Uso:
    python scripts/smoke_extractor.py [path_a_pdf]

Default: data/input/CERTIFICADOS PRUEBA-6.pdf

Falla con exit code != 0 si:
  - Algun campo viene vacio
  - El layout no calza con lo esperado
  - El PDF no existe

Regla global del responsable: cualquier funcion que mapee shape externo
(PDF) a shape interno debe smoke-testearse con UN fixture REAL antes de
mergear. NO asumir keys/posiciones.
"""
import sys
from pathlib import Path

# Permite correr el script directamente (sin instalar paquete)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extraer_campos import extraer

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPO_ROOT / 'data' / 'input' / 'CERTIFICADOS PRUEBA-6.pdf'


def main():
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = DEFAULT_PDF

    if not pdf_path.exists():
        print(f"[ERROR] No existe el PDF: {pdf_path}")
        sys.exit(2)

    print(f"[INFO] Smoke testing extractor con: {pdf_path.name}")
    print()

    try:
        campos = extraer(pdf_path)
    except ValueError as e:
        print(f"[FAIL] Extraccion fallo: {e}")
        sys.exit(1)

    print(f"[OK] Extraccion exitosa. 8 campos canonicos:")
    print()
    d = campos.to_dict()
    for k, v in d.items():
        marker = "  " if v else "!!"
        print(f"  {marker} {k:<14} = {v!r}")

    # Validar
    vacios = [k for k, v in d.items() if not v]
    if vacios:
        print(f"\n[FAIL] Campos vacios: {vacios}")
        sys.exit(1)

    print(f"\n[OK] Smoke PASSED. Extractor listo para pipeline.")


if __name__ == '__main__':
    main()
