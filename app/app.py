"""App Streamlit local para el jefe del Centro de Capacitacion.

Arranque:
    python -m streamlit run app/app.py
o:
    iniciar.bat

Asume:
- Python instalado
- Dependencias del pyproject.toml instaladas
- Token CGR existente en C:\\Users\\aleja\\token_cgr.json (out-of-band)
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# Permitir importar desde /scripts
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from bajar_certificados import (  # noqa: E402
    autenticar, descargar, listar_pdfs, sanitizar_nombre, ubicar_subcarpeta,
)
from calcular_hash import (  # noqa: E402
    CAMPOS_CANONICOS_V1, HASH_VERSION, calcular, string_canonico,
)
from estampar import estampar_acta_firmada  # noqa: E402
from extraer_campos import extraer  # noqa: E402
from generar_acta import git_commit_actual, slugify  # noqa: E402
from generar_excel_acta import construir_xlsx  # noqa: E402
from generar_pdf_acta import construir_acta as construir_pdf_acta  # noqa: E402

ROOT_FIRMA_ID = '1U7aSbdtoPl3cYVWDzff5_LQwQ8Bjk_1T'
TOKEN_FILE = Path(r'C:\Users\aleja\token_cgr.json')
INPUT_BASE = REPO_ROOT / 'data' / 'input'
OUTPUT_BASE = REPO_ROOT / 'data' / 'output'


# ----------------------- helpers -----------------------

def _service_cached():
    """Cachea el cliente de Drive para no re-autenticar en cada interaccion."""
    if 'drive_service' not in st.session_state:
        st.session_state.drive_service = autenticar()
    return st.session_state.drive_service


def _listar_subcarpetas_drive(service, parent_id: str):
    """Lista subcarpetas (no PDFs) bajo la carpeta padre."""
    resp = service.files().list(
        q=(f"'{parent_id}' in parents and trashed = false and "
           "mimeType = 'application/vnd.google-apps.folder'"),
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        pageSize=100,
    ).execute()
    return resp.get('files', [])


def _resolver_carpeta_pdfs(service, curso_id: str) -> str:
    """Devuelve el id de la carpeta que contiene los PDFs a procesar.

    La estructura real es Firma -> <Curso>/ -> "Sin Firma"/ -> PDFs. Buscamos la
    subcarpeta cuyo nombre contenga 'sin firma' (case-insensitive) y devolvemos su
    id. Si no existe (estructura vieja con PDFs directos), devolvemos el propio curso.
    Nunca devolvemos subcarpetas tipo 'Con Firma'/'Firmados'.
    """
    for sub in _listar_subcarpetas_drive(service, curso_id):
        if 'sin firma' in sub['name'].lower():
            return sub['id']
    return curso_id


def _subcarpetas_con_count(service, parent_id: str):
    """Devuelve lista de cursos con count de PDFs de su subcarpeta 'Sin Firma'.

    Resultado: [{'name': ..., 'id': ..., 'pdf_folder_id': ..., 'count': N}, ...]
    'id' es la carpeta de curso (lo que ve el usuario); 'pdf_folder_id' es de donde
    se bajan los PDFs (la subcarpeta 'Sin Firma', o el propio curso como fallback).
    Ordenado por count descendente (las que tienen PDFs primero).
    """
    subs = _listar_subcarpetas_drive(service, parent_id)
    resultado = []
    for s in subs:
        try:
            pdf_folder_id = _resolver_carpeta_pdfs(service, s['id'])
            pdfs = listar_pdfs(service, pdf_folder_id)
            resultado.append({'name': s['name'], 'id': s['id'],
                              'pdf_folder_id': pdf_folder_id, 'count': len(pdfs)})
        except Exception:
            resultado.append({'name': s['name'], 'id': s['id'],
                              'pdf_folder_id': s['id'], 'count': -1})
    resultado.sort(key=lambda x: (-x['count'], x['name']))
    return resultado


def _cuenta_drive(service) -> str:
    """Devuelve el correo de la cuenta autenticada en Drive."""
    try:
        info = service.about().get(fields='user(emailAddress,displayName)').execute()
        u = info.get('user', {})
        return u.get('emailAddress', '(desconocido)')
    except Exception:
        return '(desconocido)'


def _bajar_lote_a_input(service, subcarpeta_id: str):
    """Baja todos los PDFs de la subcarpeta a data/input/, sobreescribiendo."""
    INPUT_BASE.mkdir(parents=True, exist_ok=True)
    # limpiar input anterior (siempre operamos en estado limpio)
    for old in INPUT_BASE.glob('*.pdf'):
        try:
            old.unlink()
        except OSError:
            pass
    pdfs = listar_pdfs(service, subcarpeta_id)
    progress = st.progress(0.0, text=f"Bajando 0/{len(pdfs)}…")
    bajados = []
    for i, pdf in enumerate(pdfs, 1):
        safe = sanitizar_nombre(pdf['name'])
        out = INPUT_BASE / safe
        descargar(service, pdf['id'], out)
        bajados.append(out)
        progress.progress(i / len(pdfs), text=f"Bajando {i}/{len(pdfs)}…")
    progress.empty()
    return bajados


def _procesar_lote(curso: str, status_cb=None):
    """Replica generar_acta.py + generar_pdf_acta.py + generar_excel_acta.py."""
    import csv
    import hashlib
    import json

    ts_utc = datetime.now(timezone.utc)
    ts_local = ts_utc.astimezone()
    lote_dir = OUTPUT_BASE / f'lote_{ts_utc.strftime("%Y%m%d_%H%M%S")}'
    lote_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(INPUT_BASE.glob('*.pdf'))
    registros = []
    errores = []
    slugs_usados: dict[str, int] = {}
    log_lines = [
        f"[INFO] Lote: {lote_dir.name}",
        f"[INFO] Hash version: v{HASH_VERSION}",
        f"[INFO] Timestamp UTC: {ts_utc.isoformat()}",
        f"[INFO] Git commit: {git_commit_actual()}",
        "",
    ]

    for i, pdf in enumerate(pdfs):
        if status_cb:
            status_cb(i, len(pdfs), pdf.name)
        try:
            campos = extraer(pdf)
            d = campos.to_dict()
            h = calcular(d)
            canonico = string_canonico(d)

            slug = slugify(d['nombre'])
            n = slugs_usados.get(slug, 0) + 1
            slugs_usados[slug] = n
            if n > 1:
                slug = f'{slug}_n{n}'

            out_pdf = lote_dir / f'{slug}.pdf'
            estampar_acta_firmada(pdf, out_pdf, h, d, hash_version=HASH_VERSION)
            registros.append({
                'nro': len(registros) + 1,
                'archivo_original': pdf.name,
                'archivo_estampado': out_pdf.name,
                'nombre': d['nombre'], 'curso': d['curso'],
                'periodo': d['periodo'], 'horas': d['horas'],
                'modalidad': d['modalidad'], 'fecha_emision': d['fecha_emision'],
                'firmante': d['firmante'], 'jefatura': d['jefatura'],
                'string_canonico': canonico,
                'hash_sha256': h, 'hash_version': HASH_VERSION,
            })
            log_lines.append(f"  [OK] {pdf.name} -> {out_pdf.name} hash={h[:16]}...")
        except Exception as e:
            errores.append({'archivo': pdf.name, 'error': str(e)})
            log_lines.append(f"  [FAIL] {pdf.name} -> {e}")

    if status_cb:
        status_cb(len(pdfs), len(pdfs), 'Finalizado')

    # CSV
    csv_path = lote_dir / 'listado_hashes.csv'
    cols = ['nro', 'archivo_estampado', 'nombre', 'curso', 'periodo', 'horas',
            'modalidad', 'fecha_emision', 'firmante', 'jefatura',
            'hash_sha256', 'hash_version']
    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in registros:
            w.writerow(r)

    # JSON
    json_path = lote_dir / 'listado_hashes.json'
    json_path.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2), encoding='utf-8')

    # Manifest
    hash_listado = hashlib.sha256(json_path.read_bytes()).hexdigest()
    manifest = {
        'lote_id': lote_dir.name,
        'timestamp_utc': ts_utc.isoformat(),
        'timestamp_local': ts_local.isoformat(),
        'hash_version': HASH_VERSION,
        'campos_canonicos': CAMPOS_CANONICOS_V1,
        'curso': curso,
        'total_certificados': len(registros),
        'total_errores': len(errores),
        'errores': errores,
        'git_commit': git_commit_actual(),
        'hash_listado_json_sha256': hash_listado,
        'firmante_acta_pendiente': registros[0]['firmante'] if registros else None,
    }
    (lote_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    # Acta PDF + xlsx
    construir_pdf_acta(lote_dir)
    construir_xlsx(lote_dir)

    # run.log
    (lote_dir / 'run.log').write_text('\n'.join(log_lines) + '\n', encoding='utf-8')

    return lote_dir, registros, errores


def _zip_lote(lote_dir: Path) -> bytes:
    """Empaqueta la carpeta del lote en memoria como bytes para descarga."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in lote_dir.iterdir():
            zf.write(p, arcname=p.name)
    return buf.getvalue()


