import calendar
import html
import json
import os
import re
import textwrap
from datetime import date, datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from ods_handler import (
    ODS_PATH,
    read_empresas, write_empresas,
    read_interacciones, write_interacciones,
    read_num_estudiantes, write_num_estudiantes,
    read_github_alumnado, write_github_alumnado,
    read_all_lookups,
)

st.set_page_config(page_title="Empresas", layout="wide")

MAIL_TEMPLATES_DIR = Path(__file__).with_name('mail_templates')
APP_SETTINGS_PATH = Path(__file__).with_name('app_settings.json')
DEFAULT_APP_SETTINGS = {
    'calendario_primero_inicio': '',
    'calendario_primero_fin': '',
    'calendario_segundo_inicio': '',
    'calendario_segundo_fin': '',
    'festivos': [],
    'alternancia': [],
}

GITHUB_GRUPOS = ['1DAM', '2DAM', '1DAW', '2DAW', '1ASIR', '2ASIR']


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
    current_year = str(date.today().year)
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id_empresa', 'num_alumnos', 'grupo', 'anio'])
    if 'anio' not in df.columns:
        df['anio'] = current_year
    df['anio'] = df['anio'].replace('', pd.NA).fillna(current_year).astype(str)
    return df


def load_mail_templates():
    """Carga las plantillas JSON locales de correo y devuelve una lista ordenada de dicts válidos."""
    templates = []
    if not MAIL_TEMPLATES_DIR.exists():
        return templates

    for path in sorted(MAIL_TEMPLATES_DIR.glob('*.json')):
        try:
            with path.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if all(data.get(field) for field in ('id', 'label', 'subject', 'body')):
            html_path = None
            if data.get('html_file'):
                html_path = MAIL_TEMPLATES_DIR / str(data['html_file'])
            if html_path and html_path.exists():
                try:
                    data['html_body'] = html_path.read_text(encoding='utf-8')
                except OSError:
                    data['html_body'] = ''
            templates.append(data)
    return templates


def load_github_alumnado():
    """Lee todos los enlaces GitHub del alumnado y los devuelve como DataFrame."""
    rows = read_github_alumnado()
    current_course = _current_academic_course_label()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['enlace', 'grupo', 'curso_academico'])
    if 'curso_academico' not in df.columns:
        df['curso_academico'] = current_course
    df['curso_academico'] = df['curso_academico'].replace('', pd.NA).fillna(current_course).astype(str)
    for column in ('enlace', 'grupo'):
        if column not in df.columns:
            df[column] = ''
        df[column] = df[column].fillna('').astype(str)
    return df


def load_app_settings():
    """Carga la configuración general desde JSON local y completa cualquier clave ausente con defaults."""
    data = {}
    if APP_SETTINGS_PATH.exists():
        try:
            with APP_SETTINGS_PATH.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            data = {}

    settings = DEFAULT_APP_SETTINGS.copy()
    if isinstance(data, dict):
        for key, default_value in settings.items():
            if isinstance(default_value, list):
                raw_values = data.get(key, default_value)
                settings[key] = [
                    _normalize_text(str(value)) or ''
                    for value in raw_values
                    if _normalize_text(str(value)) or ''
                ] if isinstance(raw_values, list) else []
            else:
                settings[key] = _normalize_text(str(data.get(key, '') or '')) or ''
    return settings


def save_app_settings(settings):
    """Persiste la configuración general saneada en el JSON local y devuelve el valor guardado."""
    normalized = DEFAULT_APP_SETTINGS.copy()
    for key, default_value in normalized.items():
        if isinstance(default_value, list):
            raw_values = settings.get(key, default_value)
            normalized[key] = [
                _normalize_text(str(value)) or ''
                for value in raw_values
                if _normalize_text(str(value)) or ''
            ] if isinstance(raw_values, list) else []
        else:
            normalized[key] = _normalize_text(str(settings.get(key, '') or '')) or ''

    with APP_SETTINGS_PATH.open('w', encoding='utf-8') as handle:
        json.dump(normalized, handle, ensure_ascii=False, indent=2)
    return normalized


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
    if 'anio' not in df.columns:
        df['anio'] = str(date.today().year)
    df['anio'] = df['anio'].replace('', pd.NA).fillna(str(date.today().year)).astype(str)
    write_num_estudiantes(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()


def save_github_alumnado(df):
    """Persiste el DataFrame de enlaces GitHub del alumnado en el ODS."""
    if 'curso_academico' not in df.columns:
        df['curso_academico'] = _current_academic_course_label()
    df['curso_academico'] = df['curso_academico'].replace('', pd.NA).fillna(_current_academic_course_label()).astype(str)
    write_github_alumnado(df.to_dict('records'))
    st.session_state.ods_mtime = get_ods_mtime()


def _has_duplicate_alumno_asignacion(df, empresa_id, grupo, anio, exclude_idx=None):
    """Comprueba si ya existe una asignación con la misma tupla `(grupo, año)` para la empresa dada."""
    filtered = df[df['id_empresa'] == empresa_id]
    if exclude_idx is not None:
        filtered = filtered.drop(index=exclude_idx, errors='ignore')
    return ((filtered['grupo'] == grupo) & (filtered['anio'].astype(str) == str(anio))).any()


def _normalize_text(value):
    """Normaliza un campo de texto eliminando whitespace inicial y final."""
    return value.strip() if isinstance(value, str) else value


def _normalize_nombre(value):
    """Normaliza el nombre de empresa eliminando whitespace exterior y convirtiéndolo a mayúsculas."""
    normalized = _normalize_text(value)
    return normalized.upper() if isinstance(normalized, str) else normalized


def _current_academic_course_label(today=None):
    """Devuelve el curso académico actual con formato `YY-YY`."""
    current = today or date.today()
    start_year = current.year if current.month >= 9 else current.year - 1
    return f"{start_year % 100:02d}-{(start_year + 1) % 100:02d}"


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


def _valid_github_url(url):
    """Comprueba que el string tiene formato básico de perfil de GitHub."""
    return bool(re.match(r'^(https?:\/\/)?(www\.)?github\.com\/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?\/?$', url))


def _github_links_for_templates(df, academic_course):
    """Devuelve la lista de enlaces GitHub del curso indicado en formatos texto y HTML."""
    if df is None or df.empty:
        empty_text = "Pendiente de completar."
        empty_html = '<p style="margin:0; font-size:15px; line-height:1.6; color:#52606d;">Pendiente de completar.</p>'
        return {'text': empty_text, 'html': empty_html}

    filtered = df[df['curso_academico'].astype(str) == str(academic_course)].copy()
    if filtered.empty:
        empty_text = "Pendiente de completar."
        empty_html = '<p style="margin:0; font-size:15px; line-height:1.6; color:#52606d;">Pendiente de completar.</p>'
        return {'text': empty_text, 'html': empty_html}

    filtered['grupo'] = filtered['grupo'].fillna('').astype(str)
    filtered['enlace'] = filtered['enlace'].fillna('').astype(str)
    filtered = filtered.sort_values(['grupo', 'enlace']).reset_index(drop=True)

    text_lines = []
    html_items = []
    for _, record in filtered.iterrows():
        grupo = _normalize_text(record.get('grupo', '')) or 'Sin grupo'
        enlace = _normalize_text(record.get('enlace', '')) or ''
        if not enlace:
            continue
        text_lines.append(f"- {grupo}: {enlace}")
        enlace_esc = html.escape(enlace, quote=True)
        grupo_esc = html.escape(grupo)
        html_items.append(
            f'<li><strong>{grupo_esc}</strong> · '
            f'<a href="{enlace_esc}" style="color:#155f96; text-decoration:underline;">{enlace_esc}</a></li>'
        )

    if not text_lines:
        empty_text = "Pendiente de completar."
        empty_html = '<p style="margin:0; font-size:15px; line-height:1.6; color:#52606d;">Pendiente de completar.</p>'
        return {'text': empty_text, 'html': empty_html}

    return {
        'text': '\n'.join(text_lines),
        'html': f'<ul style="margin:0; padding-left:18px; font-size:15px; line-height:1.6;">{"".join(html_items)}</ul>',
    }


def _valid_phone(phone):
    """Comprueba que el string tiene formato básico de teléfono (con o sin prefijo internacional)."""
    return bool(re.match(r'^\+?[0-9]{9,13}$', phone))


def _mail_template_context(row, destinatario, settings=None):
    """Construye el contexto base para rellenar una plantilla a partir de la empresa seleccionada."""
    config = settings or DEFAULT_APP_SETTINGS
    current_course = _current_academic_course_label()
    github_links = _github_links_for_templates(st.session_state.get('github_alumnado'), current_course)
    return {
        'nombre_empresa': _normalize_text(str(row.get('nombre', '') or '')) or '',
        'contacto': _normalize_text(str(row.get('contacto', '') or '')) or '',
        'profesor': _normalize_text(str(row.get('profesor', '') or '')) or '',
        'correo_destino': _normalize_text(destinatario) or '',
        'fecha_hoy': date.today().strftime('%d/%m/%Y'),
        'curso_academico_actual': current_course,
        'github_alumnado_texto': github_links['text'],
        'github_alumnado_html': github_links['html'],
        'calendario_primero': _calendar_period_label(
            _parse_iso_date(config.get('calendario_primero_inicio', '')),
            _parse_iso_date(config.get('calendario_primero_fin', '')),
        ),
        'calendario_segundo': _calendar_period_label(
            _parse_iso_date(config.get('calendario_segundo_inicio', '')),
            _parse_iso_date(config.get('calendario_segundo_fin', '')),
        ),
        'calendario_primero_inicio': _format_date(
            _parse_iso_date(config.get('calendario_primero_inicio', ''))
        ),
        'calendario_primero_fin': _format_date(
            _parse_iso_date(config.get('calendario_primero_fin', ''))
        ),
        'calendario_segundo_inicio': _format_date(
            _parse_iso_date(config.get('calendario_segundo_inicio', ''))
        ),
        'calendario_segundo_fin': _format_date(
            _parse_iso_date(config.get('calendario_segundo_fin', ''))
        ),
    }


def _render_mail_template(template, context):
    """Rellena asunto y cuerpo de una plantilla usando variables conocidas y deja vacío lo ausente."""
    safe_context = {key: value or '' for key, value in context.items()}

    def _replace_placeholders(value):
        """Sustituye solo placeholders simples `{clave}` y deja intactas otras llaves, como las del CSS."""
        text = str(value or '')
        return re.sub(
            r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}',
            lambda match: str(safe_context.get(match.group(1), '')),
            text,
        )

    return {
        'subject': _replace_placeholders(template['subject']),
        'body': _replace_placeholders(template['body']),
        'html_body': _replace_placeholders(template.get('html_body', '')) if template.get('html_body') else '',
    }


