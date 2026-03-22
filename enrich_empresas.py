"""Enriquece el ODS con el campo Descripcion a partir de scraping web."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ODS_PATH = Path(__file__).with_name("empresas.ods")
SCRAPER_PATH = Path(__file__).with_name("scrape_empresas.js")
EMPRESAS_HEADERS = [
    "ID EMPRESA",
    "NOMBRE EMPRESA",
    "ESTADO EMPRESA",
    "OBSERVACIONES",
    "WEB",
    "LOCALIDAD",
    "CORREO EMPRESA",
    "TFNO EMPRESA",
    "EXTENSIÓN TFNO",
    "CONTACTO",
    "CORREO CONTACTO",
    "TFNO CONTACTO",
    "TECNOLOGÍAS",
    "RÉGIMEN",
    "PROFESOR",
    "DESCRIPCIÓN",
]
DATA_COLUMNS = [
    "id_empresa",
    "nombre",
    "estado",
    "observaciones",
    "web",
    "localidad",
    "correo_empresa",
    "tfno_empresa",
    "extension_tfno",
    "contacto",
    "correo_contacto",
    "tfno_contacto",
    "tecnologias",
    "regimen",
    "profesor",
    "descripcion",
]

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


@dataclass
class EmpresaRecord:
    """Representa una fila de empresa con referencia a su nodo XML original."""

    row: ET.Element
    values: list[str]


def clean_text(value: str) -> str:
    """Sanea texto eliminando espacios sobrantes en los extremos."""
    return value.strip() if isinstance(value, str) else ""


def cell_text(cell: ET.Element) -> str:
    """Extrae el texto visible de una celda ODS."""
    parts = []
    for paragraph in cell.findall("text:p", NS):
        parts.append("".join(paragraph.itertext()))
    return "\n".join(part for part in parts if part)


def expand_row(row: ET.Element, target_columns: int) -> list[str]:
    """Expande una fila ODS respetando celdas repetidas hasta `target_columns`."""
    values: list[str] = []
    repeat_key = f"{{{NS['table']}}}number-columns-repeated"
    for cell in row.findall("table:table-cell", NS):
        repeat = int(cell.attrib.get(repeat_key, "1"))
        values.extend([cell_text(cell)] * repeat)
        if len(values) >= target_columns:
            break
    if len(values) < target_columns:
        values.extend([""] * (target_columns - len(values)))
    return values[:target_columns]


def build_cell(value: str) -> ET.Element:
    """Construye una celda de texto simple para el ODS."""
    cell = ET.Element(f"{{{NS['table']}}}table-cell")
    if value:
        cell.set(f"{{{NS['office']}}}value-type", "string")
        paragraph = ET.SubElement(cell, f"{{{NS['text']}}}p")
        paragraph.text = value
    return cell


def replace_row_contents(row: ET.Element, values: list[str]) -> None:
    """Sustituye todas las celdas de una fila por una lista plana de valores."""
    for cell in list(row.findall("table:table-cell", NS)):
        row.remove(cell)
    for value in values:
        row.append(build_cell(value))


def load_empresas_sheet() -> tuple[ET.ElementTree, ET.Element, list[EmpresaRecord]]:
    """Carga la hoja Empresas desde `content.xml` y devuelve sus filas de datos."""
    with ZipFile(ODS_PATH) as ods_zip:
        content_root = ET.fromstring(ods_zip.read("content.xml"))

    sheet = content_root.find(".//table:table[@table:name='Empresas']", NS)
    if sheet is None:
        raise RuntimeError("No se ha encontrado la hoja 'Empresas' en el ODS.")

    rows = sheet.findall("table:table-row", NS)
    if not rows:
        raise RuntimeError("La hoja 'Empresas' no contiene filas.")

    records = []
    for row in rows[1:]:
        values = expand_row(row, len(DATA_COLUMNS))
        if any(values[1:15]):
            records.append(EmpresaRecord(row=row, values=values))

    return ET.ElementTree(content_root), rows[0], records


def write_updated_ods(tree: ET.ElementTree) -> None:
    """Escribe `content.xml` actualizado preservando el resto de entradas del ZIP."""
    backup_path = ODS_PATH.with_name(
        f"{ODS_PATH.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ODS_PATH.suffix}"
    )
    shutil.copy2(ODS_PATH, backup_path)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with ZipFile(ODS_PATH) as source_zip, ZipFile(temp_path, "w", ZIP_DEFLATED) as target_zip:
            for info in source_zip.infolist():
                if info.filename == "content.xml":
                    xml_payload = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
                    target_zip.writestr(info, xml_payload)
                else:
                    target_zip.writestr(info, source_zip.read(info.filename))
        shutil.move(temp_path, ODS_PATH)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def chunked(items: list[EmpresaRecord], size: int) -> Iterable[list[EmpresaRecord]]:
    """Divide una lista en bloques consecutivos del tamaño indicado."""
    for index in range(0, len(items), size):
        yield items[index:index + size]


def run_scraper(batch: list[EmpresaRecord]) -> list[dict[str, str]]:
    """Ejecuta el scraper Playwright para un bloque de empresas."""
    payload = [
        {
            "nombre": record.values[1],
            "web": record.values[4],
        }
        for record in batch
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as input_file:
        json.dump(payload, input_file, ensure_ascii=False, indent=2)
        input_path = Path(input_file.name)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as output_file:
        output_path = Path(output_file.name)

    try:
        command = ["node", str(SCRAPER_PATH), str(input_path), str(output_path)]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        return json.loads(output_path.read_text(encoding="utf-8"))
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def update_records(records: list[EmpresaRecord], scraped_rows: list[dict[str, str]]) -> None:
    """Aplica los resultados del scraping a las filas ya cargadas en memoria."""
    for record, scraped in zip(records, scraped_rows):
        record.values[15] = clean_text(scraped.get("descripcion") or "N/D")
        replace_row_contents(record.row, record.values)


def ensure_headers(header_row: ET.Element) -> None:
    """Asegura que la cabecera de la hoja Empresas incluya las nuevas columnas."""
    replace_row_contents(header_row, EMPRESAS_HEADERS)


def main() -> None:
    """Procesa todo el ODS en lotes, actualizando Descripción."""
    batch_size = 25
    tree, header_row, records = load_empresas_sheet()
    ensure_headers(header_row)

    print(f"Empresas a procesar: {len(records)}")
    for batch_index, batch in enumerate(chunked(records, batch_size), start=1):
        print(f"Lote {batch_index}: {len(batch)} empresas")
        scraped_rows = run_scraper(batch)
        update_records(batch, scraped_rows)
        write_updated_ods(tree)


if __name__ == "__main__":
    main()
