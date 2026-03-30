# Empresas

Aplicación para gestionar un listado de empresas almacenado en un fichero `.ods` (hoja de cálculo de LibreOffice).

**Demo online:** https://feoempresas-demo.streamlit.app/

## Qué hace

Permite crear, ver, editar y eliminar registros de empresas desde una interfaz web que se abre en el navegador, sin necesidad de abrir LibreOffice. Los datos se guardan directamente en el fichero `empresas.ods`.

Además, puede enriquecer cada empresa con dos campos nuevos:
- `Descripción`: resumen corto del servicio/producto y tecnologías detectadas en la web.
- `Ciclo`: recomendación de encaje para `DAW`, `DAM` y/o `ASIR`.

## Tecnologías

**Python**
Lenguaje de programación con el que está escrita la aplicación.

**Streamlit**
Librería de Python que permite construir interfaces web (botones, tablas, formularios) escribiendo solo Python, sin necesidad de saber HTML, CSS ni JavaScript. Al ejecutar la app, Streamlit levanta un servidor local y abre la interfaz en el navegador.

**odfpy**
Librería de Python para leer y escribir ficheros en formato OpenDocument (`.ods`, `.odt`…). Los ficheros `.ods` son internamente un ZIP de XMLs; odfpy abstrae esa complejidad y permite acceder a los datos como si fueran objetos Python.

## Requisitos

- Python 3 instalado y disponible en el entorno actual
- Dependencias Python: `streamlit`, `pandas` y `odfpy`

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

En Windows:

```bash
python -m streamlit run app.py
```

En Linux o WSL:

```bash
python3 -m streamlit run app.py
```

Se abrirá automáticamente en el navegador en `http://localhost:8501`.

## Estructura del proyecto

```
empresas.ods        # fichero de datos (no abrir en LibreOffice mientras la app esté en marcha)
app.py              # interfaz de usuario
ods_handler.py      # lectura y escritura del ODS
enrich_empresas.py  # enriquecimiento masivo del ODS
scrape_empresas.js  # scraping web con Playwright
CLAUDE.md           # instrucciones para los agentes de IA
README.md           # este fichero
```

## Copias de seguridad

Cada vez que se guarda un cambio, la aplicación crea automáticamente una copia del fichero en la carpeta `backups/` con la fecha y hora en el nombre (por ejemplo `backups/empresas_backup_20260313_103045.ods`).

## Enriquecimiento masivo

Para rellenar `Descripción` y `Ciclo` desde las webs del ODS:

```bash
python3 enrich_empresas.py
```

El script:
- usa `scrape_empresas.js` con Playwright para visitar la web de cada empresa,
- genera una descripción de menos de 400 caracteres,
- clasifica la empresa en `DAW`, `DAM`, `ASIR` o combinaciones separadas por `/`,
- y guarda el resultado directamente en `empresas.ods`, creando backups automáticos en cada lote.
