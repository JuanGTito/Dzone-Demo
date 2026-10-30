"""Dzone demo - tickets de mantenimiento, Kanban, supervisor y reportes PDF."""
import os
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta
from contextlib import contextmanager

APP = 'Dzone | Mantenimiento'
BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'DzoneDemo'
DB = BASE / 'dzone.db'
TECHS = [('demo1','Mecanica'), ('demo2','Electrica'), ('demo3','Mecanica'), ('demo4','General')]
STATES = ['Pendiente', 'Asignado', 'En proceso', 'En validacion', 'Terminado']
PRIORITIES = ['Critica','Alta','Media','Baja']


def workdays(start, n):
    d = start
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


@contextmanager
def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        with c:
            yield c
    finally:
        c.close()


def init_db(seed_demo=False):
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, equipo TEXT NOT NULL,
            especialidad TEXT NOT NULL DEFAULT 'General', prioridad TEXT NOT NULL DEFAULT 'Media',
            estado TEXT NOT NULL DEFAULT 'Pendiente', tecnico TEXT DEFAULT '',
            descripcion TEXT DEFAULT '', fecha_creacion TEXT NOT NULL, fecha_asignacion TEXT DEFAULT '',
            inicio TEXT DEFAULT '', fin TEXT DEFAULT '', informe TEXT DEFAULT '',
            verificado INTEGER DEFAULT 0, preventivo_dias INTEGER DEFAULT 0,
            padre INTEGER, tipo TEXT DEFAULT 'Correctivo', evidencia TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS hallazgos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tecnico TEXT, equipo TEXT, texto TEXT,
            prioridad_sugerida TEXT, estado TEXT DEFAULT 'Pendiente', fecha TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tickets_estado ON tickets(estado);
        ''')
        if seed_demo and not c.execute('SELECT 1 FROM tickets LIMIT 1').fetchone():
            today = date.today().isoformat()
            rows = [
                ('Fuga en valvula de alimentacion','VAL-101','Mecanica','Critica','Verificar fuga y realizar prueba de estanqueidad'),
                ('Revision de bomba principal','BOM-202','Mecanica','Alta','Vibracion elevada reportada por operaciones'),
                ('Tablero sin indicador','TAB-003','Electrica','Alta','Revisar lampara piloto y alimentacion'),
                ('Inspeccion de tuberia','TUB-015','General','Media','Revision visual programada'),
                ('Limpieza de filtro','FIL-008','Mecanica','Baja','Limpieza preventiva del filtro'),
            ]
            c.executemany('INSERT INTO tickets(titulo,equipo,especialidad,prioridad,descripcion,fecha_creacion) VALUES(?,?,?,?,?,?)', [(*r,today) for r in rows])


def query(sql, params=()):
    with conn() as c:
        return c.execute(sql,params).fetchall()


def update(sql, params=()):
    with conn() as c:
        cur=c.execute(sql,params)
        return cur.lastrowid


def suggested_priority(text):
    t=text.lower()
    if any(w in t for w in ('incendio','electrocucion','explosion','fuga grave','equipo detenido')):
        return 'Critica'
    if any(w in t for w in ('fuga','roto','no funciona','desgaste','dañad','danad','vibracion','calentamiento')):
        return 'Alta'
    if any(w in t for w in ('revisar','ajuste','inspeccion','verificar')):
        return 'Media'
    return 'Baja'


def pdf_for(row, temporary=False):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from xml.sax.saxutils import escape
    folder=BASE/'reportes';folder.mkdir(exist_ok=True)
    path=folder/f'TK-{row["id"]:03d}{".pending" if temporary else ""}.pdf'
    styles=getSampleStyleSheet(); styles['Normal'].leading=16;styles['Normal'].alignment=TA_LEFT
    doc=SimpleDocTemplate(str(path),pagesize=(595,842),leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=42)
    def p(s): return Paragraph(escape(str(s or 'No registrado')).replace('\n','<br/>'),styles['Normal'])
    story=[Paragraph('<b>DZONE | INFORME DE MANTENIMIENTO</b>',styles['Title']),Spacer(1,18)]
    records=[('Ticket',f'TK-{row["id"]:03d}'),('Actividad',row['titulo']),('Equipo',row['equipo']),
             ('Tipo',row['tipo']),('Prioridad',row['prioridad']),('Tecnico',row['tecnico']),
             ('Inicio',row['inicio']),('Cierre',row['fin']),('Estado',row['estado']),
             ('Validado por',row['supervisor'])]
    tbl=Table([[p(k),p(v)] for k,v in records],colWidths=[110,395])
    tbl.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.whitesmoke,colors.white]),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([tbl,Spacer(1,22),Paragraph('<b>Descripcion inicial</b>',styles['Heading3']),p(row['descripcion']),Spacer(1,12),
                  Paragraph('<b>Trabajo realizado / observaciones</b>',styles['Heading3']),p(row['informe']),Spacer(1,12),
                  Paragraph('<b>Evidencia adjunta (ruta local)</b>',styles['Heading3']),p(row['evidencia']),Spacer(1,30),
                  p('Documento generado desde Dzone Demo. No contiene firma digital ni certifica una aprobacion externa.')])
    try:
        doc.build(story)
    except Exception:
        if temporary:path.unlink(missing_ok=True)
        raise
    return path


