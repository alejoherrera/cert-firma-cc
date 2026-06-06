# Análisis: ¿Correr el pipeline desde un Google Sheet en vez de la app local?

**Fecha:** 2026-06-04
**Contexto:** El responsable pregunta si en vez de la app Streamlit se puede hacer un
script que corra desde una página de Google Sheets, que genere los hashes y el acta.

## Qué hace hoy el motor (lo que habría que portar)

| Paso | Tecnología actual | ¿Portable a Apps Script (GAS)? |
|---|---|---|
| 1. Leer PDFs de Drive (readonly) | google-api-python-client | Sí (DriveApp) |
| 2. Extraer 8 campos del PDF | **PyMuPDF** `get_text('blocks')` por anchors y posición | **No.** GAS no tiene PyMuPDF. Para sacar texto habría que convertir PDF→Google Doc (OCR), lo que **destruye la estructura de bloques** que usa el extractor. Riesgo alto de romperse. |
| 3. SHA-256 del string canónico | hashlib + NFC/lower/trim | Sí (`Utilities.computeDigest` + `normalize('NFC')`), pero es una **segunda implementación** del hash → riesgo de divergencia byte-a-byte; habría que cross-validar contra Python. |
| 4. **Estampar hash+QR en cada PDF** | **PyMuPDF overlay** | **No (bloqueante).** GAS no tiene librería nativa de manipulación de PDF ni QR. Sin esto no hay certificado estampado = se pierde el entregable central. |
| 5. acta.pdf | reportlab | Parcial (Google Doc template → export PDF, render distinto). |
| 6. acta.xlsx / listado | openpyxl / csv | Sí (es lo más natural en Sheets). |

## Bloqueante técnico

Los dos pasos que **dependen de PyMuPDF** — extracción robusta (paso 2) y **estampado
hash+QR (paso 4)** — **no se pueden hacer en Apps Script**. El estampado es el corazón del
sistema (cada cert lleva impreso su hash legible, CONSTITUTION §7). Por lo tanto **"todo
desde un Google Sheet" no es viable** sin perder el estampado.

## Bloqueante constitucional/privacidad

Apps Script corre en servidores de Google → el PII (nombres) se procesaría en la nube.
CONSTITUTION §2 + §4.2: en fase piloto el PII **no abandona el equipo del responsable**, y
§4.1 exige enmienda para escribir a Drive. Mover el procesamiento a GAS sería un cambio de
postura constitucional → requeriría ADR + posible enmienda. (Atenuante: es el Workspace
institucional cgr.go.cr, no una cuenta personal; pero sigue siendo un cambio explícito.)

## Opciones viables

- **A — Híbrido (Sheet = panel, Python local = motor).** El Sheet lista cursos/cohortes y una
  columna "procesar"; un script Python local lee el Sheet vía Sheets API, corre el motor
  **intacto** en la máquina (extracción/estampado/acta), y escribe de vuelta los hashes al
  Sheet + sube acta a Drive. Da la UX de hoja de cálculo **sin perder estampado ni privacidad**.
- **B — App local + publicar salida a un Sheet.** Se mantiene el trigger local (la app/`.bat`)
  y se agrega un paso que sube `listado_hashes` a un Google Sheet para revisión/compartir.
  Mínimo cambio. (Ya generamos `acta.xlsx`.)
- **C — Todo en GAS.** Rechazada: imposible estampar y extracción frágil.

## Recomendación preliminar

Si el objetivo es UX de hoja de cálculo / compartir: **Opción B** (barata) o **A** (si quiere
disparar desde el Sheet). El motor PyMuPDF debe seguir corriendo local en cualquier caso.
Falta confirmar **qué motiva el cambio** (ver preguntas abiertas) antes de elegir.

## Preguntas abiertas
- ¿Qué duele de la app actual? (instalar Python / que otros lo disparen / querer el acta como
  hoja editable y compartible / no querés Streamlit).
- ¿Quién más necesita dispararlo o verlo, y desde dónde?

## Motivaciones confirmadas (2026-06-04)

El responsable eligió: (1) **no querer instalar/correr Python**, (2) **acta/listado como hoja
compartible**, (3) **no querer la UI Streamlit**. NO eligió "que otros lo disparen" → sigue
siendo monousuario (él).

