"""Baja copias de los PDFs originales desde Drive CGR a data/input/.

Modo: readonly. Token scope drive.readonly. JAMAS modifica el Drive.
Operacion idempotente: re-correr no duplica, sobreescribe el archivo local.
"""
import io
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

TOKEN_FILE = r'C:\Users\aleja\token_cgr.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

ROOT_FIRMA_ID = '1U7aSbdtoPl3cYVWDzff5_LQwQ8Bjk_1T'
SUBFOLDER_SIN_FIRMA = 'Sin Firma (PRUEBA)'

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / 'data' / 'input'


def autenticar():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)


def ubicar_subcarpeta(service, parent_id: str, nombre: str) -> str:
    resp = service.files().list(
        q=f"'{parent_id}' in parents and trashed = false and name = '{nombre}'",
        fields="files(id,name,mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    items = resp.get('files', [])
    if not items:
        sys.exit(f"[ERROR] No se encontro subcarpeta '{nombre}' dentro de {parent_id}")
    return items[0]['id']


def listar_pdfs(service, folder_id: str):
    pdfs = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and mimeType = 'application/pdf'",
            fields="nextPageToken, files(id,name,size,md5Checksum)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=100,
            pageToken=page_token,
        ).execute()
        pdfs.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return pdfs


def sanitizar_nombre(nombre: str) -> str:
    # Reemplaza caracteres problemáticos en filesystem Windows (no quita acentos)
    bad = '<>:"/\\|?*'
    for ch in bad:
        nombre = nombre.replace(ch, '_')
    return nombre.strip()


def descargar(service, file_id: str, out_path: Path):
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    out_path.write_bytes(fh.getvalue())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    service = autenticar()
    sin_firma_id = ubicar_subcarpeta(service, ROOT_FIRMA_ID, SUBFOLDER_SIN_FIRMA)
    pdfs = listar_pdfs(service, sin_firma_id)
    print(f"[OK] {len(pdfs)} PDFs encontrados en '{SUBFOLDER_SIN_FIRMA}'")

    for i, pdf in enumerate(pdfs, 1):
        safe = sanitizar_nombre(pdf['name'])
        out = OUT_DIR / safe
        descargar(service, pdf['id'], out)
        size = out.stat().st_size
        print(f"  [{i:2d}/{len(pdfs)}] {safe} ({size:,} bytes)")

    print(f"\n[OK] Copias en {OUT_DIR}")


if __name__ == '__main__':
    main()
