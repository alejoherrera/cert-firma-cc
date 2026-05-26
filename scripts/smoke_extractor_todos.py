"""Smoke del extractor contra los 15 PDFs del lote. Falla si alguno no extrae OK."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraer_campos import extraer

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO_ROOT / 'data' / 'input'


def main():
    pdfs = sorted(INPUT_DIR.glob('*.pdf'))
    if not pdfs:
        print("[ERROR] No hay PDFs en data/input/")
        sys.exit(2)

    print(f"[INFO] Smoke contra {len(pdfs)} PDFs")
    print()

    fallos = []
    nombres = []
    for pdf in pdfs:
        # Print solo ASCII para evitar UnicodeEncodeError en Windows console
        nombre_safe = pdf.name.encode('ascii', errors='replace').decode('ascii')
        try:
            campos = extraer(pdf)
            nombres.append(campos.nombre)
            print(f"  [OK] {nombre_safe:<40} -> {campos.nombre.encode('ascii', errors='replace').decode('ascii')}")
        except Exception as e:
            print(f"  [FAIL] {nombre_safe:<40} -> {e}")
            fallos.append((pdf.name, str(e)))

    print()
    print(f"[OK] Extraidos: {len(pdfs) - len(fallos)}/{len(pdfs)}")
    if fallos:
        print(f"[FAIL] Fallaron: {len(fallos)}")
        sys.exit(1)
    # Reporte de duplicados de nombre (advertencia, no error)
    from collections import Counter
    repetidos = {n: c for n, c in Counter(nombres).items() if c > 1}
    if repetidos:
        print(f"[WARN] Nombres repetidos en el lote (esperable en data de prueba):")
        for n, c in repetidos.items():
            print(f"       {n.encode('ascii', errors='replace').decode('ascii')}: {c}")


if __name__ == '__main__':
    main()
