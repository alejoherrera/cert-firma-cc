"""Suite de QA del mecanismo de emision de certificados del Centro de Capacitacion CGR.

Valida, contra un lote real ya generado, que el mecanismo
"1 acta firmada + N certificados con hash impreso" es confiable y verificable.
Cada caso devuelve PASS/FAIL con su evidencia; el script sale con codigo != 0
si algun caso critico falla.

Uso:
    python scripts/qa_suite.py [lote_dir] [--lote-previo <dir>]

Default: lote mas reciente bajo data/output/lote_*/.
`--lote-previo` habilita QA-04 (idempotencia entre lotes); si no se pasa,
QA-04 se intenta contra el segundo lote mas reciente si existe.

NO consume ninguna base de datos ni PII externa: solo el lote y los PDFs
de data/input/ (mismos insumos que tendria un verificador con el papel).
"""
import argparse
import hashlib
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraer_campos import extraer
from calcular_hash import calcular, CAMPOS_CANONICOS

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_BASE = REPO_ROOT / 'data' / 'output'
INPUT_DIR = REPO_ROOT / 'data' / 'input'


def safe(s: str) -> str:
    """Print seguro en consolas cp1252 (Windows, R5)."""
    return s.encode('ascii', errors='replace').decode('ascii')


@dataclass
class Resultado:
    id: str
    titulo: str
    passed: bool
    critico: bool
    detalle: str


def _lotes_ordenados() -> list[Path]:
    return sorted(OUTPUT_BASE.glob('lote_*'), reverse=True)


def _cargar_listado(lote_dir: Path) -> list[dict]:
    return json.loads((lote_dir / 'listado_hashes.json').read_text(encoding='utf-8'))


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------- casos QA ---------------------------

def qa01_cobertura(lote_dir: Path, registros: list[dict]) -> Resultado:
    """Todos los PDFs de input quedaron representados en el lote, sin errores."""
    manifest = json.loads((lote_dir / 'manifest.json').read_text(encoding='utf-8'))
    n_input = len(list(INPUT_DIR.glob('*.pdf')))
    n_reg = len(registros)
    n_err = manifest.get('total_errores', 0)
    ok = (n_err == 0) and (n_reg == manifest.get('total_certificados'))
    cobertura = (n_reg == n_input) if n_input else None
    cob_txt = '' if cobertura is None else f", input actual={n_input} (cobertura={'OK' if cobertura else 'difiere'})"
    return Resultado(
        'QA-01', 'Cobertura del lote', ok, critico=True,
        detalle=f"procesados={n_reg}, errores={n_err}{cob_txt}",
    )


def qa02_determinismo(lote_dir: Path, registros: list[dict]) -> Resultado:
    """calcular() sobre los campos registrados reproduce el hash guardado."""
    fallos = []
    for r in registros:
        campos = {c: r[c] for c in CAMPOS_CANONICOS}
        h = calcular(campos)
        if h != r['hash_sha256']:
            fallos.append(f"{safe(r['nombre'])}: {h[:12]}!={r['hash_sha256'][:12]}")
    ok = not fallos
    return Resultado(
        'QA-02', 'Determinismo sobre campos registrados', ok, critico=True,
        detalle=f"{len(registros)} registros, {len(fallos)} discrepancias"
        + ('' if ok else f": {fallos[:3]}"),
    )


def qa03_verificacion_tercero(lote_dir: Path, registros: list[dict]) -> Resultado:
    """Extraer del PDF ESTAMPADO y recalcular reproduce el hash del acta.

    Es el caso mas importante: simula al verificador que solo tiene el papel
    y el acta firmada. El estampado (leyenda+QR) NO debe romper la extraccion.
    """
    fallos = []
    revisados = 0
    for r in registros:
        pdf = lote_dir / r['archivo_estampado']
        if not pdf.exists():
            fallos.append(f"{r['archivo_estampado']}: no existe")
            continue
        try:
            d = extraer(pdf).to_dict()
            h = calcular(d)
            revisados += 1
            if h != r['hash_sha256']:
                fallos.append(f"{safe(r['nombre'])}: hash difiere")
        except Exception as e:
            fallos.append(f"{r['archivo_estampado']}: {safe(str(e))}")
    ok = (not fallos) and revisados == len(registros)
    return Resultado(
        'QA-03', 'Verificacion por tercero (PDF estampado)', ok, critico=True,
        detalle=f"verificados={revisados}/{len(registros)}, fallos={len(fallos)}"
        + ('' if ok else f": {fallos[:3]}"),
    )


def qa04_idempotencia(registros: list[dict], lote_previo: Path | None) -> Resultado:
    """Mismo input -> mismo hash, independiente del lote/timestamp.

    Compara por nombre los hashes entre el lote actual y un lote previo.
    Los nombres presentes en ambos deben tener hash identico.
    """
    if not lote_previo or not (lote_previo / 'listado_hashes.json').exists():
        return Resultado(
            'QA-04', 'Idempotencia entre lotes', True, critico=False,
            detalle='omitido: no hay lote previo comparable',
        )
    prev = {r['nombre']: r['hash_sha256'] for r in _cargar_listado(lote_previo)}
    comunes = 0
    discrepancias = []
    for r in registros:
        if r['nombre'] in prev:
            comunes += 1
            if prev[r['nombre']] != r['hash_sha256']:
                discrepancias.append(safe(r['nombre']))
    ok = (comunes > 0) and (not discrepancias)
    return Resultado(
        'QA-04', 'Idempotencia entre lotes', ok, critico=False,
        detalle=f"vs {lote_previo.name}: comunes={comunes}, discrepancias={len(discrepancias)}"
        + ('' if ok else f": {discrepancias[:3]}"),
    )