def _abrir_en_explorer(path: Path):
    if sys.platform == 'win32':
        os.startfile(str(path))


# ----------------------- UI -----------------------

st.set_page_config(page_title="cert-firma-cc", layout="centered",
                   page_icon="📜", menu_items={'About': None})

# Header
col1, col2 = st.columns([5, 1])
with col1:
    st.title("cert-firma-cc")
    st.caption("Centro de Capacitación CGR — pipeline de hash + acta única")
with col2:
    st.markdown("**v0.4.0**")

st.divider()

# Sidebar: estado de conexion (auto-conecta al cargar)
with st.sidebar:
    st.subheader("Estado")
    if not TOKEN_FILE.exists():
        st.error(f"Token no encontrado en {TOKEN_FILE}")
        st.markdown(
            "Para generar el token, correr una vez:\n\n"
            "```\npython scripts/bajar_certificados.py\n```\n\n"
            "Eso abrira el flujo OAuth en el navegador."
        )
        st.stop()

    try:
        service = _service_cached()
        st.success("Conectado a Drive")
        cuenta = _cuenta_drive(service)
        st.caption(f"Cuenta: {cuenta}")
    except Exception as e:
        st.error(f"Error de autenticacion: {e}")
        if st.button("Reintentar"):
            st.session_state.pop('drive_service', None)
            st.rerun()
        st.stop()

    st.divider()
    st.caption(f"Repo: {REPO_ROOT}")
    st.caption(f"Hash version: v{HASH_VERSION}")

