import os
import shutil
from datetime import datetime

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P

ODS_PATH = os.path.join(os.path.dirname(__file__), 'empresas.ods')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')

NUM_COLS = 16
COLUMNS = [
    'id_empresa',
    'nombre',
    'estado',
    'observaciones',
    'web',
    'localidad',
    'correo_empresa',
    'tfno_empresa',
    'extension_tfno',
    'contacto',
    'correo_contacto',
    'tfno_contacto',
    'tecnologias',
    'regimen',
    'profesor',
    'descripcion',
]

INTERACCIONES_COLS = ['id_empresa', 'tipo', 'descripcion', 'fecha', 'profesor']
NUM_ESTUDIANTES_COLS = ['id_empresa', 'num_alumnos', 'grupo', 'anio']


def _cell_value(cell):
    """Extrae el texto de una celda ODS. Devuelve cadena vacía si la celda no tiene contenido."""
    ps = cell.getElementsByType(P)
    return str(ps[0]) if ps else ''


def _row_to_list(row, n_cols=NUM_COLS):
    """Expande celdas repetidas y devuelve una lista de valores ajustada a `n_cols`."""
    values = []
    for cell in row.getElementsByType(TableCell):
        repeat = cell.getAttribute('numbercolumnsrepeated')
        n = int(repeat) if repeat else 1
        val = _cell_value(cell)
        values.extend([val] * n)
    if len(values) < n_cols:
        values.extend([''] * (n_cols - len(values)))
    return values[:n_cols]


def _make_row(values):
    """Construye un TableRow de odfpy a partir de una lista de valores de texto."""
    row = TableRow()
    for val in values:
        cell = TableCell()
        if val:
            cell.addElement(P(text=str(val)))
        row.addElement(cell)
    return row


def _create_ods_backup():
    """Crea una copia de seguridad del ODS en la carpeta `backups` y devuelve su ruta."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_name = f'empresas_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.ods'
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(ODS_PATH, backup_path)
    return backup_path


def _replace_sheet_header(sheet, headers):
    """Reemplaza la fila de cabecera de una hoja por los encabezados indicados."""
    rows = sheet.getElementsByType(TableRow)
    if rows:
        sheet.removeChild(rows[0])
    sheet.insertBefore(_make_row(headers), sheet.firstChild)


def read_empresas():
    """Devuelve una lista de empresas como diccionarios y omite filas vacías."""
    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[0]
    rows = sheet.getElementsByType(TableRow)
    result = []
    for row in rows[1:]:  # skip header
        vals = _row_to_list(row)
        if any(vals):
            result.append(dict(zip(COLUMNS, vals)))
    return result


def write_empresas(empresas):
    """Sobrescribe la hoja Empresas con la lista recibida y crea un backup antes de guardar."""
    _create_ods_backup()

    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[0]
    rows = sheet.getElementsByType(TableRow)

    # Remove all data rows, keep header (index 0)
    for row in list(rows[1:]):
        sheet.removeChild(row)

    # Add updated rows
    for empresa in empresas:
        vals = [empresa.get(col, '') or '' for col in COLUMNS]
        sheet.addElement(_make_row(vals))

    doc.save(ODS_PATH)


def read_lookup(sheet_index):
    """Devuelve los valores de la primera columna de una hoja auxiliar."""
    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[sheet_index]
    values = []
    for row in sheet.getElementsByType(TableRow):
        cells = row.getElementsByType(TableCell)
        if cells:
            val = _cell_value(cells[0])
            if val:
                values.append(val)
    return values


def read_all_lookups():
    """Devuelve un dict con todas las tablas de referencia del ODS.
    Claves: estado_empresa, localizacion, regimen, profesor, tipo_interaccion, grupo_estudiantes.
    Devuelve lista vacía para cualquier hoja que no exista en el fichero.
    """
    def _safe(idx):
        try:
            return read_lookup(idx)
        except IndexError:
            return []

    return {
        'estado_empresa':    _safe(4),
        'localizacion':      _safe(1),
        'regimen':           _safe(3),
        'profesor':          _safe(2),
        'tipo_interaccion':  _safe(6),
        'grupo_estudiantes': _safe(8),
    }


def read_interacciones():
    """Devuelve todos los registros de la hoja Interacciones como lista de dicts. Omite filas vacías."""
    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[5]
    rows = sheet.getElementsByType(TableRow)
    result = []
    for row in rows[1:]:  # skip header
        vals = _row_to_list(row, len(INTERACCIONES_COLS))
        if any(vals):
            result.append(dict(zip(INTERACCIONES_COLS, vals)))
    return result


def write_interacciones(interacciones):
    """Sobrescribe la hoja Interacciones con la lista recibida. Crea backup antes de guardar."""
    _create_ods_backup()

    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[5]
    rows = sheet.getElementsByType(TableRow)

    for row in list(rows[1:]):
        sheet.removeChild(row)

    for interaccion in interacciones:
        vals = [interaccion.get(col, '') or '' for col in INTERACCIONES_COLS]
        sheet.addElement(_make_row(vals))

    doc.save(ODS_PATH)


def read_num_estudiantes():
    """Devuelve todos los registros de la hoja Num_estudiantes como lista de dicts. Omite filas vacías."""
    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[7]
    rows = sheet.getElementsByType(TableRow)
    result = []
    for row in rows[1:]:  # skip header
        vals = _row_to_list(row, len(NUM_ESTUDIANTES_COLS))
        if any(vals):
            result.append(dict(zip(NUM_ESTUDIANTES_COLS, vals)))
    return result


def write_num_estudiantes(registros):
    """Sobrescribe la hoja Num_estudiantes con la lista recibida. Crea backup antes de guardar."""
    _create_ods_backup()

    doc = load(ODS_PATH)
    sheet = doc.spreadsheet.getElementsByType(Table)[7]
    rows = sheet.getElementsByType(TableRow)

    _replace_sheet_header(sheet, ['ID_EMPRESA', 'NUM_ALUMNOS', 'GRUPO', 'AÑO'])
    rows = sheet.getElementsByType(TableRow)

    for row in list(rows[1:]):
        sheet.removeChild(row)

    for registro in registros:
        vals = [registro.get(col, '') or '' for col in NUM_ESTUDIANTES_COLS]
        sheet.addElement(_make_row(vals))

    doc.save(ODS_PATH)
