"""
Script para generar empresas_demo.ods con datos ficticios.
Ejecutar una sola vez: python crear_demo.py
"""
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P


def make_cell(value):
    cell = TableCell()
    if value != '' and value is not None:
        cell.addElement(P(text=str(value)))
    return cell


def make_row(values):
    row = TableRow()
    for v in values:
        row.addElement(make_cell(v))
    return row


def add_sheet(doc, name, rows):
    sheet = Table(name=name)
    for row_data in rows:
        sheet.addElement(make_row(row_data))
    doc.spreadsheet.addElement(sheet)
    return sheet


doc = OpenDocumentSpreadsheet()

# ── Sheet 0: Empresas ──────────────────────────────────────────────────────────
empresas = [
    ['ID EMPRESA', 'NOMBRE EMPRESA', 'ESTADO EMPRESA', 'OBSERVACIONES', 'WEB',
     'LOCALIDAD', 'CORREO EMPRESA', 'TFNO EMPRESA', 'EXTENSIÓN TFNO',
     'CONTACTO', 'CORREO CONTACTO', 'TFNO CONTACTO',
     'TECNOLOGÍAS', 'RÉGIMEN', 'PROFESOR', 'DESCRIPCION'],

    [1,  'TechSur Canarias S.L.',       'Colabora',
     'Muy buena disposición con los alumnos', 'https://techsur.es',
     'Santa Cruz de Tenerife', 'info@techsur.es', '922100001', '',
     'Carlos Mendoza', 'c.mendoza@techsur.es', '922100002',
     'Python, Django, PostgreSQL', 'Híbrido', 'Ana García',
     'Empresa de desarrollo web y APIs REST con sede en Santa Cruz'],

    [2,  'Islas Digital S.L.',           'Colabora',
     'Acogen alumnos de DAW y DAM', 'https://islasdigital.com',
     'La Laguna', 'hola@islasdigital.com', '922200010', '',
     'Marta Reyes', 'm.reyes@islasdigital.com', '922200011',
     'React, Node.js, MongoDB', 'En remoto', 'Pedro Martín',
     'Startup de productos SaaS para pymes canarias'],

    [3,  'Volcán Software S.L.',          'Empresa potencial (interés futuro)',
     'Contactar en septiembre', 'https://volcan.software',
     'Arona', 'contacto@volcan.software', '922300020', '105',
     'Diego Fuentes', 'd.fuentes@volcan.software', '922300021',
     'Java, Spring Boot, Angular', 'Presencial', 'Laura Sánchez',
     'Desarrollo de software a medida para sector turístico'],

    [4,  'Macaronesia Systems S.L.',      'Pendiente de respuesta',
     'Enviado email en febrero, sin respuesta aún', 'https://macaronesia.sys',
     'Puerto de la Cruz', 'info@macaronesia.sys', '922400030', '',
     '', '', '',
     'PHP, Laravel, MySQL', 'Presencial', 'Miguel Torres',
     'Sistemas de gestión hotelera y turística'],

    [5,  'Atlántico Tech S.L.',           'Colabora',
     'Empresa muy comprometida con la FP', 'https://atlanticotech.es',
     'Santa Cruz de Tenerife', 'rrhh@atlanticotech.es', '922500040', '201',
     'Patricia Vega', 'p.vega@atlanticotech.es', '922500041',
     'Python, Machine Learning, FastAPI', 'Híbrido', 'Carmen López',
     'Consultoría tecnológica e inteligencia artificial'],

    [6,  'Teide Informática S.L.',        'Colaboró anteriormente',
     'Buen trato pero no tienen plazas este curso', 'https://teideinformatica.es',
     'La Orotava', 'teide@teideinformatica.es', '922600050', '',
     'Andrés Delgado', 'a.delgado@teideinformatica.es', '922600051',
     'Windows Server, Redes, VMware', 'Presencial', 'Javier Rodríguez',
     'Mantenimiento y soporte IT para empresas locales'],

    [7,  'Canary Cloud Solutions S.L.',   'Empresa potencial (solicita información)',
     'Interesados en DAM preferentemente', 'https://canarycloud.io',
     'Santa Cruz de Tenerife', 'hello@canarycloud.io', '922700060', '',
     'Lucía Borges', 'l.borges@canarycloud.io', '922700061',
     'AWS, Docker, Kubernetes, Terraform', 'En remoto', 'Elena Fernández',
     'Infraestructura cloud y DevOps para empresas medianas'],

    [8,  'Drago Digital S.L.',            'Colabora',
     '', 'https://dragodigital.com',
     'Tacoronte', 'info@dragodigital.com', '922800070', '',
     'Sofía Acosta', 's.acosta@dragodigital.com', '922800071',
     'Shopify, WooCommerce, SEO', 'Presencial', 'Roberto Díaz',
     'Agencia de marketing digital y comercio electrónico'],

    [9,  'Taoro Tecnología S.L.',         'Sin respuesta',
     'Dos emails enviados sin contestación', 'https://taorotech.es',
     'Los Realejos', 'contacto@taorotech.es', '922900080', '',
     '', '', '',
     'C#, .NET, SQL Server', 'Presencial', 'Isabel Moreno',
     'Desarrollo de software ERP para el sector agrícola'],

    [10, 'Guanche Systems S.L.',          'Colabora',
     'Excelente feedback de los alumnos', 'https://guanchesystems.com',
     'San Cristóbal de La Laguna', 'sistemas@guanchesystems.com', '922010090', '',
     'Héctor Navarro', 'h.navarro@guanchesystems.com', '922010091',
     'Linux, Python, Bash, Ansible', 'Híbrido', 'Francisco Jiménez',
     'Administración de sistemas y ciberseguridad'],

    [11, 'BitIsland S.L.',                'Empresa nueva',
     'Empresa creada hace 6 meses, sector fintech', 'https://bitisland.es',
     'Santa Cruz de Tenerife', 'team@bitisland.es', '922011100', '',
     'Irene Castro', 'i.castro@bitisland.es', '922011101',
     'Kotlin, Swift, Flutter', 'En remoto', 'María Ruiz',
     'Aplicaciones móviles para banca y finanzas'],

    [12, 'NubeTech Tenerife S.L.',        'Colabora',
     '', 'https://nubetech.es',
     'Güímar', 'nube@nubetech.es', '922012110', '300',
     'Omar Santana', 'o.santana@nubetech.es', '922012111',
     'Google Cloud, BigQuery, Python', 'Híbrido', 'Daniel Hernández',
     'Análisis de datos y business intelligence en la nube'],

    [13, 'SurCode S.L.',                  'No interesada',
     'No tienen capacidad para tutorizar alumnos', 'https://surcode.dev',
     'Arona', 'info@surcode.dev', '922013120', '',
     'Verónica Ojeda', 'v.ojeda@surcode.dev', '922013121',
     'Vue.js, Nuxt, TypeScript', 'En remoto', 'Patricia González',
     'Desarrollo frontend para startups'],

    [14, 'Océano Digital S.L.',           'Colabora',
     'Muy activos en jornadas del centro', 'https://oceanodigital.es',
     'Candelaria', 'contacto@oceanodigital.es', '922014130', '',
     'Luis Medina', 'l.medina@oceanodigital.es', '922014131',
     'WordPress, PHP, JavaScript', 'Presencial', 'Ana García',
     'Diseño y desarrollo de páginas web para turismo rural'],

    [15, 'Palmera Software S.L.',         'Empresa potencial (interés futuro)',
     'Quieren esperar al próximo curso', 'https://palmerasoftware.com',
     'Gran Canaria', 'rrhh@palmerasoftware.com', '928015140', '',
     'Cristina Álvarez', 'c.alvarez@palmerasoftware.com', '928015141',
     'Java, Microservices, Apache Kafka', 'En remoto', 'Pedro Martín',
     'Plataformas digitales para administración pública'],

    [16, 'Brisa Tecnológica S.L.',        'Colabora',
     '', 'https://brisatech.es',
     'Icod de los Vinos', 'brisa@brisatech.es', '922016150', '',
     'Mario Espinosa', 'm.espinosa@brisatech.es', '922016151',
     'React Native, Firebase, Node.js', 'Híbrido', 'Laura Sánchez',
     'Apps móviles y soluciones IoT para el hogar inteligente'],

    [17, 'Roque IT Solutions S.L.',       'Sin respuesta',
     '', 'https://roqueit.com',
     'Granadilla de Abona', 'hello@roqueit.com', '922017160', '',
     '', '', '',
     'Salesforce, Python, REST APIs', 'Presencial', 'Miguel Torres',
     'Implantación y personalización de CRM Salesforce'],

    [18, 'Timple Software S.L.',          'Colabora',
     'Dos alumnos de DAM en prácticas este año', 'https://timplesoftware.es',
     'La Laguna', 'info@timplesoftware.es', '922018170', '10',
     'Rebeca Flores', 'r.flores@timplesoftware.es', '922018171',
     'Python, Django REST, React', 'Híbrido', 'Carmen López',
     'Software de gestión para cooperativas agrícolas canarias'],

    [19, 'Calima Tech S.L.',              'Descartada',
     'Malas referencias de otras empresas del sector', 'https://calimatech.io',
     'Fuerteventura', 'calima@calimatech.io', '928019180', '',
     'Nicolás Guerra', 'n.guerra@calimatech.io', '928019181',
     'Unity, C#, ARKit', 'Presencial', 'Javier Rodríguez',
     'Videojuegos y realidad aumentada para turismo'],

    [20, 'Alisio Solutions S.L.',         'Colabora',
     'Centro de trabajo muy bien equipado', 'https://alisiosolutions.com',
     'Santa Cruz de Tenerife', 'alisio@alisiosolutions.com', '922020190', '',
     'Natalia Domínguez', 'n.dominguez@alisiosolutions.com', '922020191',
     'Cisco, Fortinet, Palo Alto, SIEM', 'Presencial', 'Elena Fernández',
     'Ciberseguridad y auditorías de seguridad para empresas'],

    [21, 'Pino Canario IT S.L.',          'Empresa potencial (solicita información)',
     'Requieren alumnos con inglés B2', 'https://pinocanarioit.es',
     'Tegueste', 'it@pinocanarioit.es', '922021200', '',
     'Álvaro Pérez', 'a.perez@pinocanarioit.es', '922021201',
     'SAP, ABAP, SAP HANA', 'Presencial', 'Roberto Díaz',
     'Consultoría e implantación SAP para medianas empresas'],

    [22, 'Bordón Digital S.L.',           'Colaboró anteriormente',
     'No tienen plazas por reducción de plantilla', 'https://bordondigital.com',
     'La Palma', 'info@bordondigital.com', '922022210', '',
     'Elena Cabrera', 'e.cabrera@bordondigital.com', '922022211',
     'Odoo, Python, PostgreSQL', 'En remoto', 'Isabel Moreno',
     'Implantación y desarrollo de módulos Odoo ERP'],

    [23, 'Garajonay Systems S.L.',        'Colabora',
     '', 'https://garajonaysys.com',
     'La Gomera', 'gs@garajonaysys.com', '922023220', '',
     'Fernando Trujillo', 'f.trujillo@garajonaysys.com', '922023221',
     'TypeScript, NestJS, GraphQL', 'En remoto', 'Francisco Jiménez',
     'Backend para plataformas de educación online'],

    [24, 'Cumbre Vieja Tech S.L.',        'Pendiente de respuesta',
     'Reunión pendiente de confirmar', 'https://cumbreviejatech.es',
     'El Hierro', 'cv@cumbreviejatech.es', '922024230', '',
     'Sara Hernández', 's.hernandez@cumbreviejatech.es', '922024231',
     'Energías renovables, IoT, Python', 'Híbrido', 'María Ruiz',
     'Software de monitorización para instalaciones de energía renovable'],

    [25, 'Hierro Digital S.L.',           'Empresa nueva',
     'Empresa fundada en 2025, sector logística', 'https://hierrodigital.io',
     'El Hierro', 'contacto@hierrodigital.io', '922025240', '',
     'Tomás Suárez', 't.suarez@hierrodigital.io', '922025241',
     'Flutter, Go, Firebase', 'En remoto', 'Daniel Hernández',
     'Apps de gestión logística para empresas de distribución'],
]
add_sheet(doc, 'Empresas', empresas)

