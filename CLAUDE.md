# Empresas CRUD

Aplicación local para gestionar el fichero `empresas.ods`. Uso personal (usuario único).

## Stack

- **Python**: `C:/Users/Noemi/AppData/Local/Programs/Python/Python314/python.exe`
- **UI**: Streamlit
- **ODS**: odfpy
- **Fichero de datos**: `empresas.ods` (en la raíz del proyecto)

## Ejecutar la aplicación

```bash
C:/Users/Noemi/AppData/Local/Programs/Python/Python314/python.exe -m streamlit run app.py
```

## Estructura del fichero ODS

### Hoja principal: `Empresas` (~300 registros)

| Columna (índice) | Nombre en ODS | Tipo | FK |
|---|---|---|---|
| 0 | ID EMPRESA | numérico | — |
| 1 | NOMBRE EMPRESA | texto | — |
| 2 | ESTADO EMPRESA | texto | → Estado_empresa |
| 3 | OBSERVACIONES | texto largo | — |
| 4 | WEB | url | — |
| 5 | LOCALIDAD | texto | → Localizacion |
| 6 | CORREO EMPRESA | email | — |
| 7 | TFNO EMPRESA | texto | — |
| 8 | EXTENSIÓN TFNO | texto | — |
| 9 | CONTACTO | texto | — |
| 10 | CORREO CONTACTO | email | — |
| 11 | TFNO CONTACTO | texto | — |
| 12 | TECNOLOGÍAS | texto largo | — |
| 13 | RÉGIMEN | texto | → Regimen |
| 14 | PROFESOR | texto | → Profesor |
| 15 | DESCRIPCION | texto largo | — |

> La fila 0 es la cabecera. Los datos empiezan en la fila 1.

### Tablas de referencia (solo lectura)

**Localizacion** (col 0): Adeje, Arafo, Arico, Arona, Buenavista del Norte, Candelaria, El Rosario, El Sauzal, El Tanque, Fasnia, Garachico, Granadilla de Abona, Guía de Isora, Güímar, Icod de los Vinos, La Guancha, La Matanza de Acentejo, La Orotava, La Victoria de Acentejo, Los Realejos, Los Silos, Puerto de la Cruz, San Cristóbal de La Laguna, San Juan de la Rambla, San Miguel de Abona, Santa Cruz de Tenerife, Santa Úrsula, Santiago del Teide, Tacoronte, Tegueste, Vilaflor de Chasna, Gran Canaria, El Hierro, La Gomera, La Palma, Lanzarote, Fuerteventura, Península, Erasmus, Deslocalizado, Extranjero, Tenerife

**Profesor** (col 0): Alejandro, Ángel, Antonio, Carlos, David Airam, David Betancor, Eleazar, Joatham, Juan Jesús, Juan Orribo, Malu, Noemí, Rubén, Sara, Sergio

**Regimen** (col 0): Presencial, En remoto, Híbrido

**Estado_empresa** (col 0): Descartada, Empresa nueva, Sin respuesta, No interesada, Empresa potencial (solicita información), Empresa potencial (interés futuro), Colaboró anteriormente, Colabora, Pendiente de respuesta


## Lectura del ODS

odfpy devuelve caracteres especiales (ñ, á, etc.) con problemas de encoding en algunas versiones. Verificar siempre con datos reales al desarrollar.

Patrón básico de lectura:

```python
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P

def get_cell_value(cell):
    ps = cell.getElementsByType(P)
    return str(ps[0]) if ps else ''

doc = load('empresas.ods')
sheets = doc.spreadsheet.getElementsByType(Table)
sheet_empresas = sheets[0]  # índice 0 = Empresas
```

## Convenciones

- Añadir un docstring explicativo encima de cada función (qué hace, parámetros relevantes y valor de retorno si no es obvio)
- Los índices de columna son los definitivos (más fiables que los nombres del ODS)
- Al escribir de vuelta al ODS, preservar siempre la fila de cabecera (fila 0) intacta
- No añadir ni eliminar columnas — solo modificar filas de datos
- Hacer backup del ODS antes de operaciones de escritura masiva

## Ficheros del proyecto

```
empresas.ods         # datos — NO modificar a mano mientras la app está abierta
app.py               # entrada principal Streamlit
ods_handler.py       # lectura y escritura del ODS
```
