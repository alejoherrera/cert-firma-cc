"""Genera un PDF del acta tabular a partir del listado_hashes.json de un lote.

Uso:
    python scripts/generar_pdf_acta.py [lote_dir]

Default: el lote mas reciente bajo data/output/lote_*/

Output: <lote_dir>/acta.pdf

El PDF queda listo para abrir en el firmador BCCR y aplicarle firma PAdES.
La firma digital en si es responsabilidad humana (fuera de scope).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_BASE = REPO_ROOT / 'data' / 'output'

# Color azul CGR
AZUL_CGR = colors.HexColor('#222D72')
GRIS_TENUE = colors.HexColor('#EAEAEA')
GRIS_TEXTO = colors.HexColor('#4A4A4A')


def safe(s: str) -> str:
    return s.encode('ascii', errors='replace').decode('ascii')


def ultimo_lote() -> Path:
    lotes = sorted(OUTPUT_BASE.glob('lote_*'), reverse=True)
    if not lotes:
        sys.exit(f"[ERROR] No hay lotes en {OUTPUT_BASE}")
    return lotes[0]


def construir_acta(lote_dir: Path) -> Path:
    listado_path = lote_dir / 'listado_hashes.json'
    manifest_path = lote_dir / 'manifest.json'
    if not listado_path.exists() or not manifest_path.exists():
        sys.exit(f"[ERROR] Lote incompleto: faltan listado_hashes.json o manifest.json en {lote_dir}")

    registros = json.loads(listado_path.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

    out_pdf = lote_dir / 'acta.pdf'

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=landscape(LETTER),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title='Acta de emisión de certificados',
        author='Centro de Capacitación CGR',
        subject=f"Hash listado: {manifest['hash_listado_json_sha256']}",
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'TituloCGR', parent=styles['Heading1'],
        textColor=AZUL_CGR, fontSize=14, leading=18,
        alignment=1, spaceAfter=6,
    )
    estilo_subt = ParagraphStyle(
        'SubtCGR', parent=styles['Normal'],
        textColor=AZUL_CGR, fontSize=11, leading=14,
        alignment=1, spaceAfter=2,
    )
    estilo_titulo_acta = ParagraphStyle(
        'TituloActa', parent=styles['Heading2'],
        textColor=colors.black, fontSize=13, leading=16,
        alignment=1, spaceBefore=12, spaceAfter=12,
    )
    estilo_normal = ParagraphStyle(
        'NormalCGR', parent=styles['Normal'],
        fontSize=9.5, leading=12, alignment=0,
    )
    estilo_pie = ParagraphStyle(
        'PieCGR', parent=styles['Normal'],
        fontSize=10, leading=14, alignment=1,
        textColor=GRIS_TEXTO, spaceBefore=20,
    )

    story = []

    # Header CGR
    story.append(Paragraph('CONTRALORÍA GENERAL DE LA REPÚBLICA', estilo_titulo))
    story.append(Paragraph('División de Gestión de Apoyo &nbsp;·&nbsp; Unidad Centro de Capacitación', estilo_subt))
    story.append(Spacer(1, 4 * mm))

    # Titulo del acta
    story.append(Paragraph('ACTA DE EMISIÓN DE CERTIFICADOS', estilo_titulo_acta))

    # Tabla metadata
    curso = manifest.get('curso') or '(sin especificar)'
    fecha_emision_lote = registros[0]['fecha_emision'] if registros else '—'
    meta_data = [
        ['Curso / Actividad', curso],
        ['Fecha de emisión de los certificados', fecha_emision_lote],
        ['Total de certificados emitidos', str(manifest['total_certificados'])],
        ['Versión del hash canónico', f"v{manifest['hash_version']}"],
        ['Identificador del lote', manifest['lote_id']],
        ['Fecha de generación del acta', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['SHA-256 del listado de hashes', manifest['hash_listado_json_sha256']],
    ]
    tabla_meta = Table(meta_data, colWidths=[6.5 * cm, 16 * cm])
    tabla_meta.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (0, -1), AZUL_CGR),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (0, -1), GRIS_TENUE),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
        # SHA del listado en mono
        ('FONTNAME', (1, -1), (1, -1), 'Courier'),
        ('FONTSIZE', (1, -1), (1, -1), 8.5),
    ]))
    story.append(tabla_meta)
    story.append(Spacer(1, 6 * mm))

    # Prosa institucional
    prosa = (
        "Quien suscribe, en calidad de Jefatura A.I de la Unidad Centro de Capacitación de la "
        "División de Gestión de Apoyo de la Contraloría General de la República, hace constar la "
        "emisión de los certificados de participación cuyos hashes criptográficos SHA-256 se listan "
        "a continuación. Cada certificado emitido contiene impreso su propio hash, el cual debe "
        "coincidir con la entrada correspondiente en este acta. La firma digital aplicada sobre este "
        "documento da fe institucional del lote completo de certificados aquí registrados."
    )
    story.append(Paragraph(prosa, estilo_normal))
    story.append(Spacer(1, 5 * mm))

    # Tabla de certificados
    encabezado = ['Nº', 'Participante', 'Hash SHA-256 del certificado']
    rows = [encabezado]
    for r in registros:
        rows.append([str(r['nro']), r['nombre'], r['hash_sha256']])

    tabla = Table(rows, colWidths=[1.2 * cm, 7.5 * cm, 13.8 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_CGR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'LEFT'),
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (1, -1), 9.5),
        ('FONTNAME', (2, 1), (2, -1), 'Courier'),
        ('FONTSIZE', (2, 1), (2, -1), 7.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F8FB')]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
    ]))
    story.append(tabla)

    # Pie firmable
    pie_html = (
        f"<para align='center'>"
        f"<b>El presente documento será firmado digitalmente por:</b><br/>"
        f"<font color='#222D72'>Lic. Juan Alejandro Herrera López</font><br/>"
        f"Jefatura A.I, Unidad Centro de Capacitación<br/>"
        f"División de Gestión de Apoyo<br/>"
        f"Contraloría General de la República"
        f"</para>"
    )
    story.append(Paragraph(pie_html, estilo_pie))

    doc.build(story)
    return out_pdf


def main():
    if len(sys.argv) > 1:
        lote = Path(sys.argv[1])
    else:
        lote = ultimo_lote()
    if not lote.exists() or not lote.is_dir():
        sys.exit(f"[ERROR] No existe lote: {lote}")
    print(f"[INFO] Lote: {safe(lote.name)}")
    out = construir_acta(lote)
    print(f"[OK] Acta PDF -> {safe(str(out))} ({out.stat().st_size:,} bytes)")


if __name__ == '__main__':
    main()