# Inicializar wizard step
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'subcarpeta_seleccionada' not in st.session_state:
    st.session_state.subcarpeta_seleccionada = None
if 'pdfs_bajados' not in st.session_state:
    st.session_state.pdfs_bajados = []
if 'lote_resultado' not in st.session_state:
    st.session_state.lote_resultado = None

# Step 1: elegir cohorte
st.header("Paso 1 — Elegir cohorte")

with st.spinner("Consultando carpetas del Drive…"):
    subcarpetas = _subcarpetas_con_count(service, ROOT_FIRMA_ID)

if not subcarpetas:
    st.warning("La carpeta raíz 'Firma' del Drive no tiene subcarpetas.")
    st.stop()

# Labels descriptivos con el count de PDFs por subcarpeta
def _label(s):
    if s['count'] < 0:
        return f"{s['name']} (sin acceso)"
    return f"{s['name']} — {s['count']} PDF{'' if s['count'] == 1 else 's'}"

opciones_label = [_label(s) for s in subcarpetas]
# Por default seleccionar la primera con PDFs > 0
default_idx = next((i for i, s in enumerate(subcarpetas) if s['count'] > 0), 0)

sel_label = st.selectbox(
    "Subcarpeta dentro de 'Firma' del Drive CGR:",
    options=opciones_label,
    index=default_idx,
    help="Las subcarpetas se ordenan por cantidad de PDFs (las con contenido primero).",
)
sel_idx = opciones_label.index(sel_label)
sel = subcarpetas[sel_idx]
sel_nombre = sel['name']
sel_id = sel['id']

if sel['count'] == 0:
    st.info(f"La subcarpeta '{sel_nombre}' está vacía. Elegí otra del listado.")

col_a, col_b = st.columns([1, 3])
with col_a:
    btn_disabled = sel['count'] == 0
    if st.button("Bajar PDFs",
                 use_container_width=True,
                 type="primary",
                 disabled=btn_disabled):
        with st.spinner(f"Bajando {sel['count']} PDFs del Drive…"):
            st.session_state.pdfs_bajados = _bajar_lote_a_input(service, sel['pdf_folder_id'])
            st.session_state.subcarpeta_seleccionada = sel_nombre
        st.success(f"Bajados {len(st.session_state.pdfs_bajados)} PDFs a data/input/")

