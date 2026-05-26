"""Orquestador del lote: extrae, hashea, estampa los N PDFs y produce
el listado de hashes + manifest.json + run.log.

Output: data/output/lote_<timestamp>/
  - <slug-nombre>.pdf x N
  - listado_hashes.csv
  - listado_hashes.json
  - manifest.json
  - run.log

El jefe del Centro arma el acta (PDF o XML) a partir de listado_hashes.* y
la firma con el firmador del BCCR (fuera del scope de este sistema).
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraer_campos import extraer
from calcular_hash import calcular, string_canonico, HASH_VERSION, CAMPOS_CANONICOS_V1
from estampar import estampar_acta_firmada

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO_ROOT / 'data' / 'input'
OUTPUT_BASE = REPO_ROOT / 'data' / 'output'


def slugify(nombre: str) -> str:
    """'Maria del Milagro Fonseca Hernandez' -> 'maria_del_milagro_fonseca_hernandez'."""
    # NFKD: separa los caracteres base de sus diacriticos
    sin_acentos = ''.join(
        c for c in unicodedata.normalize('NFKD', nombre)
        if not unicodedata.combining(c)
    )
    # solo ascii alphanum y espacios
    limpio = re.sub(r'[^A-Za-z0-9 ]+', '', sin_acentos).strip().lower()
    return re.sub(r'\s+', '_', limpio) or 'sin_nombre'


def git_commit_actual() -> str:
    """Devuelve el SHA corto del commit actual, o 'uncommitted' si no hay."""
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        # detectar cambios uncommitted
        dirty = subprocess.call(
            ['git', 'diff', '--quiet', '--exit-code'],
            cwd=REPO_ROOT,
        ) != 0
        return out + ('-dirty' if dirty else '')
    except Exception:
        return 'uncommitted'


def safe_print(s: str) -> None:
    """Print que no revienta en consolas cp1252 (Windows R5)."""
    print(s.encode('ascii', errors='replace').decode('ascii'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', type=Path, default=INPUT_DIR,
                    help='Carpeta con PDFs originales (default: data/input)')
    ap.add_argument('--curso', type=str, default=None,
                    help='Identificador del curso para el manifest (opcional)')
    args = ap.parse_args()

    pdfs = sorted(args.input_dir.glob('*.pdf'))
    if not pdfs:
        print(f"[ERROR] No hay PDFs en {args.input_dir}")
        sys.exit(2)

    ts_utc = datetime.now(timezone.utc)
    ts_local = ts_utc.astimezone()
    lote_dir = OUTPUT_BASE / f'lote_{ts_utc.strftime("%Y%m%d_%H%M%S")}'
    lote_dir.mkdir(parents=True, exist_ok=True)

    log_path = lote_dir / 'run.log'
    log_lines = []

    def log(msg: str) -> None:
        log_lines.append(msg)
        safe_print(msg)

    log(f"[INFO] Lote: {lote_dir.name}")
    log(f"[INFO] Input: {args.input_dir} ({len(pdfs)} PDFs)")
    log(f"[INFO] Hash version: v{HASH_VERSION}")
    log(f"[INFO] Campos canonicos: {CAMPOS_CANONICOS_V1}")
    log(f"[INFO] Timestamp UTC: {ts_utc.isoformat()}")
    log(f"[INFO] Git commit: {git_commit_actual()}")
    log("")

    registros = []
    errores = []
    slugs_usados = {}  # detectar colisiones de slug

    for pdf in pdfs:
        nombre_safe = pdf.name.encode('ascii', errors='replace').decode('ascii')
        try:
            campos = extraer(pdf)
            d = campos.to_dict()
            h = calcular(d)
            canonico = string_canonico(d)

            slug = slugify(d['nombre'])
            # si hay colision (homonimos), agregar sufijo n2, n3, ...
            n = slugs_usados.get(slug, 0) + 1
            slugs_usados[slug] = n
            if n > 1:
                slug = f'{slug}_n{n}'
                log(f"[WARN] Colision de slug, usando: {slug}")

            out_pdf = lote_dir / f'{slug}.pdf'
            estampar_acta_firmada(pdf, out_pdf, h, d, hash_version=HASH_VERSION)

            registros.append({
                'nro': len(registros) + 1,
                'archivo_original': pdf.name,
                'archivo_estampado': out_pdf.name,
                'nombre': d['nombre'],
                'curso': d['curso'],
                'periodo': d['periodo'],
                'horas': d['horas'],
                'modalidad': d['modalidad'],
                'fecha_emision': d['fecha_emision'],
                'firmante': d['firmante'],
                'jefatura': d['jefatura'],
                'string_canonico': canonico,
                'hash_sha256': h,
                'hash_version': HASH_VERSION,
            })
            log(f"  [OK] {nombre_safe:<40} -> {slug}.pdf  hash={h[:16]}...")
        except Exception as e:
            errores.append({'archivo': pdf.name, 'error': str(e)})
            log(f"  [FAIL] {nombre_safe:<40} -> {e}")

    log("")
    log(f"[OK] Procesados: {len(registros)}/{len(pdfs)}")
    if errores:
        log(f"[FAIL] Errores: {len(errores)}")

    # listado_hashes.csv
    csv_path = lote_dir / 'listado_hashes.csv'
    cols = ['nro', 'archivo_estampado', 'nombre', 'curso', 'periodo',
            'horas', 'modalidad', 'fecha_emision', 'firmante', 'jefatura',
            'hash_sha256', 'hash_version']
    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in registros:
            w.writerow(r)
    log(f"[OK] CSV:  {csv_path.name} ({csv_path.stat().st_size:,} bytes)")

    # listado_hashes.json
    json_path = lote_dir / 'listado_hashes.json'
    json_path.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    log(f"[OK] JSON: {json_path.name} ({json_path.stat().st_size:,} bytes)")

    # manifest.json (resumen para el acta)
    # hash del propio listado (para que el acta lo incluya)
    import hashlib
    listado_bytes = json_path.read_bytes()
    hash_listado = hashlib.sha256(listado_bytes).hexdigest()
    manifest = {
        'lote_id': lote_dir.name,
        'timestamp_utc': ts_utc.isoformat(),
        'timestamp_local': ts_local.isoformat(),
        'hash_version': HASH_VERSION,
        'campos_canonicos': CAMPOS_CANONICOS_V1,
        'curso': args.curso,
        'total_certificados': len(registros),
        'total_errores': len(errores),
        'errores': errores,
        'git_commit': git_commit_actual(),
        'hash_listado_json_sha256': hash_listado,
        'firmante_acta_pendiente': 'Lic. Juan Alejandro Herrera Lopez',
    }
    manifest_path = lote_dir / 'manifest.json'
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    log(f"[OK] Manifest: {manifest_path.name}")
    log(f"[OK] Hash del listado_hashes.json: {hash_listado}")

    log_path.write_text('\n'.join(log_lines) + '\n', encoding='utf-8')
    safe_print(f"\n[OK] Lote completo en: {lote_dir}")

    if errores:
        sys.exit(1)


if __name__ == '__main__':
    main()