## Reconciliación (la tensión)

- El estampado + extracción **obligan a correr PyMuPDF (Python) localmente**. No hay forma de
  evitar que "algo Python" corra en su equipo sin hostear en la nube (lo que viola §2/§4.2 +
  presupuesto $0). Por lo tanto **"sin Python en ningún lado" es imposible**; lo alcanzable es
  **que él no perciba/instale Python**.
- Solución a (1)+(3): **empaquetar el motor como .exe único de Windows** (PyInstaller). Doble
  clic, sin instalar Python, sin Streamlit. El motor corre local (PII safe). UI mínima nativa o
  sin UI (procesa el curso configurado).
- Solución a (2): publicar `listado_hashes`/acta a un **Google Sheet compartible**. PERO esto
  significa que la herramienta **escribe a Drive** → cruza CONSTITUTION §4.1 ("escribir a Drive
  requiere enmienda constitucional") y exige **ampliar el scope OAuth** (hoy solo
  `drive.readonly`; haría falta `spreadsheets` + `drive.file`). Es un **gate de gobernanza**:
  decisión del único firmante. Alternativa sin enmienda: el tool genera `acta.xlsx` local y el
  responsable lo sube/comparte manualmente.

## Recomendación refinada

1. **.exe standalone** (PyInstaller) reemplaza app Streamlit → cubre (1) y (3). Riesgo: tamaño
   ~80MB y posibles falsos positivos de antivirus; build pipeline nuevo.
2. Para (2): decidir gobernanza. Si autoriza enmienda → agregar publisher a Google Sheet con
   scope ampliado + ADR. Si no → mantener `acta.xlsx` local y compartir manual.

Pendiente go-ahead del responsable en ambos puntos antes de construir.

## CORRECCIÓN 2026-06-04 (R43 — sobreafirmé sin verificar)

El responsable señaló que con Apps Script no hace falta `.exe`. Tiene razón, y al verificar
encontré que **sobreafirmé el bloqueante de estampado**:

- **Estampar en Apps Script SÍ es viable.** La librería `PDFApp` de Tanaike (wrapper GAS+pdf-lib
  sobre runtime V8) embebe texto e imágenes en un PDF con coordenadas x,y y fuentes custom. El
  QR se embebe como imagen (generada por lib/API). → Mi "bloqueante duro" era **falso**.
  Fuentes: github.com/tanaikech/PDFApp ; medium "Cooking PDF over Google Apps Script".
- **PII en la nube:** objeción **débil** — los PDFs originales YA viven en el Drive de
  `cgr.go.cr`. Procesarlos con GAS dentro del mismo Workspace no los saca de donde ya están.
  §4.1 (escribir a Drive) seguiría requiriendo enmienda, pero es un trámite del firmante, no un
  muro. El framing previo (readonly local + exe) era una de varias arquitecturas, no la única.
- **El verdadero riesgo restante en GAS = extracción de los 8 campos.** Parsear texto con
  estructura/posición (como hace PyMuPDF `get_text('blocks')`) en GAS es inmaduro: la vía común
  es OCR→Google Doc, que **pierde el layout** del que dependen nuestros anchors. Hay libs
  (`PDF.gs`) pero la calidad posicional no está validada.

### El crux que decide la arquitectura (no resuelto)

**¿Existe data fuente de los certificados (una hoja/registro con nombre, curso, período, etc.)
o solo tenemos los PDF terminados?**
- Si **existe data fuente** → GAS no necesita parsear PDFs: calcula el hash desde los campos
  fuente, estampa con PDFApp, arma el acta como Sheet. **Cubre las 3 motivaciones, sin Python,
  sin exe.** Arquitectura limpia.
- Si **solo hay PDFs** → GAS debe extraer texto del PDF (riesgoso). Ahí el motor PyMuPDF local
  sigue siendo más confiable, y GAS solo serviría como front/publicador.

Pendiente: confirmar origen de los certificados antes de elegir.

## Hallazgo 2026-06-05: la matrícula NO contiene los campos del hash