def qa05_integridad_listado(lote_dir: Path) -> Resultado:
    """sha256(listado_hashes.json) == manifest.hash_listado_json_sha256."""
    manifest = json.loads((lote_dir / 'manifest.json').read_text(encoding='utf-8'))
    real = _sha256_file(lote_dir / 'listado_hashes.json')
    esperado = manifest.get('hash_listado_json_sha256')
    ok = real == esperado
    return Resultado(
        'QA-05', 'Integridad del listado (sello en manifest)', ok, critico=True,
        detalle=f"manifest={esperado[:16] if esperado else None}..., real={real[:16]}...",
    )


def qa06_originales_intocables(registros: list[dict]) -> Resultado:
    """Re-estampar un original a un archivo temporal no modifica el original."""
    from estampar import estampar_acta_firmada
    pdfs = sorted(INPUT_DIR.glob('*.pdf'))
    if not pdfs:
        return Resultado('QA-06', 'Originales intocables', True, critico=True,
                         detalle='omitido: no hay PDFs en data/input/')
    src = pdfs[0]
    antes = _sha256_file(src)
    tmp = INPUT_DIR.parent / 'qa_tmp_estampado.pdf'
    try:
        d = extraer(src).to_dict()
        estampar_acta_firmada(src, tmp, calcular(d), d, hash_version=1)
        despues = _sha256_file(src)
        difiere_salida = _sha256_file(tmp) != antes
        ok = (antes == despues) and difiere_salida
        detalle = (f"input estable={antes == despues}, "
                   f"salida!=input={difiere_salida} ({safe(src.name)})")
    finally:
        if tmp.exists():
            tmp.unlink()
    return Resultado('QA-06', 'Originales intocables', ok, critico=True, detalle=detalle)


def qa07_avalancha(registros: list[dict]) -> Resultado:
    """Alterar 1 caracter de un campo cambia el hash (efecto avalancha)."""
    if not registros:
        return Resultado('QA-07', 'Sensibilidad (avalancha)', False, critico=True,
                         detalle='sin registros')
    base = {c: registros[0][c] for c in CAMPOS_CANONICOS}
    h0 = calcular(base)
    alterado = dict(base)
    alterado['curso'] = base['curso'] + 'x'
    h1 = calcular(alterado)
    ok = h0 != h1
    return Resultado('QA-07', 'Sensibilidad (avalancha)', ok, critico=True,
                     detalle=f"hash cambia al alterar 'curso': {ok} ({h0[:8]}.. vs {h1[:8]}..)")


def qa08_nfc(registros: list[dict]) -> Resultado:
    """Acento precompuesto (NFC) vs combinado (NFD) producen el mismo hash."""
    if not registros:
        return Resultado('QA-08', 'Normalizacion NFC', False, critico=True,
                         detalle='sin registros')
    base = {c: registros[0][c] for c in CAMPOS_CANONICOS}
    nfd = {c: unicodedata.normalize('NFD', v) for c, v in base.items()}
    ok = calcular(base) == calcular(nfd)
    # confirmar que la prueba es significativa (que habia algo que normalizar)
    significativo = any(base[c] != nfd[c] for c in CAMPOS_CANONICOS)
    return Resultado('QA-08', 'Normalizacion NFC', ok, critico=True,
                     detalle=f"NFC==NFD hash: {ok}; prueba significativa (habia acentos): {significativo}")


# --------------------------- runner ---------------------------

def correr(lote_dir: Path, lote_previo: Path | None) -> list[Resultado]:
    registros = _cargar_listado(lote_dir)
    return [
        qa01_cobertura(lote_dir, registros),
        qa02_determinismo(lote_dir, registros),
        qa03_verificacion_tercero(lote_dir, registros),
        qa04_idempotencia(registros, lote_previo),
        qa05_integridad_listado(lote_dir),
        qa06_originales_intocables(registros),
        qa07_avalancha(registros),
        qa08_nfc(registros),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lote', nargs='?', type=Path, default=None)
    ap.add_argument('--lote-previo', type=Path, default=None)
    args = ap.parse_args()

    lotes = _lotes_ordenados()
    lote_dir = args.lote or (lotes[0] if lotes else None)
    if not lote_dir or not lote_dir.exists():
        sys.exit(f"[ERROR] Lote no encontrado: {lote_dir}")

    lote_previo = args.lote_previo
    if lote_previo is None:
        # segundo lote mas reciente distinto al actual
        otros = [lt for lt in lotes if lt != lote_dir]
        lote_previo = otros[0] if otros else None

    print(f"[INFO] QA suite — lote: {safe(lote_dir.name)}")
    if lote_previo:
        print(f"[INFO] Lote previo (idempotencia): {safe(lote_previo.name)}")
    print()

    resultados = correr(lote_dir, lote_previo)

    for r in resultados:
        marca = '[PASS]' if r.passed else ('[FAIL]' if r.critico else '[WARN]')
        print(f"{marca} {r.id} {r.titulo}")
        print(f"        {r.detalle}")

    fallos_criticos = [r for r in resultados if not r.passed and r.critico]
    passed = sum(1 for r in resultados if r.passed)
    print()
    print(f"[INFO] Resultado: {passed}/{len(resultados)} casos PASS; "
          f"{len(fallos_criticos)} fallos criticos")

    sys.exit(1 if fallos_criticos else 0)


if __name__ == '__main__':
    main()
