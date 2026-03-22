import html
import os
import re
import streamlit as st
import pandas as pd
from ods_handler import ODS_PATH, read_empresas, write_empresas, read_all_lookups

st.set_page_config(page_title="Empresas", layout="wide")


@st.cache_data
def get_lookups():
    """Carga las tablas de referencia del ODS y las cachea para toda la sesión."""
    return read_all_lookups()


def load_data():
    """Lee todas las empresas del ODS y las devuelve como DataFrame."""
    df = pd.DataFrame(read_empresas())
    for column in ('descripcion', 'id_empresa'):
        if column not in df.columns:
            df[column] = ''
    return df


def get_ods_mtime():
    """Devuelve la fecha de modificación del ODS para detectar cambios externos."""
    return os.path.getmtime(ODS_PATH)


def save_data(df):
    """Persiste el DataFrame completo en el ODS e invalida la caché de lookups."""
    write_empresas(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()
    st.cache_data.clear()


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
        st.session_state.ods_mtime = get_ods_mtime()
    except Exception as e:
        st.error(f"No se pudo cargar el fichero de datos: {e}")
        st.stop()

try:
    current_ods_mtime = get_ods_mtime()
except Exception as e:
    st.error(f"No se pudo comprobar el fichero de datos: {e}")
    st.stop()

if st.session_state.get('ods_mtime') != current_ods_mtime:
    try:
        st.session_state.df = load_data()
        st.session_state.ods_mtime = current_ods_mtime
    except Exception as e:
        st.error(f"No se pudo recargar el fichero de datos: {e}")
        st.stop()

try:
    lookups = get_lookups()
except Exception as e:
    st.error(f"No se pudieron cargar las tablas de referencia: {e}")
    st.stop()
df_all = st.session_state.df

# ── Título ──────────────────────────────────────────────────────────────────
st.title("Empresas")

if st.button("Recargar desde ODS"):
    try:
        st.session_state.df = load_data()
        st.session_state.ods_mtime = get_ods_mtime()
        st.rerun()
    except Exception as e:
        st.error(f"No se pudo recargar el fichero de datos: {e}")

# ── Filtros ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
with col1:
    search = st.text_input("Buscar nombre", placeholder="Escribe para filtrar…")
with col2:
    f_estado = st.selectbox("Estado", ["(todos)"] + lookups['estado_empresa'])
with col3:
    f_profesor = st.selectbox("Profesor", ["(todos)"] + lookups['profesor'])
with col4:
    f_localidad = st.selectbox("Localidad", ["(todas)"] + lookups['localizacion'])

mask = pd.Series([True] * len(df_all))
if search:
    mask &= df_all['nombre'].str.contains(search, case=False, na=False)
if f_estado != "(todos)":
    mask &= df_all['estado'] == f_estado
if f_profesor != "(todos)":
    mask &= df_all['profesor'] == f_profesor
if f_localidad != "(todas)":
    mask &= df_all['localidad'] == f_localidad

df_view = df_all[mask].reset_index(drop=True)

# ── Tabla ────────────────────────────────────────────────────────────────────
st.write(f"**{len(df_view)}** empresa(s)")

selection = st.dataframe(
    df_view[['id_empresa', 'nombre', 'estado', 'localidad', 'regimen', 'profesor', 'web', 'descripcion']],
    use_container_width=True,
    hide_index=False,
    on_select="rerun",
    selection_mode="single-row",
)

selected_row = None
if selection and selection.selection.rows:
    selected_row = df_view.iloc[selection.selection.rows[0]]

st.divider()

# ── Acciones ─────────────────────────────────────────────────────────────────
tab_nueva, tab_editar, tab_eliminar = st.tabs(["➕ Nueva empresa", "✏️ Editar", "🗑️ Eliminar"])

EMPTY = {col: '' for col in df_all.columns} | {'estado': 'Empresa nueva'}


def empresa_form(key, defaults=None):
    """Renderiza el formulario de empresa y devuelve datos saneados, con `nombre` en mayúsculas."""
    d = defaults or EMPTY
    field_errors = st.session_state.get('form_field_errors', set())
    with st.form(key):
        c1, c2 = st.columns(2)
        with c1:
            nombre        = st.text_input("Nombre empresa *", value=d.get('nombre', ''))
            if 'nombre' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ El nombre es obligatorio.</p>', unsafe_allow_html=True)
            estado        = st.selectbox("Estado", lookups['estado_empresa'],
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
            contacto      = st.text_input("Contacto", value=d.get('contacto', ''))
            correo_con    = st.text_input("Correo contacto", value=d.get('correo_contacto', ''))
            if 'correo_con' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Asegúrate de incluir una @ y un dominio (ejemplo: nombre@correo.com). </p>', unsafe_allow_html=True)
            tfno_con      = st.text_input("Teléfono contacto", value=d.get('tfno_contacto', ''))
            if 'tfno_con' in field_errors:
                st.markdown('<p style="color:#ff4b4b;font-size:0.8em;margin-top:-12px">⚠ Formato inválido. Ejemplo válido: 612345678 o +34612345678</p>', unsafe_allow_html=True)
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
                st.rerun()  # segundo rerun para que los indicadores de campo aparezcan

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


# ── Tab nueva ────────────────────────────────────────────────────────────────
with tab_nueva:
    result = empresa_form("form_nueva")
    if result:
        existing_ids = pd.to_numeric(df_all['id_empresa'], errors='coerce').dropna()
        result['id_empresa'] = str(int(existing_ids.max()) + 1) if not existing_ids.empty else '1'
        new_row = pd.DataFrame([result])
        st.session_state.df = pd.concat([df_all, new_row], ignore_index=True)
        try:
            save_data(st.session_state.df)
            st.success(f"Empresa añadida: {html.escape(result['nombre'])}")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")

# ── Tab editar ───────────────────────────────────────────────────────────────
with tab_editar:
    if selected_row is None:
        st.info("Selecciona una fila en la tabla para editar.")
    else:
        st.write(f"Editando: {html.escape(str(selected_row['nombre']))}")
        if selected_row.get('descripcion'):
            st.caption(html.escape(str(selected_row['descripcion'])))
        result = empresa_form("form_editar", defaults=selected_row.to_dict())
        if result:
            # Find the row in the full df by nombre (unique enough) and update
            idx = df_all.index[df_all['nombre'] == selected_row['nombre']].tolist()
            if idx:
                for col, val in result.items():
                    st.session_state.df.at[idx[0], col] = val
                try:
                    save_data(st.session_state.df)
                    st.success("Cambios guardados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

# ── Tab eliminar ─────────────────────────────────────────────────────────────
with tab_eliminar:
    if selected_row is None:
        st.info("Selecciona una fila en la tabla para eliminar.")
    else:
        st.warning(
            "¿Eliminar "
            f"{html.escape(str(selected_row['nombre']))}"
            "? Esta acción crea un backup automático antes de guardar."
        )
        if st.button("Confirmar eliminación", type="primary"):
            st.session_state.df = df_all[df_all['nombre'] != selected_row['nombre']].reset_index(drop=True)
            try:
                save_data(st.session_state.df)
                st.success("Empresa eliminada.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo eliminar: {e}")
