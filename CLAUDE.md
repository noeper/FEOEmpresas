# Empresas CRUD

Aplicación local para gestionar el fichero `empresas.ods`. Uso personal (usuario único).

## Stack

- **Python**: Python 3 disponible en el entorno actual
- **UI**: Streamlit
- **ODS**: odfpy
- **Fichero de datos**: `empresas.ods` (en la raíz del proyecto)

## Ejecutar la aplicación

En Windows:

```bash
python -m streamlit run app.py
```

En Linux o WSL:

```bash
python3 -m streamlit run app.py
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

## Convenciones Streamlit

### Caché
- Cachear con `@st.cache_data` toda función que lea del ODS, usando `mtime: float` como primer parámetro para invalidar automáticamente al cambiar el fichero
- Patrón: `@st.cache_data\ndef get_datos(mtime: float): return read_...()` — llamar siempre con `get_datos(mtime=get_ods_mtime())`
- No usar `st.cache_data.clear()` global tras guardar; solo invalidar la función cacheada concreta (`.clear()` sobre la función, no sobre toda la caché)
- Usar `@st.cache_resource` únicamente para recursos no serializables que se comparten entre sesiones (no aplica aquí)

### Session state
- Inicializar todas las claves con `if 'clave' not in st.session_state:` al principio del script, nunca en medio
- Guardar en session_state los DataFrames principales (df, interacciones, num_estudiantes) para evitar releer el ODS en cada rerun
- No almacenar en session_state objetos no serializables (conexiones, handles de fichero)
- Usar prefijos descriptivos en las claves para evitar colisiones entre secciones: `_sel_id`, `accion_int`, etc. — ya aplicado, mantenerlo

### Botones y reruns
- Preferir callbacks `on_click=` para cambiar session_state en lugar del patrón `if st.button(): st.session_state.x = ...; st.rerun()` — los callbacks se ejecutan antes del rerun, garantizando consistencia
- Usar `st.rerun()` solo cuando sea estrictamente necesario (p.ej. tras guardar datos); no para simples cambios de vista que un callback resolvería
- No anidar widgets ni botones dentro de `if st.button():` — el contenido solo vive un rerun

### Formularios
- Usar `st.form` cuando el usuario necesite rellenar varios campos antes de confirmar — evita reruns en cada keystroke
- Solo el `st.form_submit_button` puede tener callback dentro de un form; los demás widgets del form no
- No anidar forms dentro de forms

### Datos tabulares
- Usar `st.dataframe` con `on_select="rerun"` para tablas seleccionables de solo lectura (ya aplicado)
- Usar `st.data_editor` si se quiere edición directa en tabla (alternativa a formularios para campos simples)
- Para tablas grandes, configurar `height=` explícito para no desplazar el resto de la UI

### Orden de definición en app.py
El fichero sigue este orden estricto (Streamlit ejecuta el script de arriba a abajo y llama funciones en línea):
1. Imports y configuración (`st.set_page_config`)
2. Funciones puras y helpers (load/save, normalize, validadores, `_idx`)
3. Funciones de UI (`empresa_form`, `empresa_ficha`)
4. Funciones decoradas con `@st.dialog` o `@st.fragment` — siempre después de las funciones que invocan
5. Inicialización de session state y procesamiento de resultados pendientes
6. Código de UI ejecutable (widgets, tablas, lógica de sección principal)

Nunca colocar código ejecutable (widgets, lógica condicional) antes de las definiciones de funciones que ese código llama.

### ods_handler.py
- Cada función de lectura debe abrir el ODS una sola vez (`doc = load(ODS_PATH)`) y extraer todas las hojas que necesite en esa misma llamada — no llamar a `load()` varias veces dentro de la misma operación lógica

## Ficheros del proyecto

```
empresas.ods         # datos — NO modificar a mano mientras la app está abierta
app.py               # entrada principal Streamlit
ods_handler.py       # lectura y escritura del ODS
```
