import html
import json
import os
import re
from datetime import date
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ods_handler import (
    ODS_PATH,
    read_empresas, write_empresas,
    read_interacciones, write_interacciones,
    read_num_estudiantes, write_num_estudiantes,
    read_all_lookups,
)

st.set_page_config(page_title="Empresas", layout="wide")

CORREO_INICIAL_PATH = os.path.join(os.path.dirname(__file__), 'correo-inicial.html')


_LOOKUPS_VER = 3  # incrementar cuando cambie read_all_lookups()


@st.cache_data
def get_lookups(mtime: float, _ver: int = _LOOKUPS_VER):
    """Carga las tablas de referencia del ODS y las cachea por mtime del fichero."""
    return read_all_lookups()


def load_data():
    """Lee todas las empresas del ODS y las devuelve como DataFrame."""
    df = pd.DataFrame(read_empresas())
    for column in ('descripcion', 'id_empresa'):
        if column not in df.columns:
            df[column] = ''
    return df


def load_interacciones():
    """Lee todos los registros de interacciones del ODS y los devuelve como DataFrame."""
    rows = read_interacciones()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id_empresa', 'tipo', 'descripcion', 'fecha', 'profesor'])


def load_num_estudiantes():
    """Lee todos los registros de alumnos del ODS y los devuelve como DataFrame."""
    rows = read_num_estudiantes()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id_empresa', 'num_alumnos', 'grupo'])


def get_ods_mtime():
    """Devuelve la fecha de modificación del ODS para detectar cambios externos."""
    return os.path.getmtime(ODS_PATH)