if st.session_state.pdfs_bajados:
    st.caption(f"📁 {len(st.session_state.pdfs_bajados)} PDFs listos en `data/input/` (cohorte: {st.session_state.subcarpeta_seleccionada})")

st.divider()

# Step 2: preview
st.header("Paso 2 — Verificar extracción (muestra)")
pdfs_locales = sorted(INPUT_BASE.glob('*.pdf')) if INPUT_BASE.exists() else []
if not pdfs_locales:
    st.info("Bajá una cohorte primero (Paso 1).")
else:
    st.caption(f"{len(pdfs_locales)} certificados en disco local.")
    muestra = pdfs_locales[:3]
    for pdf in muestra:
        try:
            campos = extraer(pdf)
            d = campos.to_dict()
            with st.expander(f"✓ {d['nombre']}"):
                col_l, col_r = st.columns(2)
                with col_l:
                    st.write(f"**Curso:** {d['curso']}")
                    st.write(f"**Período:** {d['periodo']}")
                    st.write(f"**Horas:** {d['horas']}")
                    st.write(f"**Modalidad:** {d['modalidad']}")
                with col_r:
                    st.write(f"**Fecha emisión:** {d['fecha_emision']}")
                    st.write(f"**Firmante:** {d['firmante']}")
                    st.write(f"**Jefatura:** {d['jefatura']}")
                    h = calcular(d)
                    st.code(f"hash = {h[:32]}…", language=None)
        except Exception as e:
            st.error(f"✗ {pdf.name}: {e}")

st.divider()

# Step 3: procesar
st.header("Paso 3 — Procesar lote")
if not pdfs_locales:
    st.info("Bajá una cohorte primero.")
else:
    curso = st.text_input(
        "Nombre del curso (va al manifest del acta)",
        value=st.session_state.subcarpeta_seleccionada or "",
        help="Solo etiqueta administrativa. El hash NO depende de este campo.",
    )

    if st.button("🚀 Procesar lote", type="primary", use_container_width=True):
        if not curso.strip():
            st.error("Indicá el nombre del curso antes de procesar.")
        else:
            progress = st.progress(0.0, text="Iniciando…")

            def cb(i, total, archivo):
                progress.progress(
                    min(i / total, 1.0),
                    text=f"Procesando {i}/{total}: {archivo}",
                )

            with st.spinner("Procesando…"):
                lote_dir, registros, errores = _procesar_lote(curso, status_cb=cb)
                st.session_state.lote_resultado = lote_dir
            progress.empty()
            if errores:
                st.warning(f"Procesados con errores: {len(errores)}")
            else:
                st.success(f"✓ Lote completo: {len(registros)} certificados estampados.")

# Step 4: resultado
if st.session_state.lote_resultado:
    st.divider()
    st.header("Paso 4 — Resultado")
    lote = st.session_state.lote_resultado
    st.write(f"📁 **Lote**: `{lote.name}`")
    st.write(f"📂 **Ruta**: `{lote}`")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("📂 Abrir carpeta", use_container_width=True):
            _abrir_en_explorer(lote)
    with col_b:
        if (lote / 'acta.pdf').exists():
            if st.button("📄 Abrir acta.pdf", use_container_width=True):
                _abrir_en_explorer(lote / 'acta.pdf')
    with col_c:
        if (lote / 'acta.xlsx').exists():
            if st.button("📊 Abrir acta.xlsx", use_container_width=True):
                _abrir_en_explorer(lote / 'acta.xlsx')
    with col_d:
        zip_bytes = _zip_lote(lote)
        st.download_button(
            "💾 Descargar .zip",
            data=zip_bytes,
            file_name=f"{lote.name}.zip",
            mime='application/zip',
            use_container_width=True,
        )

    # Resumen
    import json
    manifest = json.loads((lote / 'manifest.json').read_text(encoding='utf-8'))
    st.caption(
        f"Total: {manifest['total_certificados']} certs · "
        f"Hash version: v{manifest['hash_version']} · "
        f"Commit: {manifest['git_commit']}"
    )
    st.code(f"SHA-256 del listado_hashes.json:\n{manifest['hash_listado_json_sha256']}", language=None)
    st.info("Próximo paso fuera de la app: firmar `acta.pdf` con la tarjeta BCCR.")