# ── Sheet 1: Localizacion ──────────────────────────────────────────────────────
localizacion = [
    ['Adeje'], ['Arafo'], ['Arico'], ['Arona'], ['Buenavista del Norte'],
    ['Candelaria'], ['El Rosario'], ['El Sauzal'], ['El Tanque'], ['Fasnia'],
    ['Garachico'], ['Granadilla de Abona'], ['Guía de Isora'], ['Güímar'],
    ['Icod de los Vinos'], ['La Guancha'], ['La Matanza de Acentejo'],
    ['La Orotava'], ['La Victoria de Acentejo'], ['Los Realejos'], ['Los Silos'],
    ['Puerto de la Cruz'], ['San Cristóbal de La Laguna'],
    ['San Juan de la Rambla'], ['San Miguel de Abona'],
    ['Santa Cruz de Tenerife'], ['Santa Úrsula'], ['Santiago del Teide'],
    ['Tacoronte'], ['Tegueste'], ['Vilaflor de Chasna'],
    ['Gran Canaria'], ['El Hierro'], ['La Gomera'], ['La Palma'],
    ['Lanzarote'], ['Fuerteventura'], ['Península'], ['Erasmus'],
    ['Deslocalizado'], ['Extranjero'], ['Tenerife'],
]
add_sheet(doc, 'Localizacion', localizacion)