def save_data(df):
    """Persiste el DataFrame completo en el ODS e invalida la caché de lookups."""
    write_empresas(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()
    st.cache_data.clear()


def save_interacciones(df):
    """Persiste el DataFrame de interacciones en el ODS."""
    write_interacciones(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()


def save_num_estudiantes(df):
    """Persiste el DataFrame de alumnos en el ODS."""
    write_num_estudiantes(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()


def _normalize_text(value):
    """Normaliza un campo de texto eliminando whitespace inicial y final."""
    return value.strip() if isinstance(value, str) else value


def _normalize_nombre(value):
    """Normaliza el nombre de empresa eliminando whitespace exterior y convirtiéndolo a mayúsculas."""
    normalized = _normalize_text(value)
    return normalized.upper() if isinstance(normalized, str) else normalized


# ── Estado inicial ──────────────────────────────────────────────────────────
if 'df' not in st.session_state:
    try:
        st.session_state.df = load_data()
        st.session_state.interacciones = load_interacciones()
        st.session_state.num_estudiantes = load_num_estudiantes()
        st.session_state.ods_mtime = get_ods_mtime()
    except Exception as e:
        st.error(f"No se pudo cargar el fichero de datos: {e}")
        st.stop()

if 'accion' not in st.session_state:
    st.session_state.accion = None
if 'accion_int' not in st.session_state:
    st.session_state.accion_int = None
if 'accion_alu' not in st.session_state:
    st.session_state.accion_alu = None

try:
    current_ods_mtime = get_ods_mtime()
except Exception as e:
    st.error(f"No se pudo comprobar el fichero de datos: {e}")
    st.stop()

if st.session_state.get('ods_mtime') != current_ods_mtime:
    try:
        st.session_state.df = load_data()
        st.session_state.interacciones = load_interacciones()
        st.session_state.num_estudiantes = load_num_estudiantes()
        st.session_state.ods_mtime = current_ods_mtime
    except Exception as e:
        st.error(f"No se pudo recargar el fichero de datos: {e}")
        st.stop()

try:
    lookups = get_lookups(mtime=get_ods_mtime())
except Exception as e:
    st.error(f"No se pudieron cargar las tablas de referencia: {e}")
    st.stop()
df_all = st.session_state.df

# ── Título ───────────────────────────────────────────────────────────────────
col_t, col_b = st.columns([5, 1])
with col_t:
    st.title("Empresas")
with col_b:
    st.write("")
    if st.button("➕ Nueva empresa", use_container_width=True):
        st.session_state.accion = 'nueva'
        st.session_state.pop('_sel_id', None)
        st.rerun()

# ── Filtros ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
with col1:
    nombres = sorted(df_all['nombre'].dropna().unique().tolist())
    search = st.selectbox("Buscar nombre", options=nombres, index=None, placeholder="Escribe para filtrar…")
with col2:
    f_estado = st.selectbox("Estado", ["(todos)"] + lookups['estado_empresa'])
with col3:
    f_profesor = st.selectbox("Profesor", ["(todos)"] + lookups['profesor'])
with col4:
    f_localidad = st.selectbox("Localidad", ["(todas)"] + lookups['localizacion'])

mask = pd.Series([True] * len(df_all))
if search:
    mask &= df_all['nombre'] == search
if f_estado != "(todos)":
    mask &= df_all['estado'] == f_estado
if f_profesor != "(todos)":
    mask &= df_all['profesor'] == f_profesor
if f_localidad != "(todas)":
    mask &= df_all['localidad'] == f_localidad

df_view = df_all[mask].reset_index(drop=True)

# ── Columnas calculadas ───────────────────────────────────────────────────────
_int_counts = (
    st.session_state.interacciones
    .groupby('id_empresa')
    .size()
    .rename('interacciones')
)
_alu_sums = (
    st.session_state.num_estudiantes
    .assign(num_alumnos=lambda d: pd.to_numeric(d['num_alumnos'], errors='coerce').fillna(0))
    .groupby('id_empresa')['num_alumnos']
    .sum()
    .astype(int)
    .rename('alumnos')
)
df_view = (
    df_view
    .join(_int_counts, on='id_empresa')
    .join(_alu_sums, on='id_empresa')
    .fillna({'interacciones': 0, 'alumnos': 0})
    .astype({'interacciones': int, 'alumnos': int})
)

# ── Tabla ────────────────────────────────────────────────────────────────────
st.write(f"**{len(df_view)}** empresa(s)")

selection = st.dataframe(
    df_view[['nombre', 'estado', 'localidad', 'regimen', 'profesor', 'interacciones', 'alumnos', 'web', 'descripcion']],
    use_container_width=True,
    hide_index=False,
    on_select="rerun",
    selection_mode="single-row",
    height=250,
)

selected_row = None
if selection and selection.selection.rows:
    selected_row = df_view.iloc[selection.selection.rows[0]]
    st.session_state['_sel_id'] = str(selected_row['id_empresa'])
elif st.session_state.get('_sel_id'):
    matching = df_view[df_view['id_empresa'] == st.session_state['_sel_id']]
    if not matching.empty:
        selected_row = matching.iloc[0]
    else:
        st.session_state.pop('_sel_id', None)

st.divider()

EMPTY = {col: '' for col in df_all.columns} | {'estado': 'Empresa nueva'}


def empresa_form(key, defaults=None, lock_estado=False):
    """Renderiza el formulario de empresa y devuelve datos saneados, con `nombre` en mayúsculas.
    Si lock_estado=True el campo Estado se muestra como solo lectura.
    """
    d = defaults or EMPTY
    field_errors = st.session_state.get('form_field_errors', set())
    with st.form(key):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Datos de la empresa**")
            nombre        = st.text_input("Nombre empresa *", value=d.get('nombre', ''))
            if 'nombre' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ El nombre es obligatorio.</p>', unsafe_allow_html=True)
            if lock_estado:
                st.text_input("Estado de la empresa", value=d.get('estado', ''), disabled=True)
                estado = d.get('estado', '')
            else:
                estado = st.selectbox("Estado de la empresa", lookups['estado_empresa'],
                                      index=_idx(lookups['estado_empresa'], d.get('estado')))
            observaciones = st.text_area("Observaciones", value=d.get('observaciones', ''), height=80)
            web           = st.text_input("Web", value=d.get('web', ''))
            if 'web' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Ejemplo válido: https://empresa.com</p>', unsafe_allow_html=True)
            localidad     = st.selectbox("Localidad", [''] + lookups['localizacion'],
                                         index=_idx([''] + lookups['localizacion'], d.get('localidad')))
            correo_emp    = st.text_input("Correo empresa", value=d.get('correo_empresa', ''))
            if 'correo_emp' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Asegúrate de incluir una @ y un dominio (ejemplo: nombre@correo.com). Si quieres indicar que no está disponible en la web, escribe N/D.</p>', unsafe_allow_html=True)
            tfno_emp      = st.text_input("Teléfono empresa", value=d.get('tfno_empresa', ''))
            if 'tfno_emp' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Ejemplo válido: 612345678 o +34612345678</p>', unsafe_allow_html=True)
            ext_tfno      = st.text_input("Extensión", value=d.get('extension_tfno', ''))
        with c2:
            st.markdown("**Persona de contacto**")
            contacto      = st.text_input("Contacto", value=d.get('contacto', ''))
            correo_con    = st.text_input("Correo contacto", value=d.get('correo_contacto', ''))
            if 'correo_con' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Asegúrate de incluir una @ y un dominio (ejemplo: nombre@correo.com). </p>', unsafe_allow_html=True)
            tfno_con      = st.text_input("Teléfono contacto", value=d.get('tfno_contacto', ''))
            if 'tfno_con' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Ejemplo válido: 612345678 o +34612345678</p>', unsafe_allow_html=True)
            st.markdown("**Otros datos**")
            tecnologias   = st.text_area("Tecnologías", value=d.get('tecnologias', ''), height=80)
            descripcion   = st.text_area("Descripción", value=d.get('descripcion', ''), height=100)
            regimen       = st.selectbox("Régimen", [''] + lookups['regimen'],
                                         index=_idx([''] + lookups['regimen'], d.get('regimen')))
            profesor      = st.selectbox("Profesor", [''] + lookups['profesor'],
                                         index=_idx([''] + lookups['profesor'], d.get('profesor')))

        submitted = st.form_submit_button("Guardar")
        if submitted:
            new_field_errors = set()
            normalized = {
                'nombre': _normalize_nombre(nombre),
                'observaciones': _normalize_text(observaciones),
                'web': _normalize_text(web),
                'correo_empresa': _normalize_text(correo_emp),
                'tfno_empresa': _normalize_text(tfno_emp),
                'extension_tfno': _normalize_text(ext_tfno),
                'contacto': _normalize_text(contacto),
                'correo_contacto': _normalize_text(correo_con),
                'tfno_contacto': _normalize_text(tfno_con),
                'tecnologias': _normalize_text(tecnologias),
                'descripcion': _normalize_text(descripcion),
            }

            if not normalized['nombre']:
                new_field_errors.add('nombre')

            if (
                normalized['correo_empresa']
                and normalized['correo_empresa'].upper() != 'N/D'
                and not _valid_email(normalized['correo_empresa'])
            ):
                new_field_errors.add('correo_emp')
            if normalized['correo_contacto'] and not _valid_email(normalized['correo_contacto']):
                new_field_errors.add('correo_con')
            if normalized['web'] and not _valid_url(normalized['web']):
                new_field_errors.add('web')
            if normalized['tfno_empresa'] and not _valid_phone(normalized['tfno_empresa']):
                new_field_errors.add('tfno_emp')
            if normalized['tfno_contacto'] and not _valid_phone(normalized['tfno_contacto']):
                new_field_errors.add('tfno_con')

            st.session_state.form_field_errors = new_field_errors

            if new_field_errors:
                st.rerun()

            st.session_state.form_field_errors = set()

            return {
                'nombre': normalized['nombre'],
                'estado': estado,
                'observaciones': normalized['observaciones'],
                'web': normalized['web'],
                'localidad': localidad,
                'correo_empresa': normalized['correo_empresa'],
                'tfno_empresa': normalized['tfno_empresa'],
                'extension_tfno': normalized['extension_tfno'],
                'contacto': normalized['contacto'],
                'correo_contacto': normalized['correo_contacto'],
                'tfno_contacto': normalized['tfno_contacto'],
                'tecnologias': normalized['tecnologias'],
                'descripcion': normalized['descripcion'],
                'regimen': regimen,
                'profesor': profesor,
            }
    return None


def empresa_ficha(row):
    """Muestra los datos de una empresa en modo solo lectura, en dos columnas."""
    st.subheader(row.get('nombre', ''))
    c1, c2 = st.columns(2)
    campos_c1 = [
        ('Estado', 'estado'),
        ('Localidad', 'localidad'),
        ('Régimen', 'regimen'),
        ('Web', 'web'),
        ('Correo empresa', 'correo_empresa'),
        ('Teléfono empresa', 'tfno_empresa'),
        ('Extensión', 'extension_tfno'),
        ('Observaciones', 'observaciones'),
    ]
    campos_c2 = [
        ('Contacto', 'contacto'),
        ('Correo contacto', 'correo_contacto'),
        ('Teléfono contacto', 'tfno_contacto'),
        ('Profesor', 'profesor'),
        ('Tecnologías', 'tecnologias'),
        ('Descripción', 'descripcion'),
    ]
    with c1:
        for label, key in campos_c1:
            val = row.get(key, '')
            if val:
                st.markdown(f"**{label}:** {html.escape(str(val))}")
    with c2:
        for label, key in campos_c2:
            val = row.get(key, '')
            if val:
                st.markdown(f"**{label}:** {html.escape(str(val))}")


def _idx(lst, val):
    """Safe index lookup for selectbox defaults."""
    try:
        return lst.index(val) if val in lst else 0
    except Exception:
        return 0


def _valid_email(email):
    """Comprueba que el string tiene formato básico de correo electrónico."""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def _valid_url(url):
    """Comprueba que el string tiene formato básico de URL web."""
    return bool(re.match(r'^(https?:\/\/)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z0-9]{2,}([\/\?#].*)?$', url))


def _valid_phone(phone):
    """Comprueba que el string tiene formato básico de teléfono (con o sin prefijo internacional)."""
    return bool(re.match(r'^\+?[0-9]{9,13}$', phone))


# ── Sección principal ─────────────────────────────────────────────────────────
if st.session_state.accion == 'nueva':
    st.subheader("Nueva empresa")
    if st.button("✖ Cancelar"):
        st.session_state.accion = None
        st.rerun()
    result = empresa_form("form_nueva")
    if result:
        existing_ids = pd.to_numeric(df_all['id_empresa'], errors='coerce').dropna()
        result['id_empresa'] = str(int(existing_ids.max()) + 1) if not existing_ids.empty else '1'
        new_row = pd.DataFrame([result])
        st.session_state.df = pd.concat([df_all, new_row], ignore_index=True)
        try:
            save_data(st.session_state.df)
            st.session_state.accion = None
            st.success(f"Empresa añadida: {html.escape(result['nombre'])}")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")

elif selected_row is not None:
    accion = st.session_state.accion

    if accion == 'editar':
        # ── Editar ────────────────────────────────────────────────────────────
        st.subheader(f"Editando: {html.escape(str(selected_row['nombre']))}")
        if st.button("✖ Cancelar"):
            st.session_state.accion = None
            st.rerun()
        result = empresa_form("form_editar", defaults=selected_row.to_dict(), lock_estado=True)
        if result:
            idx = df_all.index[df_all['id_empresa'] == selected_row['id_empresa']].tolist()
            if idx:
                for col, val in result.items():
                    st.session_state.df.at[idx[0], col] = val
                try:
                    save_data(st.session_state.df)
                    st.session_state.accion = None
                    st.success("Cambios guardados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

    elif accion == 'eliminar':
        # ── Eliminar ──────────────────────────────────────────────────────────
        st.warning(
            f"¿Eliminar **{html.escape(str(selected_row['nombre']))}**? "
            "Esta acción crea un backup automático antes de guardar."
        )
        confirmar = st.checkbox("Confirmo que quiero eliminar esta empresa")
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("Confirmar eliminación", type="primary", disabled=not confirmar):
                st.session_state.df = df_all[df_all['id_empresa'] != selected_row['id_empresa']].reset_index(drop=True)
                try:
                    save_data(st.session_state.df)
                    st.session_state.accion = None
                    st.session_state.pop('_sel_id', None)
                    st.success("Empresa eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")
        with col_b:
            if st.button("✖ Cancelar"):
                st.session_state.accion = None
                st.rerun()

    else:
        # ── Ficha ─────────────────────────────────────────────────────────────
        empresa_ficha(selected_row.to_dict())
        col_e, col_d, _ = st.columns([1, 1, 5])
        with col_e:
            if st.button("✏️ Editar"):
                st.session_state.accion = 'editar'
                st.rerun()
        with col_d:
            if st.button("🗑️ Eliminar"):
                st.session_state.accion = 'eliminar'
                st.rerun()

    st.divider()

    # ── Tabs interacciones y alumnos ─────────────────────────────────────────
    tab_interacciones, tab_alumnos = st.tabs([
        "📞 Interacciones con la empresa", "🎓 Alumnos acogidos"
    ])

    # ── Tab interacciones ─────────────────────────────────────────────────────
    with tab_interacciones:
        empresa_id = str(selected_row['id_empresa'])

        # Resetear estado de interacciones al cambiar de empresa
        if st.session_state.get('_prev_empresa_id') != empresa_id:
            st.session_state.accion_int = None
            st.session_state.pop('_sel_int_idx', None)
            st.session_state['_prev_empresa_id'] = empresa_id

        df_int = st.session_state.interacciones
        df_emp_int = df_int[df_int['id_empresa'] == empresa_id].reset_index()
        # df_emp_int tiene columna 'index' con el índice original en session_state.interacciones

        # Cabecera con botón añadir
        col_h, col_btn = st.columns([5, 1])
        with col_h:
            st.write(f"Interacciones con **{html.escape(str(selected_row['nombre']))}**")
        with col_btn:
            if st.button("➕ Añadir", key="btn_nueva_int", use_container_width=True):
                st.session_state.accion_int = 'nueva'
                st.session_state.pop('_sel_int_idx', None)
                st.rerun()

        # Tabla de interacciones seleccionable
        if df_emp_int.empty:
            st.caption("Sin interacciones registradas.")
            sel_int = None
        else:
            sel_int = st.dataframe(
                df_emp_int[['tipo', 'descripcion', 'fecha', 'profesor']],
                use_container_width=True,
                hide_index=False,
                on_select="rerun",
                selection_mode="single-row",
                height=200,
            )
            if sel_int and sel_int.selection.rows:
                pos = sel_int.selection.rows[0]
                st.session_state['_sel_int_idx'] = int(df_emp_int.iloc[pos]['index'])
                st.session_state.accion_int = None

        # Sección detalle / formulario
        orig_idx = st.session_state.get('_sel_int_idx')
        sel_int_row = (
            st.session_state.interacciones.loc[orig_idx]
            if orig_idx is not None and orig_idx in st.session_state.interacciones.index
            else None
        )

        st.divider()

        if st.session_state.accion_int == 'nueva':
            # ── Formulario nueva interacción ──────────────────────────────────
            col_tit, col_can = st.columns([5, 1])
            with col_tit:
                st.subheader("Añadir interacción")
            with col_can:
                st.write("")
                if st.button("✖ Cancelar", key="cancel_int"):
                    st.session_state.accion_int = None
                    st.rerun()
            if os.path.exists(CORREO_INICIAL_PATH):
                with open(CORREO_INICIAL_PATH, 'r', encoding='utf-8') as f:
                    _correo_contenido = f.read()
                _correo_js = json.dumps(_correo_contenido)
                components.html(f"""
                    <style>
                        body {{ margin: 0; font-family: sans-serif; }}
                        button {{
                            background: #1a7abf; color: white; border: none;
                            border-radius: 6px; padding: 6px 14px; font-size: 14px;
                            cursor: pointer; display: flex; align-items: center; gap: 6px;
                        }}
                        button:hover {{ background: #155f96; }}
                        #msg {{ margin-top: 4px; font-size: 12px; color: #21a656; min-height: 16px; }}
                    </style>
                    <button title="Copia el contenido del primer mensaje de solicitud de colaboración a la empresa con datos de los ciclos, calendario y enlaces a githubs del alumnado"
                            onclick="doCopy()">
                        📋 Copia y pega este mensaje en tu correo para enviárselo a las empresas
                    </button>
                    <div id="msg"></div>
                    <script>
                    async function doCopy() {{
                        const text = {_correo_js};
                        try {{
                            await navigator.clipboard.writeText(text);
                        }} catch (e) {{
                            // Fallback execCommand para entornos sin Clipboard API
                            const ta = document.createElement('textarea');
                            ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
                            document.body.appendChild(ta);
                            ta.focus(); ta.select();
                            document.execCommand('copy');
                            document.body.removeChild(ta);
                        }}
                        const msg = document.getElementById('msg');
                        msg.textContent = '✓ Copiado al portapapeles';
                        setTimeout(() => msg.textContent = '', 3000);
                    }}
                    </script>
                """, height=65)

            with st.form("form_add_interaccion"):
                c1, c2 = st.columns(2)
                with c1:
                    tipo_c  = st.selectbox("Tipo *", lookups['tipo_interaccion'])
                    fecha_c = st.date_input("Fecha de la interacción *", value=date.today(), format="DD/MM/YYYY")
                    st.caption(f"Estado actual: **{selected_row.get('estado', '—')}**")
                    estado_emp = st.selectbox(
                        "Actualizar estado a",
                        lookups['estado_empresa'],
                        index=_idx(lookups['estado_empresa'], selected_row.get('estado')),
                    )
                with c2:
                    profesor_c = st.selectbox("Profesor", [''] + lookups['profesor'])
                    desc_c     = st.text_area("Descripción", height=80)
                if st.form_submit_button("Guardar"):
                    if not tipo_c or not fecha_c:
                        st.error("Los campos Tipo y Fecha de la interacción son obligatorios.")
                    else:
                        new_row = pd.DataFrame([{
                            'id_empresa': empresa_id,
                            'tipo': tipo_c,
                            'descripcion': desc_c.strip(),
                            'fecha': fecha_c.strftime("%d/%m/%Y"),
                            'profesor': profesor_c,
                        }])
                        st.session_state.interacciones = pd.concat(
                            [st.session_state.interacciones, new_row], ignore_index=True
                        )
                        idx_emp = df_all.index[df_all['id_empresa'] == empresa_id].tolist()
                        if idx_emp:
                            st.session_state.df.at[idx_emp[0], 'estado'] = estado_emp
                        try:
                            save_interacciones(st.session_state.interacciones)
                            save_data(st.session_state.df)
                            st.session_state.accion_int = None
                            st.success("Interacción añadida.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo guardar: {e}")

        elif sel_int_row is not None:
            # ── Ficha interacción ─────────────────────────────────────────────
            c1, c2 = st.columns(2)
            with c1:
                for label, key in [('Tipo', 'tipo'), ('Fecha', 'fecha'), ('Profesor', 'profesor')]:
                    val = sel_int_row.get(key, '')
                    if val:
                        st.markdown(f"**{label}:** {html.escape(str(val))}")
            with c2:
                desc = sel_int_row.get('descripcion', '')
                if desc:
                    st.markdown(f"**Descripción:** {html.escape(str(desc))}")
            if st.button("🗑️ Eliminar interacción", key="btn_del_interaccion"):
                st.session_state.interacciones = (
                    st.session_state.interacciones
                    .drop(index=orig_idx)
                    .reset_index(drop=True)
                )
                st.session_state.pop('_sel_int_idx', None)
                try:
                    save_interacciones(st.session_state.interacciones)
                    st.success("Interacción eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")

    # ── Tab alumnos ───────────────────────────────────────────────────────────
    with tab_alumnos:
        empresa_id = str(selected_row['id_empresa'])

        # Resetear estado al cambiar de empresa
        if st.session_state.get('_prev_empresa_id_alu') != empresa_id:
            st.session_state.accion_alu = None
            st.session_state.pop('_sel_alu_idx', None)
            st.session_state['_prev_empresa_id_alu'] = empresa_id

        df_alu = st.session_state.num_estudiantes
        df_emp_alu = df_alu[df_alu['id_empresa'] == empresa_id].reset_index()

        # Cabecera con botón añadir
        col_h, col_btn = st.columns([5, 1])
        with col_h:
            st.write(f"Alumnos asignados a **{html.escape(str(selected_row['nombre']))}**")
        with col_btn:
            if st.button("➕ Añadir", key="btn_nueva_alu", use_container_width=True):
                st.session_state.accion_alu = 'nueva'
                st.session_state.pop('_sel_alu_idx', None)
                st.rerun()

        # Tabla seleccionable
        if df_emp_alu.empty:
            st.caption("Sin alumnos asignados.")
            sel_alu = None
        else:
            sel_alu = st.dataframe(
                df_emp_alu[['num_alumnos', 'grupo']],
                use_container_width=True,
                hide_index=False,
                on_select="rerun",
                selection_mode="single-row",
                height=200,
            )
            if sel_alu and sel_alu.selection.rows:
                pos = sel_alu.selection.rows[0]
                st.session_state['_sel_alu_idx'] = int(df_emp_alu.iloc[pos]['index'])
                st.session_state.accion_alu = None

        # Recuperar fila seleccionada
        orig_idx_alu = st.session_state.get('_sel_alu_idx')
        sel_alu_row = (
            st.session_state.num_estudiantes.loc[orig_idx_alu]
            if orig_idx_alu is not None and orig_idx_alu in st.session_state.num_estudiantes.index
            else None
        )

        st.divider()

        if st.session_state.accion_alu == 'nueva':
            # ── Formulario nueva asignación ───────────────────────────────────
            col_tit, col_can = st.columns([5, 1])
            with col_tit:
                st.subheader("Añadir asignación")
            with col_can:
                st.write("")
                if st.button("✖ Cancelar", key="cancel_alu"):
                    st.session_state.accion_alu = None
                    st.rerun()
            with st.form("form_add_alumnos"):
                c1, c2 = st.columns(2)
                with c1:
                    num_alu = st.number_input("Número de alumnos", min_value=1, step=1, value=1)
                with c2:
                    grupo_alu = st.selectbox("Grupo", lookups['grupo_estudiantes'])
                if st.form_submit_button("Guardar"):
                    es_primera = df_emp_alu.empty
                    new_row = pd.DataFrame([{
                        'id_empresa': empresa_id,
                        'num_alumnos': str(int(num_alu)),
                        'grupo': grupo_alu,
                    }])
                    st.session_state.num_estudiantes = pd.concat(
                        [st.session_state.num_estudiantes, new_row], ignore_index=True
                    )
                    idx_emp = df_all.index[df_all['id_empresa'] == empresa_id].tolist()
                    if idx_emp:
                        st.session_state.df.at[idx_emp[0], 'estado'] = 'Colabora'
                    try:
                        save_num_estudiantes(st.session_state.num_estudiantes)
                        save_data(st.session_state.df)
                        st.session_state.accion_alu = None
                        if es_primera:
                            st.toast("Asignación añadida. La empresa pasa al estado Colabora.")
                        else:
                            st.toast("Asignación añadida.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo guardar: {e}")

        elif sel_alu_row is not None:
            # ── Ficha asignación ──────────────────────────────────────────────
            st.markdown(f"**Grupo:** {html.escape(str(sel_alu_row.get('grupo', '')))}")
            st.markdown(f"**Número de alumnos:** {html.escape(str(sel_alu_row.get('num_alumnos', '')))}")
            if st.button("🗑️ Eliminar asignación", key="btn_del_alu"):
                st.session_state.num_estudiantes = (
                    st.session_state.num_estudiantes
                    .drop(index=orig_idx_alu)
                    .reset_index(drop=True)
                )
                quedan = st.session_state.num_estudiantes[
                    st.session_state.num_estudiantes['id_empresa'] == empresa_id
                ]
                if quedan.empty:
                    idx_emp = df_all.index[df_all['id_empresa'] == empresa_id].tolist()
                    if idx_emp:
                        st.session_state.df.at[idx_emp[0], 'estado'] = 'Pendiente de respuesta'
                st.session_state.pop('_sel_alu_idx', None)
                try:
                    save_num_estudiantes(st.session_state.num_estudiantes)
                    save_data(st.session_state.df)
                    if quedan.empty:
                        st.toast('Asignación eliminada. La empresa pasa al estado "Pendiente de respuesta".')
                    else:
                        st.toast("Asignación eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")

else:
    st.info("Selecciona una empresa en la tabla para ver su ficha.")
