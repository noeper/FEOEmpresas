# Empresas CRUD

Aplicación local para gestionar el fichero `empresas.ods`. Es una app de uso personal con un único usuario y una interfaz web hecha con Streamlit.

## Objetivo del proyecto

- Permitir crear, listar, filtrar, editar y eliminar empresas sin abrir LibreOffice.
- Persistir los cambios directamente en `empresas.ods`.
- Mantener la hoja principal y las tablas de referencia del ODS como fuente de verdad.

## Stack y ejecución

- Python: `C:/Users/Noemi/AppData/Local/Programs/Python/Python314/python.exe`
- UI: Streamlit
- Datos ODS: odfpy
- Soporte tabular: pandas

Ejecutar:

```bash
C:/Users/Noemi/AppData/Local/Programs/Python/Python314/python.exe -m streamlit run app.py
```

La app abre en `http://localhost:8501`.

## Archivos relevantes

- `app.py`: interfaz Streamlit, filtros, tabla, formularios y validaciones.
- `ods_handler.py`: lectura y escritura del fichero ODS.
- `empresas.ods`: base de datos real del proyecto.
- `README.md`: descripción funcional y requisitos.
- `CLAUDE.md`: documento fuente de instrucciones anteriores para agentes.

## Archivos que no interesan

- No leer ni usar `empresas_backuu_*.ods`: son backups irrelevantes.
- Tampoco usar backups automáticos `empresas_backup_*.ods` como fuente de verdad salvo que el usuario pida una restauración o una auditoría.

## Modelo de datos ODS

La hoja principal es `Empresas` y la fila `0` es la cabecera. Los datos empiezan en la fila `1`.

Columnas de datos usadas por la app:

| Índice | Campo interno | Nombre en ODS |
|---|---|---|
| 0 | `nombre` | NOMBRE EMPRESA |
| 1 | `estado` | ESTADO EMPRESA |
| 2 | `observaciones` | OBSERVACIONES |
| 3 | `web` | WEB |
| 4 | `localidad` | LOCALIDAD |
| 5 | `correo_empresa` | CORREO EMPRESA |
| 6 | `tfno_empresa` | TFNO EMPRESA |
| 7 | `extension_tfno` | EXTENSIÓN TFNO |
| 8 | `contacto` | CONTACTO |
| 9 | `correo_contacto` | CORREO CONTACTO |
| 10 | `tfno_contacto` | TFNO CONTACTO |
| 11 | `tecnologias` | TECNOLOGÍAS |
| 12 | `regimen` | RÉGIMEN |
| 13 | `profesor` | PROFESOR |
| 14 | `descripcion` | DESCRIPCION |
| 15 | `ciclo` | CICLO |

Notas importantes:

- `ods_handler.py` trabaja con `NUM_COLS = 16`.
- Al leer filas, las celdas repetidas del ODS se expanden con `numbercolumnsrepeated`.

## Tablas de referencia

La app carga estas tablas desde hojas auxiliares del mismo ODS:

- `Localizacion`
- `Profesor`
- `Regimen`
- `Estado_empresa`

En código, `read_all_lookups()` asume estos índices:

- `localizacion`: hoja 1
- `profesor`: hoja 2
- `regimen`: hoja 3
- `estado_empresa`: hoja 4

Si cambia el orden de hojas del ODS, habrá que actualizar esos índices.

## Comportamiento actual de la app

- Cachea las tablas de referencia con `@st.cache_data`.
- Carga empresas en `st.session_state.df`.
- Filtra por nombre, estado, profesor y localidad.
- Permite selección de una única fila en la tabla.
- Valida nombre obligatorio, correo, URL y teléfono antes de guardar.
- Al guardar o eliminar, escribe todo el dataset y limpia la caché de Streamlit.
- Antes de cada escritura, crea un backup automático con formato `empresas_backup_YYYYMMDD_HHMMSS.ods`.

## Restricciones y convenciones

- No modificar manualmente `empresas.ods` mientras la app esté abierta.
- Preservar siempre la fila de cabecera al escribir.
- No añadir ni eliminar columnas; solo modificar filas de datos.
- Los índices de columna son más fiables que los nombres visibles del ODS.
- Verificar siempre con datos reales si aparecen problemas con tildes, eñes u otros caracteres especiales al leer el ODS.
- Añadir un docstring claro encima de cada función nueva o modificada.
- Todo texto introducido por el usuario debe sanearse antes de validarse y antes de persistirse.
- El saneado mínimo de texto consiste en aplicar `strip()` para eliminar whitespace inicial y final.
- No eliminar espacios internos salvo que una validación específica del campo lo requiera.
- El escape debe aplicarse al renderizar contenido de usuario en contextos que puedan interpretar HTML o marcado.
- No almacenar por defecto texto escapado en `empresas.ods`; en disco deben guardarse datos saneados, no entidades HTML.

## Detalles de implementación a tener en cuenta

- `app.py` identifica la fila a editar o eliminar por `nombre`, asumiendo que es suficientemente único. Si hubiera nombres duplicados, puede afectar a la fila equivocada.
- `write_empresas()` reescribe por completo la hoja `Empresas` excepto la cabecera.
- `read_lookup()` y `read_empresas()` cargan el ODS desde disco en cada llamada; si se toca rendimiento, revisar este patrón con cuidado.
- La validación de `web` permite URLs con o sin `http://` o `https://`.
- `correo_empresa` admite explícitamente `N/D` como valor no email en el formulario.

## Flujo recomendado para cambios

1. Leer `README.md`, `app.py` y `ods_handler.py`.
2. Tratar `empresas.ods` como la fuente de verdad.
3. Si el cambio afecta a persistencia, revisar que no se rompa la conservación de cabecera ni la creación de backups.
4. Si el cambio afecta a formularios, mantener compatibilidad con los nombres de columna definidos en `COLUMNS`.
5. Si el cambio afecta a tablas de referencia, confirmar que los índices de hoja siguen siendo correctos.

## Alcance para futuros agentes

- Priorizar cambios en `app.py` y `ods_handler.py`.
- No basarse en backups para entender el estado actual de los datos.
- Si hay que depurar datos corruptos o problemas de encoding, trabajar siempre contra el ODS real y con copias de seguridad preservadas.