# ── Sheet 2: Profesor ──────────────────────────────────────────────────────────
profesores = [
    ['Ana García'], ['Pedro Martín'], ['Laura Sánchez'], ['Miguel Torres'],
    ['Carmen López'], ['Javier Rodríguez'], ['Elena Fernández'],
    ['Roberto Díaz'], ['Isabel Moreno'], ['Francisco Jiménez'],
    ['María Ruiz'], ['Daniel Hernández'], ['Patricia González'],
    ['Alejandro Muñoz'], ['Cristina Álvarez'],
]
add_sheet(doc, 'Profesor', profesores)

# ── Sheet 3: Regimen ──────────────────────────────────────────────────────────
regimen = [['Presencial'], ['En remoto'], ['Híbrido']]
add_sheet(doc, 'Regimen', regimen)

# ── Sheet 4: Estado_empresa ───────────────────────────────────────────────────
estados = [
    ['Descartada'], ['Empresa nueva'], ['Sin respuesta'], ['No interesada'],
    ['Empresa potencial (solicita información)'],
    ['Empresa potencial (interés futuro)'],
    ['Colaboró anteriormente'], ['Colabora'], ['Pendiente de respuesta'],
]
add_sheet(doc, 'Estado_empresa', estados)

# ── Sheet 5: Interacciones ────────────────────────────────────────────────────
interacciones = [
    ['id_empresa', 'tipo', 'descripcion', 'fecha', 'profesor'],
    [1,  'Email',              'Primer contacto, presentación del programa de FP dual', '2025-10-05', 'Ana García'],
    [1,  'Visita a empresa', 'Visita al centro, acuerdo de colaboración firmado',      '2025-11-12', 'Ana García'],
    [2,  'Llamada telefónica', 'Confirmación de plazas para DAW2',                       '2025-10-15', 'Pedro Martín'],
    [5,  'Email',              'Envío de documentación del convenio',                    '2025-09-20', 'Carmen López'],
    [5,  'Videoconferencia',   'Revisión de tareas asignadas a los alumnos',             '2026-01-10', 'Carmen López'],
    [8,  'Visita a empresa',   'Jornada de puertas abiertas con alumnos de DAM1',        '2025-12-03', 'Roberto Díaz'],
    [10, 'Email',              'Solicitud de informe de seguimiento',                    '2026-02-14', 'Francisco Jiménez'],
    [12, 'Visita a empresa', 'Presentación del proyecto final de los alumnos',         '2026-03-01', 'Daniel Hernández'],
    [14, 'Llamada telefónica', 'Confirmación de evaluación positiva de los alumnos',     '2026-03-10', 'Ana García'],
    [18, 'Email',              'Inicio de prácticas, envío de plan formativo',           '2026-01-07', 'Carmen López'],
    [20, 'Videoconferencia',   'Reunión de seguimiento trimestral',                      '2026-02-20', 'Elena Fernández'],
    [23, 'Email',              'Confirmación de plaza para DAW2',                        '2025-10-28', 'Francisco Jiménez'],
]
add_sheet(doc, 'Interacciones', interacciones)

