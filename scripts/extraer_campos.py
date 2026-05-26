"""Extractor de los 8 campos canonicos visibles del certificado PDF.

Estrategia: usa anchor strings que sabemos estan presentes en el cert
(`Otorgan el presente`, `Por haber realizado el taller`, `Realizado del`,
`Horas totales:`, `Modalidad:`, `Jefatura`) y extrae los bloques entre
ellos. Esto es mas robusto que indexar por posicion fija, porque el
curso puede ocupar 1, 2 o mas bloques segun su largo.

Layout esperado (orden de aparicion):
  ...header CGR (descartado)...
  "Otorgan el presente certificado de participacion a"
  NOMBRE
  "Por haber realizado el taller"
  CURSO (1+ bloques, posiblemente con comillas curly)
  "Realizado del X al Y"                                       -> periodo
  "Horas totales: N / Modalidad: V / San Jose, fecha"          -> horas, modalidad, fecha
  "FIRMANTE / Jefatura ..."                                    -> firmante, jefatura

Si algun anchor no se encuentra o algun campo queda vacio, raise ValueError.
"""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class CamposCanonicos:
    nombre: str
    curso: str
    periodo: str
    horas: str
    modalidad: str
    fecha_emision: str
    firmante: str
    jefatura: str

    def to_dict(self) -> dict:
        return {
            'nombre': self.nombre,
            'curso': self.curso,
            'periodo': self.periodo,
            'horas': self.horas,
            'modalidad': self.modalidad,
            'fecha_emision': self.fecha_emision,
            'firmante': self.firmante,
            'jefatura': self.jefatura,
        }


_QUITAR_COMILLAS = '"“”‘’«» '


def _normalizar_comillas(t: str) -> str:
    return t.strip(_QUITAR_COMILLAS).strip()


def _limpiar(t: str) -> str:
    """Trim, colapsa multilines en 1 linea con espacios, normaliza Unicode."""
    lineas = [ln.strip() for ln in t.split('\n') if ln.strip()]
    return unicodedata.normalize('NFC', ' '.join(lineas)).strip()


def _split_kv(linea: str) -> str:
    """'Horas totales: 4' -> '4'. Si no hay ':' devuelve la linea."""
    if ':' in linea:
        return linea.split(':', 1)[1].strip()
    return linea.strip()


def _lineas_no_vacias(t: str) -> list[str]:
    return [ln.strip() for ln in t.split('\n') if ln.strip()]


def _find_idx(textos: list[str], substring: str, start: int = 0) -> int:
    """Devuelve indice del primer bloque que contiene substring. -1 si no."""
    for i in range(start, len(textos)):
        if substring in textos[i]:
            return i
    return -1


def extraer(pdf_path: Path) -> CamposCanonicos:
    """Extrae los 8 campos canonicos del PDF. Raise ValueError si layout incompatible."""
    doc = fitz.open(pdf_path)
    try:
        if len(doc) < 1:
            raise ValueError(f"PDF sin paginas: {pdf_path}")
        page = doc[0]
        blocks = page.get_text('blocks')
        # Solo bloques de texto (type 0) no vacios, ordenados por y0
        text_blocks = sorted(
            [b for b in blocks if b[6] == 0 and b[4] and b[4].strip()],
            key=lambda b: b[1],
        )
        textos = [b[4].strip() for b in text_blocks]

        # Anchors
        i_otorgan = _find_idx(textos, "Otorgan el presente")
        i_taller = _find_idx(textos, "Por haber realizado el taller", i_otorgan + 1 if i_otorgan >= 0 else 0)
        i_realizado = _find_idx(textos, "Realizado del", i_taller + 1 if i_taller >= 0 else 0)

        for n, i in [("Otorgan", i_otorgan), ("Por haber realizado el taller", i_taller),
                     ("Realizado del", i_realizado)]:
            if i < 0:
                raise ValueError(f"Anchor '{n}' no encontrado en {pdf_path.name}")

        # NOMBRE: bloques entre i_otorgan + 1 y i_taller - 1
        nombre_blocks = textos[i_otorgan + 1 : i_taller]
        if not nombre_blocks:
            raise ValueError(f"No hay bloques entre 'Otorgan' y 'Por haber realizado' en {pdf_path.name}")
        nombre = _limpiar(' '.join(nombre_blocks))

        # CURSO: bloques entre i_taller + 1 y i_realizado - 1 (1 o mas bloques)
        curso_blocks = textos[i_taller + 1 : i_realizado]
        if not curso_blocks:
            raise ValueError(f"No hay bloques entre 'Por haber realizado' y 'Realizado del' en {pdf_path.name}")
        curso = _normalizar_comillas(_limpiar(' '.join(curso_blocks)))

        # PERIODO: el bloque del anchor 'Realizado del'
        periodo = _limpiar(textos[i_realizado])

        # HORAS/MODALIDAD/FECHA: el bloque siguiente (idx i_realizado + 1)
        if i_realizado + 1 >= len(textos):
            raise ValueError(f"No hay bloque despues de 'Realizado del' en {pdf_path.name}")
        bloque_hmf = _lineas_no_vacias(textos[i_realizado + 1])

        horas = None
        modalidad = None
        fecha_emision_candidatos = []
        for ln in bloque_hmf:
            ln_low = ln.lower()
            if 'horas' in ln_low and ':' in ln:
                horas = _split_kv(ln)
            elif 'modalidad' in ln_low and ':' in ln:
                modalidad = _split_kv(ln)
            else:
                fecha_emision_candidatos.append(ln)

        if not horas:
            raise ValueError(f"No encontre 'Horas' en bloque: {bloque_hmf}")
        if not modalidad:
            raise ValueError(f"No encontre 'Modalidad' en bloque: {bloque_hmf}")
        if not fecha_emision_candidatos:
            raise ValueError(f"No encontre fecha de emision en bloque: {bloque_hmf}")
        # Si hay >1 linea candidata, tomamos la que parezca fecha (contiene año 20XX)
        fecha_emision = next(
            (ln for ln in fecha_emision_candidatos if re.search(r'20\d{2}', ln)),
            fecha_emision_candidatos[-1]
        )
        fecha_emision = unicodedata.normalize('NFC', fecha_emision.strip())
        horas = unicodedata.normalize('NFC', horas)
        modalidad = unicodedata.normalize('NFC', modalidad)

        # FIRMANTE / JEFATURA: ultimo bloque que contenga 'efatura' (case-insensitive)
        i_jefatura = -1
        for i in range(len(textos) - 1, -1, -1):
            if 'efatura' in textos[i].lower():
                i_jefatura = i
                break
        if i_jefatura < 0:
            raise ValueError(f"No encontre bloque con 'Jefatura' en {pdf_path.name}")
        bloque_firma = _lineas_no_vacias(textos[i_jefatura])
        if len(bloque_firma) < 2:
            raise ValueError(
                f"Bloque firma tiene {len(bloque_firma)} lineas en {pdf_path.name}, "
                f"esperaba >= 2. Contenido: {bloque_firma}"
            )
        firmante = unicodedata.normalize('NFC', bloque_firma[0])
        jefatura = unicodedata.normalize('NFC', bloque_firma[1])

        campos = CamposCanonicos(
            nombre=nombre,
            curso=curso,
            periodo=periodo,
            horas=horas,
            modalidad=modalidad,
            fecha_emision=fecha_emision,
            firmante=firmante,
            jefatura=jefatura,
        )

        for k, v in campos.to_dict().items():
            if not v:
                raise ValueError(f"Campo '{k}' vacio en {pdf_path.name}")

        return campos
    finally:
        doc.close()