Ejemplo real `Matrícula (56).csv` (cohorte Fideicomisos):
columnas = `Nombre; Primer Apellido; Segundo Apellido; Cédula; Institución; Siglas; Resultado;
Email; Expediente`.

Mapeo contra los 8 campos canónicos:
- `nombre` → reconstruible: `Nombre + Primer Apellido + Segundo Apellido` = "Jenaro Soto Rojas"
  (coincide con lo que imprime el PDF, validado por el extractor PyMuPDF). OK.
- `curso, periodo, horas, modalidad, fecha_emision, firmante, jefatura` → **NO están en la
  matrícula.** Son constantes a nivel de cohorte que viven en el generador/plantilla del
  certificado, no en la matrícula.
- `Cédula, Institución, Email` → PII extra que **NO entra al hash** (ADR-0001). Irrelevante al
  canónico, pero es PII → la matrícula no se commitea.

### Implicación

La "hoja fuente" cubre solo la identidad. Para que GAS calcule el hash necesita además los **7
campos de cohorte**. Diseño viable: por lote, el operador aporta (a) matrícula = nombres, (b) 7
constantes de cohorte (curso, frase de período, horas, modalidad, fecha emisión, firmante,
jefatura) tal como se imprimen. GAS combina nombre × constantes → canónico → hash → estampa →
acta. Sigue sin requerir Python, **si** las 7 constantes reproducen el texto del PDF exacto
(validar contra el oráculo PyMuPDF en una muestra).

### Pendiente (crux 2)

¿De dónde salen los 7 campos de cohorte? (config del generador de certificados / se tipean por
lote / otra hoja). Sin esa fuente, GAS no puede calcular el hash.

## Dato decisivo 2026-06-05: el generador de certificados es EXTERNO/manual

Respuestas del responsable: los 7 campos de cohorte viven en "el generador de certificados",
pero ese generador es "otro sistema / manual" — **NO Apps Script, NO controlado por nosotros.**

### Por qué esto reordena la recomendación (verificabilidad)

CONSTITUTION §7 + ADR-0001: el hash estampado debe ser igual a `hash(texto visible en el papel)`,
porque un tercero recalcula leyendo solo el papel. Hay dos formas de obtener los inputs del hash:

1. **Extraer del PDF terminado (PyMuPDF).** El hash sale del mismísimo texto impreso →
   coincidencia con el papel **garantizada por construcción**. Es lo que hace el sistema hoy.
2. **Reconstruir desde datos fuente** (matrícula + 7 constantes tipeadas). El hash coincide con
   el papel **solo si** la reconstrucción reproduce el texto impreso carácter-por-carácter. Si
   difiere (un espacio, un punto, "Gestión" vs "Gestion"), se estampa un hash que **NO coincide
   con el papel** y **todos** los certificados fallan la verificación de terceros — en silencio.

El generador es externo/manual ⇒ no podemos leer programáticamente sus 7 constantes ni inyectar
el hash en el momento de impresión. Tendríamos que **tipearlas a mano por lote** en GAS. Y el
validador natural de la opción (2) — extraer el texto del PDF para comparar — es justo lo que GAS
hace mal. **GAS-puro no puede auto-validar la garantía legal**; necesitaría PyMuPDF como oráculo
al menos una vez por lote, lo que rompe el "sin Python".

### Recomendación (revisada, decisiva)

El artefacto autoritativo es el **PDF terminado** producido por un sistema que no controlamos.
Para un sistema de grado legal, los inputs del hash deben salir del papel → **mantener el motor
PyMuPDF como núcleo de verificabilidad** (opción 1). GAS-puro reconstruyendo desde constantes
manuales apuesta la garantía legal a una transcripción manual, sin forma robusta de validarla.

Cómo atender las 3 motivaciones SIN sacrificar correctitud:
- **No Streamlit / no instalar Python** → empaquetar el motor PyMuPDF como **.exe de un clic**
  (corre el motor probado; el usuario no ve ni instala Python).
- **Hoja compartible** → publisher Python → Google Sheet (requiere enmienda §4.1 + scope).

GAS-puro solo sería defendible si el hash se integra DENTRO del generador (computado con las
cadenas exactas al imprimir) — inviable hoy porque el generador es externo/manual.