# ── Sheet 6: Tipo_interaccion ─────────────────────────────────────────────────
tipos_interaccion = [
    ['Llamada telefónica'], ['Email'],['Visita a empresa'], ['Videoconferencia'],
]
add_sheet(doc, 'Tipo_interaccion', tipos_interaccion)

# ── Sheet 7: Num_estudiantes ──────────────────────────────────────────────────
num_estudiantes = [
    ['id_empresa', 'num_alumnos', 'grupo'],
    [1,  2, '1DAM'],
    [2,  1, '1DAW'],
    [5,  2, '2DAM'],
    [8,  1, '2DAW'],
    [10, 1, '2ASIR'],
    [12, 1, '2DAM'],
    [14, 1, '1DAW'],
    [18, 2, '2DAM'],
    [20, 1, '2ASIR'],
    [23, 1, '1DAW'],
]
add_sheet(doc, 'Num_estudiantes', num_estudiantes)

# ── Sheet 8: Grupo_estudiantes ────────────────────────────────────────────────
grupos = [
    ['1DAW'], ['1DAM'], ['1ASIR'], 
    ['2DAW'], ['2DAM'], ['2ASIR'],
]
add_sheet(doc, 'Grupo_estudiantes', grupos)

doc.save('empresas_demo.ods')
print('✓ empresas_demo.ods creado correctamente')
