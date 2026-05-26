"""Verificador independiente: dado un PDF estampado, recalcula el hash
desde los 8 campos visibles y compara contra el hash esperado.

Implementa el criterio #5 de la spec: 'self-verificacion con solo el papel'.

Uso:
    python scripts/verificar.py <pdf_estampado> [<hash_esperado>]

Si se pasa hash_esperado, lo compara; si no, solo imprime el hash recalculado.

IMPORTANTE: este script NO lee ninguna base de datos ni archivo de
participantes. Solo usa el PDF en input. Es el rol del verificador
publico que tiene el papel y el hash listado en el acta.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraer_campos import extraer
from calcular_hash import calcular, string_canonico, HASH_VERSION


def safe(s: str) -> str:
    return s.encode('ascii', errors='replace').decode('ascii')


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/verificar.py <pdf> [<hash_esperado>]")
        sys.exit(2)
    pdf = Path(sys.argv[1])
    esperado = sys.argv[2] if len(sys.argv) > 2 else None

    if not pdf.exists():
        print(f"[ERROR] No existe: {pdf}")
        sys.exit(2)

    campos = extraer(pdf)
    d = campos.to_dict()
    canonico = string_canonico(d)
    h = calcular(d)

    print(f"[OK] PDF: {safe(pdf.name)}")
    print(f"[OK] Hash version: v{HASH_VERSION}")
    print(f"[OK] Campos extraidos:")
    for k, v in d.items():
        print(f"     {k:<14} = {safe(v)}")
    print(f"[OK] String canonico:")
    print(f"     {safe(canonico)}")
    print(f"[OK] Hash recalculado: {h}")

    if esperado:
        if h == esperado:
            print(f"\n[OK] HASH COINCIDE con el esperado. Certificado VALIDO.")
            sys.exit(0)
        else:
            print(f"\n[FAIL] HASH NO COINCIDE")
            print(f"        esperado:  {esperado}")
            print(f"        calculado: {h}")
            sys.exit(1)


if __name__ == '__main__':
    main()