def _mail_recipient_options(row):
    """Devuelve las opciones de destinatario válidas disponibles para la empresa seleccionada."""
    options = []
    candidates = [
        ('Correo de contacto', _normalize_text(str(row.get('correo_contacto', '') or '')) or ''),
        ('Correo de empresa', _normalize_text(str(row.get('correo_empresa', '') or '')) or ''),
    ]
    seen = set()
    for label, email in candidates:
        if email and email.upper() != 'N/D' and _valid_email(email) and email not in seen:
            options.append({'label': label, 'value': email})
            seen.add(email)
    return options


def _parse_iso_date(value):
    """Convierte una fecha ISO en `date` y devuelve `None` si el valor no es valido."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _format_date(value):
    """Formatea una fecha como `DD/MM/YYYY` o devuelve cadena vacia si no existe."""
    return value.strftime('%d/%m/%Y') if isinstance(value, date) else ''


def _special_dates_for_year(settings, key, year):
    """Devuelve las fechas especiales configuradas para una clave y año concretos."""
    dates = []
    for raw_value in settings.get(key, []):
        parsed = _parse_iso_date(raw_value) or _parse_display_date(raw_value)
        if isinstance(parsed, date) and parsed.year == year and 1 <= parsed.month <= 6:
            dates.append(parsed)
    return sorted(set(dates))


def _parse_display_date(value):
    """Convierte una fecha `DD/MM/YYYY` a `date` y devuelve `None` si no es valida."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%d/%m/%Y').date()
    except ValueError:
        return None


def _format_interaccion_date(value):
    """Devuelve una fecha de interacción en formato `DD/MM/YYYY` o el texto original si no se puede parsear."""
    parsed = _parse_display_date(value) or _parse_iso_date(value)
    if parsed:
        return _format_date(parsed)
    return _normalize_text(str(value or '')) or ''


def _calendar_period_label(start_date, end_date):
    """Devuelve un resumen legible del periodo configurado para reutilizarlo en plantillas."""
    if start_date and end_date:
        return f"Del {_format_date(start_date)} al {_format_date(end_date)}."
    return ''


def _group_consecutive_dates(values):
    """Agrupa fechas consecutivas y devuelve una lista de tuplas `(inicio, fin)`."""
    if not values:
        return []

    sorted_values = sorted(set(values))
    groups = []
    start_day = sorted_values[0]
    end_day = sorted_values[0]
    for current in sorted_values[1:]:
        if current.toordinal() == end_day.toordinal() + 1:
            end_day = current
            continue
        groups.append((start_day, end_day))
        start_day = current
        end_day = current
    groups.append((start_day, end_day))
    return groups


def _format_date_range_label(start_date, end_date):
    """Devuelve una etiqueta legible para una fecha única o un rango de fechas."""
    if not start_date or not end_date:
        return "Sin periodo configurado"
    if start_date == end_date:
        return _format_date(start_date)
    return f"{_format_date(start_date)} - {_format_date(end_date)}"


def _holiday_range_summary(start_date, end_date):
    """Devuelve una descripción corta de un bloque festivo con rango y número de días."""
    if not start_date or not end_date:
        return "Sin rango"
    total_days = (end_date - start_date).days + 1
    return f"{_format_date_range_label(start_date, end_date)} · {total_days} día(s)"


def _training_hours_label(start_date, end_date, holiday_dates=None, alternancia_dates=None):
    """Calcula las horas de formación del periodo excluyendo fines de semana, festivos y alternancia."""
    if not start_date or not end_date or start_date > end_date:
        return "0 horas"

    excluded_days = set(holiday_dates or []) | set(alternancia_dates or [])
    total_days = 0
    for ordinal in range(start_date.toordinal(), end_date.toordinal() + 1):
        current = date.fromordinal(ordinal)
        if current.weekday() >= 5 or current in excluded_days:
            continue
        total_days += 1
    return f"{total_days * 8} horas"


def _save_calendar_settings_payload(primero_inicio, primero_fin, segundo_inicio, segundo_fin, holiday_dates, alternancia_dates):
    """Persiste toda la configuración de calendarios y días especiales en `app_settings.json`."""
    return save_app_settings({
        'calendario_primero_inicio': primero_inicio.isoformat() if primero_inicio else '',
        'calendario_primero_fin': primero_fin.isoformat() if primero_fin else '',
        'calendario_segundo_inicio': segundo_inicio.isoformat() if segundo_inicio else '',
        'calendario_segundo_fin': segundo_fin.isoformat() if segundo_fin else '',
        'festivos': [holiday.isoformat() for holiday in sorted(set(holiday_dates))],
        'alternancia': [day.isoformat() for day in sorted(set(alternancia_dates))],
    })


def _semester_date_or_none(value, year):
    """Devuelve la fecha si pertenece a enero-junio del año indicado; en otro caso devuelve `None`."""
    if isinstance(value, date) and value.year == year and 1 <= value.month <= 6:
        return value
    return None


def render_semester_calendar(title, primero_inicio, primero_fin, segundo_inicio, segundo_fin, year, holiday_dates=None, alternancia_dates=None):
    """Renderiza un único calendario de enero a junio mostrando 1º, 2º y sus solapes."""
    cal = calendar.Calendar(firstweekday=0)
    month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio']
    weekday_names = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
    holiday_dates = set(holiday_dates or [])
    alternancia_dates = set(alternancia_dates or [])
    months_html = []
    for month_index, month in enumerate(range(1, 7)):
        weeks_html = []
        for week in cal.monthdayscalendar(year, month):
            cells = []
            for day_num in week:
                if day_num == 0:
                    cells.append('<td class="sem-empty"></td>')
                    continue

                current = date(year, month, day_num)
                classes = ['sem-day']
                is_weekend = current.weekday() >= 5
                is_holiday = current in holiday_dates
                is_alternancia = current in alternancia_dates
                in_primero = bool(primero_inicio and primero_fin and primero_inicio <= current <= primero_fin)
                in_segundo = bool(segundo_inicio and segundo_fin and segundo_inicio <= current <= segundo_fin)
                if not is_weekend and not is_holiday and not is_alternancia:
                    if in_primero and in_segundo:
                        classes.append('sem-overlap')
                    elif in_primero:
                        classes.append('sem-first')
                    elif in_segundo:
                        classes.append('sem-second')
                if is_holiday:
                    classes.append('sem-holiday')
                elif is_alternancia:
                    classes.append('sem-alternancia')
                if is_weekend:
                    classes.append('sem-weekend')

                cells.append(f'<td class="{" ".join(classes)}">{day_num}</td>')
            weeks_html.append(f"<tr>{''.join(cells)}</tr>")

        weekday_header = ''.join(f'<th>{weekday}</th>' for weekday in weekday_names)
        months_html.append(textwrap.dedent(f"""
            <div class="sem-month">
                <div class="sem-month-title">{month_names[month_index]}</div>
                <table class="sem-table">
                    <thead><tr>{weekday_header}</tr></thead>
                    <tbody>{''.join(weeks_html)}</tbody>
                </table>
            </div>
        """).strip())

    primero_label = _calendar_period_label(primero_inicio, primero_fin) or 'Sin periodo'
    segundo_label = _calendar_period_label(segundo_inicio, segundo_fin) or 'Sin periodo'
    summary = f"1º: {primero_label} · 2º: {segundo_label}"
    calendar_html = textwrap.dedent(f"""
        <style>
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: transparent;
        }}
        .sem-wrap {{
            margin-top: 4px;
            padding: 12px;
            border: 1px solid rgba(128,128,128,.14);
            border-radius: 12px;
            background: rgba(128,128,128,.03);
        }}
        .sem-head {{
            margin-bottom: 8px;
        }}
        .sem-title {{
            font-size: 1rem;
            font-weight: 700;
        }}
        .sem-summary {{
            font-size: .88rem;
            opacity: .72;
            margin-top: 2px;
        }}
        .sem-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(220px, 1fr));
            gap: 10px;
        }}
        @media(max-width:900px) {{
            .sem-grid {{
                grid-template-columns: repeat(2, minmax(220px, 1fr));
            }}
        }}
        @media(max-width:640px) {{
            .sem-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .sem-month {{
            background: white;
            border: 1px solid rgba(128,128,128,.12);
            border-radius: 10px;
            padding: 8px;
        }}
        .sem-month-title {{
            font-size: .92rem;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .sem-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 2px;
            table-layout: fixed;
        }}
        .sem-table th {{
            font-size: .7rem;
            opacity: .55;
            padding-bottom: 4px;
        }}
        .sem-table td {{
            text-align: center;
            font-size: .78rem;
            padding: 4px 0;
            border-radius: 6px;
        }}
        .sem-empty {{
            background: transparent;
        }}
        .sem-day {{
            background: rgba(128,128,128,.05);
        }}
        .sem-weekend {{
            background: rgba(128,128,128,.025);
            color: rgba(34,49,63,.48);
        }}
        .sem-in-range {{
            background: rgba(26,122,191,.14);
            color: #155f96;
            font-weight: 600;
        }}
        .sem-first {{
            background: rgba(26,122,191,.14);
            color: #155f96;
            font-weight: 700;
        }}
        .sem-second {{
            background: rgba(23,148,104,.16);
            color: #0d6a48;
            font-weight: 700;
        }}
        .sem-overlap {{
            background: linear-gradient(135deg, rgba(26,122,191,.18) 0 50%, rgba(23,148,104,.20) 50% 100%);
            color: #14354f;
            font-weight: 800;
        }}
        .sem-holiday {{
            background: rgba(209, 94, 24, .18);
            color: #8d3d0f;
            font-weight: 700;
        }}
        .sem-alternancia {{
            background: rgba(166, 38, 164, .20);
            color: #7b136f;
            font-weight: 700;
        }}
        .sem-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }}
        .sem-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: .78rem;
            background: white;
            border: 1px solid rgba(128,128,128,.12);
        }}
        .sem-pill::before {{
            content: "";
            width: 10px;
            height: 10px;
            border-radius: 999px;
            display: inline-block;
        }}
        .sem-pill-first::before {{
            background: rgba(26,122,191,.7);
        }}
        .sem-pill-second::before {{
            background: rgba(23,148,104,.78);
        }}
        .sem-pill-overlap::before {{
            background: linear-gradient(135deg, rgba(26,122,191,.9) 0 50%, rgba(23,148,104,.9) 50% 100%);
        }}
        .sem-pill-holiday::before {{
            background: rgba(209,94,24,.8);
        }}
        .sem-pill-alternancia::before {{
            background: rgba(166,38,164,1);
        }}
        </style>
        <div class="sem-wrap">
            <div class="sem-head">
                <div class="sem-title">{html.escape(title)} · {year}</div>
                <div class="sem-summary">{html.escape(summary)}</div>
            </div>
            <div class="sem-grid">
                {''.join(months_html)}
            </div>
            <div class="sem-legend">
                <span class="sem-pill sem-pill-second">2º</span>
                <span class="sem-pill sem-pill-first">1º</span>
                <span class="sem-pill sem-pill-overlap">2º + 1º</span>
                <span class="sem-pill sem-pill-holiday">Festivo</span>
                <span class="sem-pill sem-pill-alternancia">Alternancia</span>
            </div>
        </div>
    """).strip()
    components.html(calendar_html, height=570, scrolling=False)


