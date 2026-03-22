import os
import shutil
from datetime import datetime

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P

ODS_PATH = os.path.join(os.path.dirname(__file__), 'empresas.ods')

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


def _cell_value(cell):
    """Extrae el texto de una celda ODS. Devuelve cadena vacía si la celda no tiene contenido."""
    ps = cell.getElementsByType(P)
    return str(ps[0]) if ps else ''


def _row_to_list(row):
    """Expande celdas repetidas y devuelve una lista de valores ajustada a `NUM_COLS`."""
    values = []
    for cell in row.getElementsByType(TableCell):
        repeat = cell.getAttribute('numbercolumnsrepeated')
        n = int(repeat) if repeat else 1
        val = _cell_value(cell)
        values.extend([val] * n)
    if len(values) < NUM_COLS:
        values.extend([''] * (NUM_COLS - len(values)))
    return values[:NUM_COLS]


def _make_row(values):
    """Construye un TableRow de odfpy a partir de una lista de valores de texto."""
    row = TableRow()
    for val in values:
        cell = TableCell()
        if val:
            cell.addElement(P(text=str(val)))
        row.addElement(cell)
    return row


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
    backup = ODS_PATH.replace(
        '.ods',
        f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.ods'
    )
    shutil.copy2(ODS_PATH, backup)

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
    Claves: estado_empresa, localizacion, regimen, profesor.
    """
    return {
        'estado_empresa':  read_lookup(4),
        'localizacion':    read_lookup(1),
        'regimen':         read_lookup(3),
        'profesor':        read_lookup(2),
    }