def render_calendar_panel(title, primero_inicio, primero_fin, segundo_inicio, segundo_fin, year, holiday_dates, alternancia_dates):
    """Renderiza un bloque autocontenido con un único calendario y el resumen de ambos periodos."""
    col_info_1, col_info_2 = st.columns(2)
    with col_info_1:
        segundo_period = _calendar_period_label(segundo_inicio, segundo_fin) or 'Sin periodo configurado.'
        segundo_hours = _training_hours_label(segundo_inicio, segundo_fin, holiday_dates, alternancia_dates)
        st.markdown(
            f'<div style="display:inline-block;background:rgba(23,148,104,.16);color:#0d6a48;'
            f'padding:6px 10px;border-radius:10px;font-size:.88rem;font-weight:600;">'
            f'<strong>2º:</strong> {html.escape(segundo_period)} · '
            f'<span style="display:inline-block;background:rgba(255,255,255,.72);padding:1px 8px;'
            f'border-radius:999px;font-weight:800;">{html.escape(segundo_hours)}</span>.'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_info_2:
        primero_period = _calendar_period_label(primero_inicio, primero_fin) or 'Sin periodo configurado.'
        primero_hours = _training_hours_label(primero_inicio, primero_fin, holiday_dates, alternancia_dates)
        st.markdown(
            f'<div style="display:inline-block;background:rgba(26,122,191,.14);color:#155f96;'
            f'padding:6px 10px;border-radius:10px;font-size:.88rem;font-weight:600;">'
            f'<strong>1º:</strong> {html.escape(primero_period)} · '
            f'<span style="display:inline-block;background:rgba(255,255,255,.72);padding:1px 8px;'
            f'border-radius:999px;font-weight:800;">{html.escape(primero_hours)}</span>.'
            f'</div>',
            unsafe_allow_html=True,
        )
    render_semester_calendar(
        title,
        primero_inicio,
        primero_fin,
        segundo_inicio,
        segundo_fin,
        year,
        holiday_dates=holiday_dates,
        alternancia_dates=alternancia_dates,
    )


def _sorted_interacciones(df_interacciones):
    """Devuelve las interacciones ordenadas de mas reciente a mas antigua usando la fecha de contacto."""
    if df_interacciones.empty:
        return df_interacciones

    return (
        df_interacciones
        .assign(
            _sort_fecha=lambda df: df['fecha'].map(
                lambda value: _parse_iso_date(value) or _parse_display_date(value) or date.min
            )
        )
        .sort_values(by='_sort_fecha', ascending=False, kind='stable')
        .drop(columns=['_sort_fecha'])
    )


def render_interacciones_timeline(df_interacciones, estado_empresa=''):
    """Renderiza una lista de interacciones en formato timeline con scroll vertical."""
    if df_interacciones.empty:
        st.caption("Sin interacciones registradas.")
        return

    sorted_int = _sorted_interacciones(df_interacciones)
    estado = html.escape(str(estado_empresa or '')) or 'Sin estado'
    st.markdown(textwrap.dedent("""
        <style>
        .it-card {
            border: 1px solid rgba(26, 122, 191, 0.14);
            border-radius: 14px;
            padding: 14px 16px;
            background: linear-gradient(180deg, rgba(26, 122, 191, 0.04) 0%, rgba(255, 255, 255, 0.98) 100%);
            margin-bottom: 12px;
        }
        .it-row {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            flex-wrap: wrap;
            margin-bottom: 8px;
        }
        .it-row:last-child {
            margin-bottom: 0;
        }
        .it-label {
            width: 88px;
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .03em;
            text-transform: uppercase;
            color: rgba(18, 74, 115, 0.72);
        }
        .it-value {
            flex: 1;
            font-size: .95rem;
            color: #22313f;
        }
        .it-strong {
            font-weight: 700;
            color: #124a73;
        }
        .it-desc {
            white-space: pre-wrap;
        }
        .it-state {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(26, 122, 191, 0.12);
            color: #124a73;
            font-size: .82rem;
            font-weight: 700;
        }
        </style>
    """).strip(), unsafe_allow_html=True)

    with st.container(height=420):
        for _, row in sorted_int.iterrows():
            orig_idx = int(row['index']) if 'index' in row else int(row.name)
            fecha = html.escape(_format_interaccion_date(row.get('fecha', '')) or 'Sin fecha')
            tipo = html.escape(str(row.get('tipo', '') or '')) or 'Interacción'
            profesor = html.escape(str(row.get('profesor', '') or '')) or 'Sin profesor'
            descripcion = html.escape(str(row.get('descripcion', '') or '')) or 'Sin descripción.'
            col_card, col_actions = st.columns([12, 1])
            with col_card:
                st.markdown(textwrap.dedent(f"""
                    <div class="it-card">
                        <div class="it-row">
                            <div class="it-label">Fecha</div>
                            <div class="it-value">{fecha}</div>
                        </div>
                        <div class="it-row">
                            <div class="it-label">Tipo</div>
                            <div class="it-value it-strong">{tipo}</div>
                        </div>
                        <div class="it-row">
                            <div class="it-label">Profesor</div>
                            <div class="it-value">{profesor}</div>
                        </div>
                        <div class="it-row">
                            <div class="it-label">Descripción</div>
                            <div class="it-value it-desc">{descripcion}</div>
                        </div>
                        <div class="it-row">
                            <div class="it-label">Estado</div>
                            <div class="it-value"><span class="it-state">{estado}</span></div>
                        </div>
                    </div>
                """).strip(), unsafe_allow_html=True)
            with col_actions:
                if st.button("✏️", key=f"edit_int_{orig_idx}", help="Editar interacción", use_container_width=True):
                    st.session_state._edit_interaccion_idx = orig_idx
                    st.session_state._edit_interaccion_empresa_id = str(row.get('id_empresa', '') or '')
                    st.session_state._edit_interaccion_estado = _normalize_text(estado_empresa) or ''
                    dialog_editar_interaccion()
                if st.button("🗑️", key=f"delete_int_{orig_idx}", help="Eliminar interacción", use_container_width=True):
                    st.session_state._delete_interaccion_idx = orig_idx
                    st.session_state._delete_interaccion_nombre = html.escape(str(row.get('tipo', '') or 'Interacción'))
                    dialog_eliminar_interaccion()


def clipboard_button(label, text, key, help_text=None, html_text=None):
    """Renderiza un botón HTML que copia texto plano o HTML enriquecido al portapapeles."""
    payload = json.dumps(text)
    html_payload = json.dumps(html_text) if html_text is not None else 'null'
    button_id = re.sub(r'[^a-zA-Z0-9_-]', '_', key)
    help_attr = f'title="{html.escape(help_text)}"' if help_text else ''
    button_label = html.escape(label)
    components.html(f"""
        <style>
            .copy-btn-{button_id} {{
                background: #1a7abf;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 14px;
                cursor: pointer;
                width: 100%;
            }}
            .copy-btn-{button_id}:hover {{
                background: #155f96;
            }}
            .copy-msg-{button_id} {{
                margin-top: 4px;
                font-size: 12px;
                color: #21a656;
                min-height: 16px;
            }}
        </style>
        <button class="copy-btn-{button_id}" {help_attr} onclick="copy_{button_id}()">
            {button_label}
        </button>
        <div class="copy-msg-{button_id}" id="copy-msg-{button_id}"></div>
        <script>
        async function copy_{button_id}() {{
            const text = {payload};
            const htmlText = {html_payload};
            try {{
                if (htmlText && window.ClipboardItem && navigator.clipboard.write) {{
                    const item = new ClipboardItem({{
                        'text/plain': new Blob([text], {{ type: 'text/plain' }}),
                        'text/html': new Blob([htmlText], {{ type: 'text/html' }})
                    }});
                    await navigator.clipboard.write([item]);
                }} else {{
                    await navigator.clipboard.writeText(text);
                }}
            }} catch (e) {{
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
            }}
            const msg = document.getElementById('copy-msg-{button_id}');
            msg.textContent = '✓ Copiado al portapapeles';
            setTimeout(() => msg.textContent = '', 3000);
        }}
        </script>
    """, height=72)


def interaccion_form(key, current_estado, defaults=None):
    """Renderiza el formulario de una interacción y devuelve los datos saneados al enviarlo."""
    defaults = defaults or {}
    fecha_default = _parse_display_date(defaults.get('fecha', '')) or _parse_iso_date(defaults.get('fecha', '')) or date.today()
    tipo_default = _normalize_text(str(defaults.get('tipo', '') or '')) or ''
    profesor_default = _normalize_text(str(defaults.get('profesor', '') or '')) or ''
    descripcion_default = _normalize_text(str(defaults.get('descripcion', '') or '')) or ''
    estado_default = _normalize_text(str(defaults.get('estado_empresa', current_estado) or '')) or current_estado

    with st.form(key):
        c1, c2 = st.columns(2)
        with c1:
            tipo_c = st.selectbox("Tipo *", lookups['tipo_interaccion'], index=_idx(lookups['tipo_interaccion'], tipo_default))
            fecha_c = st.date_input("Fecha de la interacción *", value=fecha_default, format="DD/MM/YYYY")
            st.caption(f"Estado actual: **{current_estado or '—'}**")
            estado_emp = st.selectbox(
                "Actualizar estado a",
                lookups['estado_empresa'],
                index=_idx(lookups['estado_empresa'], estado_default),
            )
        with c2:
            profesor_c = st.selectbox("Profesor", [''] + lookups['profesor'], index=_idx([''] + lookups['profesor'], profesor_default))
            desc_c = st.text_area("Descripción", value=descripcion_default, height=80)

        if st.form_submit_button("Guardar"):
            if not tipo_c or not fecha_c:
                st.error("Los campos Tipo y Fecha de la interacción son obligatorios.")
                return None

            return {
                'tipo': _normalize_text(tipo_c) or '',
                'descripcion': _normalize_text(desc_c) or '',
                'fecha': fecha_c.strftime("%d/%m/%Y"),
                'profesor': _normalize_text(profesor_c) or '',
                'estado_empresa': _normalize_text(estado_emp) or current_estado,
            }

    return None


def empresa_form(key, defaults=None, lock_estado=False):
    """Renderiza el formulario de empresa y devuelve datos saneados, con `nombre` en mayúsculas.
    Si lock_estado=True el campo Estado se muestra como solo lectura.
    """
    _empty = {col: '' for col in st.session_state.df.columns} | {'estado': 'Empresa nueva'}
    d = defaults or _empty
    with st.form(key):
        st.markdown("""
        <style>
        .ef-form-section {
            font-size: .76rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
            opacity: .68;
            padding-bottom: 6px;
            margin: 8px 0 10px 0;
            border-bottom: 1px solid rgba(128,128,128,.1);
        }
        .ef-form-head {
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.15;
            margin: 0 0 8px 0;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(
            f'<div class="ef-form-head">{html.escape(str(d.get("nombre", "") or "")) or "Nueva empresa"}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="ef-form-section">Situación</div>', unsafe_allow_html=True)
        c_sit_1, c_sit_2 = st.columns(2)
        with c_sit_1:
            if lock_estado:
                st.text_input("Estado de la empresa", value=d.get('estado', ''), disabled=True)
                estado = d.get('estado', '')
            else:
                estado = st.selectbox("Estado de la empresa", lookups['estado_empresa'],
                                      index=_idx(lookups['estado_empresa'], d.get('estado')))
            localidad = st.selectbox("Localidad", [''] + lookups['localizacion'],
                                     index=_idx([''] + lookups['localizacion'], d.get('localidad')))
        with c_sit_2:
            regimen = st.selectbox("Régimen", [''] + lookups['regimen'],
                                   index=_idx([''] + lookups['regimen'], d.get('regimen')))
            profesor = st.selectbox("Profesor", [''] + lookups['profesor'],
                                    index=_idx([''] + lookups['profesor'], d.get('profesor')))

        st.markdown('<div class="ef-form-section">Datos generales de la empresa</div>', unsafe_allow_html=True)
        c_emp_1, c_emp_2 = st.columns(2)
        with c_emp_1:
            nombre        = st.text_input("Nombre empresa *", value=d.get('nombre', ''))
            web           = st.text_input("Web", value=d.get('web', ''))
            correo_emp    = st.text_input("Correo empresa", value=d.get('correo_empresa', ''))
        with c_emp_2:
            tfno_emp      = st.text_input("Teléfono empresa", value=d.get('tfno_empresa', ''))
            ext_tfno      = st.text_input("Extensión", value=d.get('extension_tfno', ''))

        st.markdown('<div class="ef-form-section">Persona de contacto</div>', unsafe_allow_html=True)
        c_con_1, c_con_2 = st.columns(2)
        with c_con_1:
            contacto      = st.text_input("Contacto", value=d.get('contacto', ''))
            correo_con    = st.text_input("Correo contacto", value=d.get('correo_contacto', ''))
        with c_con_2:
            tfno_con      = st.text_input("Teléfono contacto", value=d.get('tfno_contacto', ''))

        st.markdown('<div class="ef-form-section">Notas</div>', unsafe_allow_html=True)
        c_not_1, c_not_2 = st.columns(2)
        with c_not_1:
            tecnologias   = st.text_area("Tecnologías", value=d.get('tecnologias', ''), height=80)
            descripcion   = st.text_area("Descripción", value=d.get('descripcion', ''), height=100)
        with c_not_2:
            observaciones = st.text_area("Observaciones", value=d.get('observaciones', ''), height=188)

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

            if new_field_errors:
                if 'nombre' in new_field_errors:
                    st.error("⚠ El nombre es obligatorio.")
                if 'correo_emp' in new_field_errors:
                    st.error("⚠ Correo empresa: formato inválido. Ejemplo: nombre@correo.com (o escribe N/D).")
                if 'correo_con' in new_field_errors:
                    st.error("⚠ Correo contacto: formato inválido. Ejemplo: nombre@correo.com.")
                if 'web' in new_field_errors:
                    st.error("⚠ Web: formato inválido. Ejemplo: https://empresa.com.")
                if 'tfno_emp' in new_field_errors:
                    st.error("⚠ Teléfono empresa: formato inválido. Ejemplo: 612345678 o +34612345678.")
                if 'tfno_con' in new_field_errors:
                    st.error("⚠ Teléfono contacto: formato inválido. Ejemplo: 612345678 o +34612345678.")
                return None

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
    """Muestra los datos de una empresa como ficha CRM: situación destacada, grid de cards y notas."""

    def _v(key):
        """Devuelve el valor del campo escapado para HTML, o cadena vacía."""
        return html.escape(str(row.get(key, '') or ''))

    def _fld(label, value):
        """Genera el HTML de un campo etiqueta + valor dentro de una card."""
        val_html = (f'<div class="ef-val">{value}</div>'
                    if value else
                    '<div class="ef-val ef-empty">—</div>')
        return f'<div class="ef-field"><div class="ef-lbl">{label}</div>{val_html}</div>'

    # Valores
    nombre    = _v('nombre')
    estado    = _v('estado')
    localidad = _v('localidad')
    regimen   = _v('regimen')
    profesor  = _v('profesor')

    web_raw   = str(row.get('web', '') or '')
    web_esc   = html.escape(web_raw)
    web_html  = f'<a class="ef-link" href="{web_esc}" target="_blank">{web_esc}</a>' if web_raw else ''

    correo_emp = _v('correo_empresa')
    tfno_emp   = _v('tfno_empresa')
    ext_tfno   = _v('extension_tfno')
    tfno_emp_display = (f'{tfno_emp}&thinsp;<span class="ef-ext">ext.&nbsp;{ext_tfno}</span>'
                        if tfno_emp and ext_tfno else tfno_emp)

    contacto   = _v('contacto')
    correo_con = _v('correo_contacto')
    tfno_con   = _v('tfno_contacto')

    tecnologias   = _v('tecnologias')
    descripcion   = _v('descripcion')
    observaciones = _v('observaciones')

    # Notas: solo campos con valor
    notas_html = ''.join([
        _fld('Tecnologías', tecnologias) if tecnologias else '',
        _fld('Descripción', descripcion) if descripcion else '',
        _fld('Observaciones', observaciones) if observaciones else '',
    ]) or '<div class="ef-val ef-empty">Sin notas registradas.</div>'

    def _sit_item(label, value):
        val = value or '<span class="ef-empty">—</span>'
        return f'<div class="ef-sit-item"><div class="ef-lbl">{label}</div><div class="ef-sit-val">{val}</div></div>'

    st.markdown(f"""
<style>
.ef-wrap {{ margin-top:2px; }}
.ef-head {{ margin-bottom:8px; }}
.ef-name {{
    font-size:1.08rem; font-weight:700; line-height:1.15;
    margin:0;
}}

/* ── Situación ── */
.ef-situacion {{
    display:flex; flex-wrap:wrap; gap:28px;
    background:rgba(99,102,241,.07);
    border-left:4px solid rgba(99,102,241,.4);
    border-radius:0 10px 10px 0;
    padding:10px 16px;
    margin-bottom:10px;
}}
.ef-sit-item .ef-lbl {{
    font-size:.68rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.08em; opacity:.7; margin-bottom:3px;
}}
.ef-sit-val {{ font-size:1rem; font-weight:600; }}

/* ── Grid 2 col ── */
.ef-grid {{
    display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;
}}
@media(max-width:768px){{ .ef-grid{{ grid-template-columns:1fr; }} }}

/* ── Cards ── */
.ef-card {{
    background:rgba(128,128,128,.04);
    border:1px solid rgba(128,128,128,.12);
    border-radius:10px;
    padding:10px 14px;
}}
.ef-card-title {{
    font-size:.76rem; font-weight:800; text-transform:uppercase;
    letter-spacing:.08em; opacity:.68;
    padding-bottom:6px; margin-bottom:8px;
    border-bottom:1px solid rgba(128,128,128,.1);
}}

/* ── Notas ── */
.ef-notas {{
    background:rgba(128,128,128,.04);
    border:1px solid rgba(128,128,128,.12);
    border-radius:10px;
    padding:10px 14px;
}}
.ef-notas .ef-field {{ margin-bottom:10px; }}
.ef-notas .ef-field:last-child {{ margin-bottom:0; }}

/* ── Campos ── */
.ef-field {{ margin-bottom:7px; }}
.ef-field:last-child {{ margin-bottom:0; }}
.ef-lbl {{ font-size:.78rem; opacity:.82; margin-bottom:2px; }}
.ef-val {{ font-size:.9rem; font-weight:500; line-height:1.45; word-break:break-word; }}
.ef-empty {{ opacity:.28; font-style:italic; font-weight:400; }}
.ef-ext {{ font-size:.8em; opacity:.55; }}
.ef-link {{ color:inherit; text-decoration:underline; text-underline-offset:2px; }}
</style>

<div class="ef-wrap">

  <div class="ef-head">
    <div class="ef-name">{nombre or '<span class="ef-empty">Empresa sin nombre</span>'}</div>
  </div>

  <div class="ef-situacion">
    {_sit_item('Estado',    estado)}
    {_sit_item('Localidad', localidad)}
    {_sit_item('Régimen',   regimen)}
    {_sit_item('Profesor',  profesor)}
  </div>

  <div class="ef-grid">
    <div class="ef-card">
      <div class="ef-card-title">Datos generales de la empresa</div>
      {_fld('Web',              web_html)}
      {_fld('Correo general',   correo_emp)}
      {_fld('Teléfono general', tfno_emp_display)}
    </div>
    <div class="ef-card">
      <div class="ef-card-title">Persona de contacto</div>
      {_fld('Nombre',   contacto)}
      {_fld('Correo',   correo_con)}
      {_fld('Teléfono', tfno_con)}
    </div>
  </div>

  <div class="ef-notas">
    <div class="ef-card-title">Notas</div>
    {notas_html}
  </div>

</div>
""", unsafe_allow_html=True)


@st.dialog("Nueva empresa", width="large")
def dialog_nueva_empresa():
    """Abre un diálogo modal con el formulario de alta de empresa."""
    result = empresa_form("form_nueva")
    if result:
        st.session_state._dialog_result = result
        st.session_state._dialog_action = 'nueva'
        st.rerun()


@st.dialog("Editar empresa", width="large")
def dialog_editar_empresa():
    """Abre un diálogo modal con el formulario de edición de empresa, con datos precargados."""
    result = empresa_form(
        "form_editar",
        defaults=st.session_state.get('_edit_defaults'),
        lock_estado=True,
    )
    if result:
        st.session_state._dialog_result = result
        st.session_state._dialog_action = 'editar'
        st.rerun()


@st.dialog("Eliminar empresa", width="small")
def dialog_eliminar_empresa():
    """Pide confirmación antes de eliminar la empresa seleccionada."""
    empresa_id = st.session_state.get('_delete_empresa_id')
    if not empresa_id:
        st.error("La empresa seleccionada ya no está disponible.")
        return

    matching = st.session_state.df[st.session_state.df['id_empresa'] == empresa_id]
    if matching.empty:
        st.error("La empresa seleccionada ya no está disponible.")
        return

    row = matching.iloc[0]
    nombre = html.escape(str(row.get('nombre', '') or 'Empresa'))
    st.warning(f"¿Eliminar la empresa **{nombre}**?")
    st.caption("Esta acción crea un backup automático antes de guardar.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirmar", type="primary", use_container_width=True):
            st.session_state.df = st.session_state.df[st.session_state.df['id_empresa'] != empresa_id].reset_index(drop=True)
            st.session_state.pop('_delete_empresa_id', None)
            st.session_state.pop('_sel_id', None)
            try:
                save_data(st.session_state.df)
                st.toast("Empresa eliminada.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo eliminar: {e}")
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('_delete_empresa_id', None)
            st.rerun()


@st.dialog("Eliminar interacción", width="small")
def dialog_eliminar_interaccion():
    """Pide confirmación antes de eliminar una interacción del histórico."""
    orig_idx = st.session_state.get('_delete_interaccion_idx')
    if orig_idx is None or orig_idx not in st.session_state.interacciones.index:
        st.error("La interacción seleccionada ya no está disponible.")
        return

    row = st.session_state.interacciones.loc[orig_idx]
    tipo = html.escape(str(row.get('tipo', '') or 'Interacción'))
    fecha = html.escape(_format_interaccion_date(row.get('fecha', '')) or 'Sin fecha')
    st.warning(f"¿Eliminar la interacción **{tipo}** del **{fecha}**?")
    st.caption("Esta acción crea un backup automático antes de guardar.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirmar", type="primary", use_container_width=True):
            st.session_state.interacciones = (
                st.session_state.interacciones
                .drop(index=orig_idx)
                .reset_index(drop=True)
            )
            st.session_state.pop('_delete_interaccion_idx', None)
            try:
                save_interacciones(st.session_state.interacciones)
                st.toast("Interacción eliminada.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo eliminar: {e}")
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('_delete_interaccion_idx', None)
            st.rerun()


@st.dialog("Editar interacción", width="large")
def dialog_editar_interaccion():
    """Abre un diálogo modal para editar una interacción existente y su estado asociado."""
    orig_idx = st.session_state.get('_edit_interaccion_idx')
    empresa_id = st.session_state.get('_edit_interaccion_empresa_id')
    current_estado = st.session_state.get('_edit_interaccion_estado', '')

    if orig_idx is None or orig_idx not in st.session_state.interacciones.index:
        st.error("La interacción seleccionada ya no está disponible.")
        return

    row = st.session_state.interacciones.loc[orig_idx].to_dict()
    result = interaccion_form(
        "form_edit_interaccion",
        current_estado=current_estado,
        defaults={**row, 'estado_empresa': current_estado},
    )
    if result:
        for key in ('tipo', 'descripcion', 'fecha', 'profesor'):
            st.session_state.interacciones.at[orig_idx, key] = result[key]

        idx_emp = st.session_state.df.index[st.session_state.df['id_empresa'] == empresa_id].tolist()
        if idx_emp:
            st.session_state.df.at[idx_emp[0], 'estado'] = result['estado_empresa']

        try:
            save_interacciones(st.session_state.interacciones)
            if idx_emp:
                save_data(st.session_state.df)
            st.session_state.pop('_edit_interaccion_idx', None)
            st.session_state.pop('_edit_interaccion_empresa_id', None)
            st.session_state.pop('_edit_interaccion_estado', None)
            st.toast("Interacción actualizada.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")


@st.dialog("Añadir interacción", width="large")
def dialog_nueva_interaccion():
    """Abre un diálogo modal para crear una interacción nueva en la empresa seleccionada."""
    empresa_id = st.session_state.get('_int_empresa_id')
    current_estado = st.session_state.get('_int_empresa_estado', '')
    if not empresa_id:
        st.error("No se pudo abrir la interacción.")
        return

    result = interaccion_form("form_add_interaccion", current_estado=current_estado)
    if result:
        new_row = pd.DataFrame([{
            'id_empresa': empresa_id,
            'tipo': result['tipo'],
            'descripcion': result['descripcion'],
            'fecha': result['fecha'],
            'profesor': result['profesor'],
        }])
        st.session_state.interacciones = pd.concat(
            [st.session_state.interacciones, new_row], ignore_index=True
        )
        idx_emp = st.session_state.df.index[st.session_state.df['id_empresa'] == empresa_id].tolist()
        if idx_emp:
            st.session_state.df.at[idx_emp[0], 'estado'] = result['estado_empresa']
        try:
            save_interacciones(st.session_state.interacciones)
            save_data(st.session_state.df)
            st.toast("Interacción añadida.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")


@st.dialog("Añadir asignación", width="large")
def dialog_nueva_asignacion():
    """Abre un diálogo modal para añadir alumnos a la empresa seleccionada con el año actual bloqueado."""
    empresa_id = st.session_state.get('_alu_empresa_id')
    if not empresa_id:
        st.error("No se pudo abrir la asignación de alumnos.")
        return

    current_year = str(date.today().year)
    with st.form("form_add_alumnos"):
        c1, c2, c3 = st.columns(3)
        with c1:
            num_alu = st.number_input("Número de alumnos", min_value=1, step=1, value=1)
        with c2:
            grupo_alu = st.selectbox("Grupo", lookups['grupo_estudiantes'])
        with c3:
            st.text_input("Año", value=current_year, disabled=True)

        if st.form_submit_button("Guardar", type="primary"):
            if _has_duplicate_alumno_asignacion(st.session_state.num_estudiantes, empresa_id, grupo_alu, current_year):
                st.error("No puede existir otra asignación con la misma combinación de grupo y año para esta empresa.")
                return
            es_primera = st.session_state.num_estudiantes[
                st.session_state.num_estudiantes['id_empresa'] == empresa_id
            ].empty
            new_row = pd.DataFrame([{
                'id_empresa': empresa_id,
                'num_alumnos': str(int(num_alu)),
                'grupo': grupo_alu,
                'anio': current_year,
            }])
            st.session_state.num_estudiantes = pd.concat(
                [st.session_state.num_estudiantes, new_row], ignore_index=True
            )
            idx_emp = st.session_state.df.index[st.session_state.df['id_empresa'] == empresa_id].tolist()
            if idx_emp:
                st.session_state.df.at[idx_emp[0], 'estado'] = 'Colabora'
            try:
                save_num_estudiantes(st.session_state.num_estudiantes)
                save_data(st.session_state.df)
                if es_primera:
                    st.toast("Asignación añadida. La empresa pasa al estado Colabora.")
                else:
                    st.toast("Asignación añadida.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")


@st.dialog("Editar asignación", width="large")
def dialog_editar_asignacion():
    """Abre un diálogo modal para editar una asignación de alumnos manteniendo el año bloqueado."""
    orig_idx = st.session_state.get('_edit_alu_idx')
    if orig_idx is None or orig_idx not in st.session_state.num_estudiantes.index:
        st.error("La asignación seleccionada ya no está disponible.")
        return

    row = st.session_state.num_estudiantes.loc[orig_idx]
    current_year = str(row.get('anio', '') or date.today().year)

    with st.form("form_edit_alumnos"):
        c1, c2, c3 = st.columns(3)
        with c1:
            num_alu = st.number_input(
                "Número de alumnos",
                min_value=1,
                step=1,
                value=int(pd.to_numeric(row.get('num_alumnos', 1), errors='coerce') or 1),
            )
        with c2:
            grupo_alu = st.selectbox(
                "Grupo",
                lookups['grupo_estudiantes'],
                index=_idx(lookups['grupo_estudiantes'], row.get('grupo', '')),
            )
        with c3:
            st.text_input("Año", value=current_year, disabled=True)

        if st.form_submit_button("Guardar cambios", type="primary"):
            empresa_id = str(row.get('id_empresa', '') or '')
            if _has_duplicate_alumno_asignacion(st.session_state.num_estudiantes, empresa_id, grupo_alu, current_year, exclude_idx=orig_idx):
                st.error("No puede existir otra asignación con la misma combinación de grupo y año para esta empresa.")
                return
            st.session_state.num_estudiantes.at[orig_idx, 'num_alumnos'] = str(int(num_alu))
            st.session_state.num_estudiantes.at[orig_idx, 'grupo'] = grupo_alu
            st.session_state.num_estudiantes.at[orig_idx, 'anio'] = current_year
            try:
                save_num_estudiantes(st.session_state.num_estudiantes)
                st.toast("Asignación actualizada.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")


@st.dialog("Eliminar asignación", width="small")
def dialog_eliminar_asignacion():
    """Pide confirmación antes de eliminar una asignación de alumnos."""
    orig_idx = st.session_state.get('_delete_alu_idx')
    empresa_id = st.session_state.get('_delete_alu_empresa_id')
    if orig_idx is None or orig_idx not in st.session_state.num_estudiantes.index:
        st.error("La asignación seleccionada ya no está disponible.")
        return

    row = st.session_state.num_estudiantes.loc[orig_idx]
    grupo = html.escape(str(row.get('grupo', '') or ''))
    anio = html.escape(str(row.get('anio', '') or date.today().year))
    st.warning(f"¿Eliminar la asignación del grupo **{grupo}** del año **{anio}**?")
    st.caption("Esta acción crea un backup automático antes de guardar.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirmar", type="primary", use_container_width=True):
            st.session_state.num_estudiantes = (
                st.session_state.num_estudiantes
                .drop(index=orig_idx)
                .reset_index(drop=True)
            )
            quedan = st.session_state.num_estudiantes[
                st.session_state.num_estudiantes['id_empresa'] == empresa_id
            ]
            if quedan.empty:
                idx_emp = st.session_state.df.index[st.session_state.df['id_empresa'] == empresa_id].tolist()
                if idx_emp:
                    st.session_state.df.at[idx_emp[0], 'estado'] = 'Pendiente de respuesta'
            st.session_state.pop('_delete_alu_idx', None)
            st.session_state.pop('_delete_alu_empresa_id', None)
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
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('_delete_alu_idx', None)
            st.session_state.pop('_delete_alu_empresa_id', None)
            st.rerun()


@st.dialog("Añadir enlace GitHub", width="large")
def dialog_nuevo_github_alumno():
    """Abre un diálogo modal para añadir un enlace GitHub del alumnado con el curso actual bloqueado."""
    current_course = _current_academic_course_label()

    with st.form("form_add_github_alumno"):
        c1, c2, c3 = st.columns(3)
        with c1:
            enlace = st.text_input("Enlace GitHub", placeholder="https://github.com/usuario")
        with c2:
            grupo = st.selectbox("Grupo", GITHUB_GRUPOS)
        with c3:
            st.text_input("Curso académico", value=current_course, disabled=True)

        if st.form_submit_button("Guardar", type="primary"):
            normalized = {
                'enlace': _normalize_text(enlace) or '',
                'grupo': _normalize_text(grupo) or '',
                'curso_academico': current_course,
            }
            if not normalized['enlace']:
                st.error("⚠ El enlace GitHub es obligatorio.")
                return
            if not _valid_github_url(normalized['enlace']):
                st.error("⚠ El enlace debe ser un perfil válido de GitHub. Ejemplo: https://github.com/usuario.")
                return
            duplicate = st.session_state.github_alumnado[
                (st.session_state.github_alumnado['enlace'] == normalized['enlace'])
                & (st.session_state.github_alumnado['curso_academico'] == normalized['curso_academico'])
            ]
            if not duplicate.empty:
                st.error("⚠ Ya existe ese enlace GitHub para el curso académico actual.")
                return

            st.session_state.github_alumnado = pd.concat(
                [st.session_state.github_alumnado, pd.DataFrame([normalized])],
                ignore_index=True,
            )
            try:
                save_github_alumnado(st.session_state.github_alumnado)
                st.toast("Enlace GitHub añadido.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")


@st.dialog("Editar enlace GitHub", width="large")
def dialog_editar_github_alumno():
    """Abre un diálogo modal para editar un enlace GitHub del alumnado manteniendo el curso bloqueado."""
    orig_idx = st.session_state.get('_edit_github_idx')
    if orig_idx is None or orig_idx not in st.session_state.github_alumnado.index:
        st.error("El enlace seleccionado ya no está disponible.")
        return

    row = st.session_state.github_alumnado.loc[orig_idx]
    current_course = str(row.get('curso_academico', '') or _current_academic_course_label())

    with st.form("form_edit_github_alumno"):
        c1, c2, c3 = st.columns(3)
        with c1:
            enlace = st.text_input("Enlace GitHub", value=row.get('enlace', ''))
        with c2:
            grupo = st.selectbox("Grupo", GITHUB_GRUPOS, index=_idx(GITHUB_GRUPOS, row.get('grupo', '')))
        with c3:
            st.text_input("Curso académico", value=current_course, disabled=True)

        if st.form_submit_button("Guardar cambios", type="primary"):
            normalized_enlace = _normalize_text(enlace) or ''
            if not normalized_enlace:
                st.error("⚠ El enlace GitHub es obligatorio.")
                return
            if not _valid_github_url(normalized_enlace):
                st.error("⚠ El enlace debe ser un perfil válido de GitHub. Ejemplo: https://github.com/usuario.")
                return
            duplicate = st.session_state.github_alumnado.drop(index=orig_idx, errors='ignore')
            duplicate = duplicate[
                (duplicate['enlace'] == normalized_enlace)
                & (duplicate['curso_academico'].astype(str) == current_course)
            ]
            if not duplicate.empty:
                st.error("⚠ Ya existe ese enlace GitHub para el mismo curso académico.")
                return

            st.session_state.github_alumnado.at[orig_idx, 'enlace'] = normalized_enlace
            st.session_state.github_alumnado.at[orig_idx, 'grupo'] = _normalize_text(grupo) or ''
            st.session_state.github_alumnado.at[orig_idx, 'curso_academico'] = current_course
            try:
                save_github_alumnado(st.session_state.github_alumnado)
                st.toast("Enlace GitHub actualizado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")


@st.dialog("Eliminar enlace GitHub", width="small")
def dialog_eliminar_github_alumno():
    """Pide confirmación antes de eliminar un enlace GitHub del alumnado."""
    orig_idx = st.session_state.get('_delete_github_idx')
    if orig_idx is None or orig_idx not in st.session_state.github_alumnado.index:
        st.error("El enlace seleccionado ya no está disponible.")
        return

    row = st.session_state.github_alumnado.loc[orig_idx]
    enlace = html.escape(str(row.get('enlace', '') or ''))
    grupo = html.escape(str(row.get('grupo', '') or ''))
    curso = html.escape(str(row.get('curso_academico', '') or _current_academic_course_label()))
    st.warning(f"¿Eliminar el enlace **{enlace}** del grupo **{grupo}** del curso **{curso}**?")
    st.caption("Esta acción crea un backup automático antes de guardar.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirmar", type="primary", use_container_width=True):
            st.session_state.github_alumnado = (
                st.session_state.github_alumnado
                .drop(index=orig_idx)
                .reset_index(drop=True)
            )
            st.session_state.pop('_delete_github_idx', None)
            st.session_state.pop('_sel_github_idx', None)
            try:
                save_github_alumnado(st.session_state.github_alumnado)
                st.toast("Enlace GitHub eliminado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo eliminar: {e}")
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop('_delete_github_idx', None)
            st.rerun()


@st.dialog("Añadir", width="large")
def dialog_add_calendar_item():
    """Permite añadir formación, festivos o alternancia a la configuración de calendarios."""
    semester_start = st.session_state.get('_calendar_semester_start')
    semester_end = st.session_state.get('_calendar_semester_end')
    calendar_settings = st.session_state.get('_calendar_settings_snapshot', {})
    if not isinstance(semester_start, date) or not isinstance(semester_end, date):
        st.error("No se pudo abrir la gestión del calendario.")
        return

    st.markdown("**Añadir al calendario**")
    st.caption("Selecciona qué tipo de elemento quieres crear y completa solo los campos necesarios.")
    item_type = st.selectbox("Tipo de elemento", ["Días de formación", "Días festivos", "Día de alternancia"])

    if item_type == "Días de formación":
        st.info("Añadir o definir el periodo de formación para uno de los dos cursos.")
        calendar_target = st.selectbox("Curso al que pertenece el periodo", ["1º", "2º"])
        c1, c2 = st.columns(2)
        with c1:
            start_day = st.date_input("Fecha de inicio", value=semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_formacion_start")
        with c2:
            end_day = st.date_input("Fecha de fin", value=semester_end, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_formacion_end")
        if st.button("Guardar periodo de formación", type="primary", use_container_width=True):
            if start_day > end_day:
                st.error("La fecha final debe ser igual o posterior a la inicial.")
                return
            if calendar_target == "1º":
                primero_inicio, primero_fin = start_day, end_day
                segundo_inicio = calendar_settings.get('segundo_inicio')
                segundo_fin = calendar_settings.get('segundo_fin')
            else:
                primero_inicio = calendar_settings.get('primero_inicio')
                primero_fin = calendar_settings.get('primero_fin')
                segundo_inicio, segundo_fin = start_day, end_day
            try:
                _save_calendar_settings_payload(
                    primero_inicio,
                    primero_fin,
                    segundo_inicio,
                    segundo_fin,
                    calendar_settings.get('holiday_dates', []),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Periodo de formación guardado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    elif item_type == "Días festivos":
        st.info("Añadir un festivo puntual o un periodo festivo completo. No puede coincidir con alternancia.")
        holiday_mode = st.radio("Formato del festivo", ["Un día", "Rango"], horizontal=True)
        if holiday_mode == "Un día":
            holiday_day = st.date_input("Día festivo", value=semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_holiday_day")
        else:
            c1, c2 = st.columns(2)
            with c1:
                holiday_start = st.date_input("Inicio del periodo festivo", value=semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_holiday_start")
            with c2:
                holiday_end = st.date_input("Fin del periodo festivo", value=semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_holiday_end")
        if st.button("Guardar festivo", type="primary", use_container_width=True):
            if holiday_mode == "Un día":
                new_holidays = {holiday_day}
            else:
                if holiday_start > holiday_end:
                    st.error("La fecha final debe ser igual o posterior a la inicial.")
                    return
                day_count = (holiday_end - holiday_start).days + 1
                new_holidays = {date.fromordinal(holiday_start.toordinal() + offset) for offset in range(day_count)}
            overlap = sorted(new_holidays & set(calendar_settings.get('alternancia_dates', [])))
            if overlap:
                st.error("No se puede añadir el día porque coincide con un día de alternancia.")
                return
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    sorted(set(calendar_settings.get('holiday_dates', [])) | new_holidays),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Festivo añadido.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    else:
        st.info("Añadir un único día de alternancia. No puede coincidir con un festivo.")
        alt_day = st.date_input("Día de alternancia", value=semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="add_alternancia_day")
        if st.button("Guardar día de alternancia", type="primary", use_container_width=True):
            if alt_day in set(calendar_settings.get('holiday_dates', [])):
                st.error("No se puede añadir el día porque coincide con un festivo.")
                return
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    calendar_settings.get('holiday_dates', []),
                    sorted(set(calendar_settings.get('alternancia_dates', [])) | {alt_day}),
                )
                st.toast("Día de alternancia añadido.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")


@st.dialog("Editar", width="large")
def dialog_edit_calendar_item():
    """Permite editar formación, festivos o alternancia de la configuración de calendarios."""
    semester_start = st.session_state.get('_calendar_semester_start')
    semester_end = st.session_state.get('_calendar_semester_end')
    calendar_settings = st.session_state.get('_calendar_settings_snapshot', {})
    if not isinstance(semester_start, date) or not isinstance(semester_end, date):
        st.error("No se pudo abrir la gestión del calendario.")
        return

    holiday_ranges = _group_consecutive_dates(calendar_settings.get('holiday_dates', []))
    st.markdown("**Editar elementos del calendario**")
    st.caption("Selecciona primero qué quieres modificar y después el elemento concreto.")
    item_type = st.selectbox("Tipo de elemento", ["Días de formación", "Días festivos", "Día de alternancia"])

    if item_type == "Días de formación":
        st.info("Modificar el periodo completo de formación de uno de los dos cursos.")
        calendar_target = st.selectbox("Curso", ["1º", "2º"])
        current_start = calendar_settings.get('primero_inicio') if calendar_target == "1º" else calendar_settings.get('segundo_inicio')
        current_end = calendar_settings.get('primero_fin') if calendar_target == "1º" else calendar_settings.get('segundo_fin')
        c1, c2 = st.columns(2)
        with c1:
            start_day = st.date_input("Nueva fecha de inicio", value=current_start or semester_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_formacion_start")
        with c2:
            end_day = st.date_input("Nueva fecha de fin", value=current_end or semester_end, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_formacion_end")
        if st.button("Guardar cambios", type="primary", use_container_width=True):
            if start_day > end_day:
                st.error("La fecha final debe ser igual o posterior a la inicial.")
                return
            if calendar_target == "1º":
                primero_inicio, primero_fin = start_day, end_day
                segundo_inicio = calendar_settings.get('segundo_inicio')
                segundo_fin = calendar_settings.get('segundo_fin')
            else:
                primero_inicio = calendar_settings.get('primero_inicio')
                primero_fin = calendar_settings.get('primero_fin')
                segundo_inicio, segundo_fin = start_day, end_day
            try:
                _save_calendar_settings_payload(
                    primero_inicio,
                    primero_fin,
                    segundo_inicio,
                    segundo_fin,
                    calendar_settings.get('holiday_dates', []),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Periodo de formación actualizado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    elif item_type == "Días festivos":
        if not holiday_ranges:
            st.caption("No hay festivos para editar.")
            return
        st.info("Modificar un festivo existente, ya sea un solo día o un bloque consecutivo.")
        options = {
            _holiday_range_summary(start_day, end_day): (start_day, end_day)
            for start_day, end_day in holiday_ranges
        }
        selected_label = st.selectbox("Festivo a modificar", list(options.keys()))
        original_start, original_end = options[selected_label]
        st.caption(f"Bloque seleccionado: {_holiday_range_summary(original_start, original_end)}.")
        st.caption("Al guardar, se sustituirá este bloque completo por el nuevo valor que indiques.")
        mode = st.radio("Nuevo formato", ["Un día", "Rango"], horizontal=True)
        if mode == "Un día":
            new_day = st.date_input("Nueva fecha", value=original_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_holiday_day")
            st.caption(f"Nuevo valor: {_format_date(new_day)} · 1 día.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                new_start = st.date_input("Nuevo inicio", value=original_start, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_holiday_start")
            with c2:
                new_end = st.date_input("Nuevo fin", value=original_end, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_holiday_end")
            if new_start <= new_end:
                st.caption(f"Nuevo valor: {_holiday_range_summary(new_start, new_end)}.")
        if st.button("Guardar cambios", type="primary", use_container_width=True):
            existing_holidays = set(calendar_settings.get('holiday_dates', []))
            old_range_days = {date.fromordinal(original_start.toordinal() + offset) for offset in range((original_end - original_start).days + 1)}
            remaining_holidays = existing_holidays - old_range_days
            if mode == "Un día":
                new_range_days = {new_day}
            else:
                if new_start > new_end:
                    st.error("La fecha final debe ser igual o posterior a la inicial.")
                    return
                new_range_days = {date.fromordinal(new_start.toordinal() + offset) for offset in range((new_end - new_start).days + 1)}
            overlap = sorted(new_range_days & set(calendar_settings.get('alternancia_dates', [])))
            if overlap:
                st.error("No se puede añadir el día porque coincide con un día de alternancia.")
                return
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    sorted(remaining_holidays | new_range_days),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Festivo actualizado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    else:
        alternancia_options = calendar_settings.get('alternancia_dates', [])
        if not alternancia_options:
            st.caption("No hay días de alternancia para editar.")
            return
        st.info("Mover un día puntual de alternancia a otra fecha válida.")
        labels = {_format_date(day): day for day in alternancia_options}
        selected_label = st.selectbox("Día de alternancia a modificar", list(labels.keys()))
        original_day = labels[selected_label]
        new_day = st.date_input("Nueva fecha", value=original_day, min_value=semester_start, max_value=semester_end, format="DD/MM/YYYY", key="edit_alternancia_day")
        if st.button("Guardar cambios", type="primary", use_container_width=True):
            remaining_alternancia = set(calendar_settings.get('alternancia_dates', [])) - {original_day}
            if new_day in set(calendar_settings.get('holiday_dates', [])):
                st.error("No se puede añadir el día porque coincide con un festivo.")
                return
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    calendar_settings.get('holiday_dates', []),
                    sorted(remaining_alternancia | {new_day}),
                )
                st.toast("Día de alternancia actualizado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")


@st.dialog("Eliminar", width="large")
def dialog_delete_calendar_item():
    """Permite eliminar formación, festivos o alternancia de la configuración de calendarios."""
    calendar_settings = st.session_state.get('_calendar_settings_snapshot', {})
    holiday_ranges = _group_consecutive_dates(calendar_settings.get('holiday_dates', []))
    st.markdown("**Eliminar del calendario**")
    st.caption("Selecciona el tipo de elemento y después el registro concreto que quieres borrar.")
    item_type = st.selectbox("Tipo de elemento", ["Días de formación", "Días festivos", "Día de alternancia"])

    if item_type == "Días de formación":
        st.info("Eliminar el periodo completo de formación de uno de los cursos.")
        calendar_target = st.selectbox("Curso", ["1º", "2º"])
        if st.button("Eliminar periodo de formación", type="primary", use_container_width=True):
            if calendar_target == "1º":
                primero_inicio = None
                primero_fin = None
                segundo_inicio = calendar_settings.get('segundo_inicio')
                segundo_fin = calendar_settings.get('segundo_fin')
            else:
                primero_inicio = calendar_settings.get('primero_inicio')
                primero_fin = calendar_settings.get('primero_fin')
                segundo_inicio = None
                segundo_fin = None
            try:
                _save_calendar_settings_payload(
                    primero_inicio,
                    primero_fin,
                    segundo_inicio,
                    segundo_fin,
                    calendar_settings.get('holiday_dates', []),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Periodo de formación eliminado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    elif item_type == "Días festivos":
        if not holiday_ranges:
            st.caption("No hay festivos para eliminar.")
            return
        st.info("Eliminar un festivo puntual o un bloque consecutivo de festivos.")
        options = {
            _holiday_range_summary(start_day, end_day): (start_day, end_day)
            for start_day, end_day in holiday_ranges
        }
        selected_label = st.selectbox("Festivo a eliminar", list(options.keys()))
        start_day, end_day = options[selected_label]
        st.warning(f"Se eliminará el bloque completo: {_holiday_range_summary(start_day, end_day)}.")
        if st.button("Eliminar festivo", type="primary", use_container_width=True):
            remove_days = {date.fromordinal(start_day.toordinal() + offset) for offset in range((end_day - start_day).days + 1)}
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    sorted(set(calendar_settings.get('holiday_dates', [])) - remove_days),
                    calendar_settings.get('alternancia_dates', []),
                )
                st.toast("Festivo eliminado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")

    else:
        alternancia_options = calendar_settings.get('alternancia_dates', [])
        if not alternancia_options:
            st.caption("No hay días de alternancia para eliminar.")
            return
        st.info("Eliminar un único día de alternancia.")
        labels = {_format_date(day): day for day in alternancia_options}
        selected_label = st.selectbox("Día de alternancia a eliminar", list(labels.keys()))
        selected_day = labels[selected_label]
        if st.button("Eliminar día de alternancia", type="primary", use_container_width=True):
            try:
                _save_calendar_settings_payload(
                    calendar_settings.get('primero_inicio'),
                    calendar_settings.get('primero_fin'),
                    calendar_settings.get('segundo_inicio'),
                    calendar_settings.get('segundo_fin'),
                    calendar_settings.get('holiday_dates', []),
                    sorted(set(calendar_settings.get('alternancia_dates', [])) - {selected_day}),
                )
                st.toast("Día de alternancia eliminado.")
                st.rerun()
            except OSError as e:
                st.error(f"No se pudo guardar la configuración: {e}")


# ── Estado inicial ──────────────────────────────────────────────────────────
if 'df' not in st.session_state:
    try:
        st.session_state.df = load_data()
        st.session_state.interacciones = load_interacciones()
        st.session_state.num_estudiantes = load_num_estudiantes()
        st.session_state.github_alumnado = load_github_alumnado()
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
if 'github_alumnado' not in st.session_state:
    try:
        st.session_state.github_alumnado = load_github_alumnado()
    except Exception as e:
        st.error(f"No se pudieron cargar los enlaces GitHub del alumnado: {e}")
        st.stop()

# ── Procesar resultado pendiente de un modal ─────────────────────────────────
_pending = st.session_state.get('_dialog_action')
if _pending == 'nueva':
    _result = st.session_state.pop('_dialog_result', None)
    st.session_state.pop('_dialog_action')
    if _result is not None:
        _df = st.session_state.df
        existing_ids = pd.to_numeric(_df['id_empresa'], errors='coerce').dropna()
        _result['id_empresa'] = str(int(existing_ids.max()) + 1) if not existing_ids.empty else '1'
        st.session_state.df = pd.concat([_df, pd.DataFrame([_result])], ignore_index=True)
        try:
            save_data(st.session_state.df)
            st.toast(f"Empresa añadida: {html.escape(_result['nombre'])}")
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")

elif _pending == 'editar':
    _result = st.session_state.pop('_dialog_result', None)
    _edit_id = st.session_state.pop('_edit_id', None)
    st.session_state.pop('_dialog_action')
    if _result is not None and _edit_id is not None:
        _df = st.session_state.df
        idx = _df.index[_df['id_empresa'] == _edit_id].tolist()
        if idx:
            for col, val in _result.items():
                st.session_state.df.at[idx[0], col] = val
            try:
                save_data(st.session_state.df)
                st.toast("Cambios guardados.")
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")

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
        st.session_state.github_alumnado = load_github_alumnado()
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
app_settings = load_app_settings()

st.markdown("""
<style>
.emp-topbar {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin:0 0 6px 0;
}
.emp-topbar-title {
    font-size:1.65rem;
    font-weight:700;
    line-height:1.1;
    margin:0;
}
.emp-filter-note {
    font-size:.8rem;
    opacity:.72;
    margin:0 0 4px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Título ───────────────────────────────────────────────────────────────────
col_t, col_b = st.columns([5, 1])
with col_t:
    st.markdown('<div class="emp-topbar-title">Empresas</div>', unsafe_allow_html=True)
with col_b:
    if st.button("➕ Nueva empresa", use_container_width=True):
        dialog_nueva_empresa()

tab_empresas, tab_gestion = st.tabs(["🏢 Empresas", "⚙️ Gestión"])

with tab_empresas:
    st.markdown('<div class="emp-filter-note">Filtra y selecciona una empresa para ver su ficha.</div>', unsafe_allow_html=True)
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

    df_filtered = df_all[mask].reset_index(drop=True)

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
        df_filtered
        .join(_int_counts, on='id_empresa')
        .join(_alu_sums, on='id_empresa')
        .fillna({'interacciones': 0, 'alumnos': 0})
        .astype({'interacciones': int, 'alumnos': int})
    )

    st.caption(f"{len(df_view)} empresa(s)")

    selection = st.dataframe(
        df_view[['nombre', 'estado', 'localidad', 'regimen', 'profesor', 'interacciones', 'alumnos', 'web', 'descripcion']],
        use_container_width=True,
        hide_index=False,
        on_select="rerun",
        selection_mode="single-row",
        height=205,
    )

    selected_row = None
    if selection is not None:
        if selection.selection.rows:
            selected_row = df_view.iloc[selection.selection.rows[0]]
            st.session_state['_sel_id'] = str(selected_row['id_empresa'])
        else:
            st.session_state.pop('_sel_id', None)

    if selected_row is None and st.session_state.get('_sel_id'):
        matching = df_view[df_view['id_empresa'].astype(str) == st.session_state['_sel_id']]
        if not matching.empty:
            selected_row = matching.iloc[0]
        else:
            st.session_state.pop('_sel_id', None)

    st.divider()

    if selected_row is not None:
        empresa_id = str(selected_row['id_empresa'])

        col_info, col_acciones = st.columns([5, 1])
        with col_info:
            nombre_esc = html.escape(str(selected_row['nombre']))
            meta = " · ".join(
                v for v in [
                    selected_row.get('estado', ''),
                    selected_row.get('localidad', ''),
                    selected_row.get('regimen', ''),
                ] if v
            )
            meta_html = (f'<br><span style="font-size:.8rem;opacity:.6">{html.escape(meta)}</span>'
                         if meta else '')
            st.markdown(
                f'<div style="line-height:1.2;padding:4px 0">'
                f'<span style="font-size:1.25rem;font-weight:700">{nombre_esc}</span>'
                f'{meta_html}</div>',
                unsafe_allow_html=True,
            )
        with col_acciones:
            if st.button("✏️ Editar", key="edit_empresa_button", use_container_width=True):
                st.session_state._edit_defaults = selected_row.to_dict()
                st.session_state._edit_id = str(selected_row['id_empresa'])
                dialog_editar_empresa()
            if st.button("🗑️ Eliminar", key="delete_empresa_button", use_container_width=True):
                st.session_state._delete_empresa_id = empresa_id
                dialog_eliminar_empresa()

        tab_detalle, tab_interacciones, tab_alumnos, tab_correo = st.tabs([
            "📋 Detalle", "📞 Interacciones", "🎓 Alumnos", "✉️ Enviar correo"
        ])

        with tab_detalle:
            empresa_ficha(selected_row.to_dict())

        with tab_interacciones:
            if st.session_state.get('_prev_empresa_id') != empresa_id:
                st.session_state['_prev_empresa_id'] = empresa_id

            df_int = st.session_state.interacciones
            df_emp_int = df_int[df_int['id_empresa'] == empresa_id].reset_index()

            col_h, col_btn = st.columns([5, 1])
            with col_h:
                st.write(f"Interacciones con **{html.escape(str(selected_row['nombre']))}**")
            with col_btn:
                if st.button("➕ Añadir", key="btn_nueva_int", use_container_width=True):
                    st.session_state._int_empresa_id = empresa_id
                    st.session_state._int_empresa_estado = selected_row.get('estado', '')
                    dialog_nueva_interaccion()

            render_interacciones_timeline(df_emp_int, selected_row.get('estado', ''))

        with tab_alumnos:
            if st.session_state.get('_prev_empresa_id_alu') != empresa_id:
                st.session_state.pop('_sel_alu_idx', None)
                st.session_state['_prev_empresa_id_alu'] = empresa_id

            df_alu = st.session_state.num_estudiantes
            df_emp_alu = df_alu[df_alu['id_empresa'] == empresa_id].reset_index()

            st.write(f"Alumnos asignados a **{html.escape(str(selected_row['nombre']))}**")

            if df_emp_alu.empty:
                st.caption("Sin alumnos asignados.")
                sel_alu = None
            else:
                sel_alu = st.dataframe(
                    df_emp_alu[['num_alumnos', 'grupo', 'anio']],
                    use_container_width=True,
                    hide_index=False,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=200,
                )
                if sel_alu and sel_alu.selection.rows:
                    pos = sel_alu.selection.rows[0]
                    st.session_state['_sel_alu_idx'] = int(df_emp_alu.iloc[pos]['index'])

            orig_idx_alu = st.session_state.get('_sel_alu_idx')
            sel_alu_row = (
                st.session_state.num_estudiantes.loc[orig_idx_alu]
                if orig_idx_alu is not None and orig_idx_alu in st.session_state.num_estudiantes.index
                else None
            )
            col_alu_spacer, col_alu_add, col_alu_edit, col_alu_delete = st.columns([2.5, 1.3, 1.5, 1.7])
            with col_alu_add:
                if st.button("➕ Añadir", key="btn_nueva_alu", use_container_width=True):
                    st.session_state._alu_empresa_id = empresa_id
                    st.session_state.pop('_sel_alu_idx', None)
                    dialog_nueva_asignacion()
            with col_alu_edit:
                if st.button("✏️ Editar", key="btn_edit_alu", use_container_width=True, disabled=sel_alu_row is None):
                    st.session_state._edit_alu_idx = orig_idx_alu
                    dialog_editar_asignacion()
            with col_alu_delete:
                if st.button("🗑️ Eliminar asignación", key="btn_del_alu", use_container_width=True, disabled=sel_alu_row is None):
                    st.session_state._delete_alu_idx = orig_idx_alu
                    st.session_state._delete_alu_empresa_id = empresa_id
                    dialog_eliminar_asignacion()

        with tab_correo:
            templates = load_mail_templates()
            recipient_options = _mail_recipient_options(selected_row)

            if not templates:
                st.error("No hay plantillas de correo disponibles en la carpeta local `mail_templates`.")
            else:
                template_labels = [template['label'] for template in templates]
                selected_label = st.selectbox("Plantilla", template_labels, key=f"mail_template_{empresa_id}")
                selected_template = next(template for template in templates if template['label'] == selected_label)

                if recipient_options:
                    recipient_map = {
                        f"{option['label']}: {option['value']}": option['value']
                        for option in recipient_options
                    }
                    selected_recipient_label = st.selectbox(
                        "Destinatario",
                        list(recipient_map.keys()),
                        key=f"mail_recipient_{empresa_id}",
                    )
                    selected_recipient = recipient_map[selected_recipient_label]
                else:
                    selected_recipient = ''
                    st.warning("La empresa no tiene ningún correo válido disponible. Puedes preparar el texto igualmente.")

                rendered_mail = _render_mail_template(
                    selected_template,
                    _mail_template_context(selected_row, selected_recipient, app_settings),
                )

                st.caption("Puedes revisar y ajustar el contenido antes de copiarlo.")
                subject_value = st.text_input(
                    "Asunto",
                    value=rendered_mail['subject'],
                    key=f"mail_subject_{empresa_id}_{selected_template['id']}",
                )

                if rendered_mail.get('html_body'):
                    st.caption("Vista previa HTML")
                    components.html(rendered_mail['html_body'], height=520, scrolling=True)
                else:
                    st.text_area(
                        "Vista previa en texto",
                        value=rendered_mail['body'],
                        height=240,
                        disabled=True,
                        key=f"mail_body_preview_{empresa_id}_{selected_template['id']}",
                    )

                body_copy_value = rendered_mail.get('html_body') or rendered_mail['body']
                combined_value = (
                    f"Para: {selected_recipient}\n"
                    f"Asunto: {subject_value}\n\n"
                    f"{body_copy_value}"
                )

                c_copy_1, c_copy_2, c_copy_3 = st.columns(3)
                with c_copy_1:
                    clipboard_button("📋 Copiar asunto", subject_value, f"copy_subject_{empresa_id}")
                with c_copy_2:
                    clipboard_button(
                        "📋 Copiar cuerpo",
                        rendered_mail.get('html_body') or rendered_mail['body'],
                        f"copy_body_{empresa_id}",
                        html_text=rendered_mail.get('html_body') or None,
                    )
                with c_copy_3:
                    clipboard_button(
                        "📋 Copiar todo",
                        combined_value,
                        f"copy_full_{empresa_id}",
                        help_text="Copia destinatario, asunto y cuerpo juntos.",
                    )
    else:
        st.info("Selecciona una empresa en la tabla para ver su ficha.")

with tab_gestion:
    tab_calendarios, tab_github_alumnado = st.tabs(["📅 Calendarios", "🔗 GitHub alumnado"])

    with tab_calendarios:
        current_year = date.today().year
        primero_inicio = _semester_date_or_none(
            _parse_iso_date(app_settings.get('calendario_primero_inicio', '')),
            current_year,
        )
        primero_fin = _semester_date_or_none(
            _parse_iso_date(app_settings.get('calendario_primero_fin', '')),
            current_year,
        )
        segundo_inicio = _semester_date_or_none(
            _parse_iso_date(app_settings.get('calendario_segundo_inicio', '')),
            current_year,
        )
        segundo_fin = _semester_date_or_none(
            _parse_iso_date(app_settings.get('calendario_segundo_fin', '')),
            current_year,
        )
        holiday_dates = _special_dates_for_year(app_settings, 'festivos', current_year)
        alternancia_dates = _special_dates_for_year(app_settings, 'alternancia', current_year)

        st.write("Ajusta el periodo de formación en empresa y revisa la vista previa al instante.")
        semester_start = date(current_year, 1, 1)
        semester_end = date(current_year, 6, 30)
        st.session_state['_calendar_semester_start'] = semester_start
        st.session_state['_calendar_semester_end'] = semester_end
        st.session_state['_calendar_settings_snapshot'] = {
            'primero_inicio': primero_inicio,
            'primero_fin': primero_fin,
            'segundo_inicio': segundo_inicio,
            'segundo_fin': segundo_fin,
            'holiday_dates': holiday_dates,
            'alternancia_dates': alternancia_dates,
        }

        render_calendar_panel(
            "Calendario de prácticas",
            primero_inicio,
            primero_fin,
            segundo_inicio,
            segundo_fin,
            current_year,
            holiday_dates,
            alternancia_dates,
        )
        col_spacer, c_add, c_edit, c_delete = st.columns([6, 1, 1, 1])
        with c_add:
            if st.button("➕ Añadir", key="add_calendar_button", use_container_width=True):
                dialog_add_calendar_item()
        with c_edit:
            if st.button("✏️ Editar", key="edit_calendar_button", use_container_width=True):
                dialog_edit_calendar_item()
        with c_delete:
            if st.button("🗑️ Eliminar", key="delete_calendar_button", use_container_width=True):
                dialog_delete_calendar_item()

        st.caption(
            "Variables disponibles para futuras plantillas: "
            "{calendario_primero}, {calendario_segundo}, "
            "{calendario_primero_inicio}, {calendario_primero_fin}, "
            "{calendario_segundo_inicio}, {calendario_segundo_fin}."
        )

    with tab_github_alumnado:
        current_course = _current_academic_course_label()
        st.write("Gestiona los perfiles de GitHub del alumnado del curso académico actual.")
        st.caption(f"Curso académico actual: {current_course}")

        df_github = st.session_state.github_alumnado.copy()
        if df_github.empty:
            st.caption("No hay enlaces GitHub registrados.")
            sel_github = None
        else:
            df_github_view = df_github.reset_index()
            sel_github = st.dataframe(
                df_github_view[['enlace', 'grupo', 'curso_academico']],
                use_container_width=True,
                hide_index=False,
                on_select="rerun",
                selection_mode="single-row",
                height=240,
            )
            if sel_github and sel_github.selection.rows:
                pos = sel_github.selection.rows[0]
                st.session_state['_sel_github_idx'] = int(df_github_view.iloc[pos]['index'])
            else:
                st.session_state.pop('_sel_github_idx', None)

        orig_idx_github = st.session_state.get('_sel_github_idx')
        sel_github_row = (
            st.session_state.github_alumnado.loc[orig_idx_github]
            if orig_idx_github is not None and orig_idx_github in st.session_state.github_alumnado.index
            else None
        )

        col_spacer, c_add, c_edit, c_delete = st.columns([5.5, 1, 1, 1])
        with c_add:
            if st.button("➕ Añadir", key="btn_add_github", use_container_width=True):
                st.session_state.pop('_sel_github_idx', None)
                dialog_nuevo_github_alumno()
        with c_edit:
            if st.button("✏️ Editar", key="btn_edit_github", use_container_width=True, disabled=sel_github_row is None):
                st.session_state._edit_github_idx = orig_idx_github
                dialog_editar_github_alumno()
        with c_delete:
            if st.button("🗑️ Eliminar", key="btn_delete_github", use_container_width=True, disabled=sel_github_row is None):
                st.session_state._delete_github_idx = orig_idx_github
                dialog_eliminar_github_alumno()
