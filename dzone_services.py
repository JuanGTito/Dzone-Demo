"""Reglas transaccionales de la demo, independientes de las ventanas."""
from datetime import date, datetime
from pathlib import Path
import os
import json
import dzone_core as core
from dzone_auth import require, authorize_ticket, init_users


def event(c, entity, ident, actor, action, detail=''):
    actor=require(actor).username
    c.execute('INSERT INTO eventos(entidad, referencia, actor, accion, detalle, fecha) VALUES(?,?,?,?,?,?)',
              (entity, ident, actor, action, detail, datetime.now().isoformat(timespec='seconds')))


def create_ticket(title, equipment, skill, priority, description, actor):
    require(actor,'Supervisor')
    if not title.strip() or not equipment.strip():
        raise ValueError('Completa título y equipo.')
    with core.conn() as c:
        tid = c.execute('INSERT INTO tickets(titulo,equipo,especialidad,prioridad,descripcion,fecha_creacion) VALUES(?,?,?,?,?,?)',
            (title.strip(), equipment.strip(), skill, priority, description.strip(), date.today().isoformat())).lastrowid
        event(c, 'ticket', tid, actor, 'Creado', description.strip())
        return tid


def create_finding(technician, equipment, description, actor):
    require(actor,'Tecnico')
    if technician!=actor.username:raise ValueError('Solo puedes registrar tus propios hallazgos.')
    if not equipment.strip() or not description.strip():
        raise ValueError('Equipo y descripción son obligatorios.')
    with core.conn() as c:
        hid = c.execute('INSERT INTO hallazgos(tecnico,equipo,texto,prioridad_sugerida,fecha) VALUES(?,?,?,?,?)',
            (technician, equipment.strip(), description.strip(), core.suggested_priority(description), date.today().isoformat())).lastrowid
        event(c, 'hallazgo', hid, actor, 'Enviado', description.strip())
        return hid


def init_db(seed_demo=False):
    core.init_db(seed_demo=seed_demo)
    with core.conn() as c:
        for table, fields in {
            'tickets': {'fecha_programada': "TEXT DEFAULT ''", 'supervisor': "TEXT DEFAULT ''",'muestra_clave':"TEXT DEFAULT ''"},
            'hallazgos': {'motivo': "TEXT DEFAULT ''", 'ticket_id': 'INTEGER'},
        }.items():
            existing = {r['name'] for r in c.execute(f'PRAGMA table_info({table})')}
            for name, kind in fields.items():
                if name not in existing:
                    c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
        c.execute('''CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY, entidad TEXT NOT NULL, referencia INTEGER NOT NULL,
            actor TEXT NOT NULL, accion TEXT NOT NULL, detalle TEXT, fecha TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS borradores (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            revision INTEGER NOT NULL, contenido TEXT NOT NULL, evidencia TEXT DEFAULT '',
            fuente TEXT DEFAULT '', transcripcion_original TEXT DEFAULT '', audio TEXT DEFAULT '',
            extraccion TEXT DEFAULT '{}', modelo TEXT DEFAULT '', actor TEXT NOT NULL,
            estado TEXT NOT NULL, fecha TEXT NOT NULL, UNIQUE(ticket_id,revision))''')
        c.execute('''CREATE TABLE IF NOT EXISTS grabaciones (
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            ruta TEXT NOT NULL UNIQUE, transcripcion_original TEXT NOT NULL,
            actor TEXT NOT NULL, fecha TEXT NOT NULL)''')
        # Las demos anteriores usaban fecha_creacion como fecha programada.
        c.execute("UPDATE tickets SET fecha_programada=fecha_creacion WHERE tipo='Preventivo' AND fecha_programada=''")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_muestra ON tickets(muestra_clave) WHERE muestra_clave<>''")
        # Compatibilidad con la demo anterior sin modificar el historial original.
        for old,new in [('Ana Torres','demo1'),('Luis Ramos','demo2'),('Rosa Quispe','demo3'),('Marco Diaz','demo4')]:
            c.execute('UPDATE tickets SET tecnico=? WHERE tecnico=?',(new,old))
            c.execute('UPDATE hallazgos SET tecnico=? WHERE tecnico=?',(new,old))
    init_users()


def ticket(c, tid, states):
    r = c.execute('SELECT * FROM tickets WHERE id=?', (tid,)).fetchone()
    if not r or r['estado'] not in states:
        raise ValueError('El ticket cambió de estado. Actualiza la vista.')
    return r


def visible_tickets(actor,order='id DESC'):
    require(actor)
    # order is an internal application constant, never user input.
    if actor.role=='Supervisor':return core.query('SELECT * FROM tickets ORDER BY '+order)
    return core.query('SELECT * FROM tickets WHERE tecnico=? ORDER BY '+order,(actor.username,))


def visible_findings(actor):
    require(actor)
    suffix=" ORDER BY CASE estado WHEN 'Pendiente' THEN 0 ELSE 1 END,id DESC"
    if actor.role=='Supervisor':return core.query('SELECT * FROM hallazgos'+suffix)
    return core.query('SELECT * FROM hallazgos WHERE tecnico=?'+suffix,(actor.username,))


def read_ticket(tid,actor):
    require(actor)
    rows=core.query('SELECT * FROM tickets WHERE id=?',(tid,))
    if not rows:raise ValueError('El ticket no existe.')
    return authorize_ticket(actor,rows[0])


def read_finding(hid,actor):
    require(actor)
    rows=core.query('SELECT * FROM hallazgos WHERE id=?',(hid,))
    if not rows:raise ValueError('El hallazgo no existe.')
    row=rows[0]
    if actor.role=='Tecnico' and row['tecnico']!=actor.username:raise ValueError('Este hallazgo no pertenece a tu usuario.')
    return row


def assign_ticket(tid, person, actor, automatic=False):
    require(actor,'Supervisor')
    with core.conn() as c:
        r = ticket(c, tid, ('Pendiente', 'Asignado'))
        if r['fecha_programada'] and r['fecha_programada'] > date.today().isoformat():
            raise ValueError('El trabajo está programado para una fecha futura.')
        if (person, r['especialidad']) not in core.TECHS:
            raise ValueError('El técnico no tiene la especialidad requerida.')
        c.execute("UPDATE tickets SET tecnico=?, estado='Asignado', fecha_asignacion=? WHERE id=?",
                  (person, datetime.now().isoformat(timespec='seconds'), tid))
        event(c, 'ticket', tid, actor, 'Asignación automática' if automatic else 'Asignación manual',
              f"{r['tecnico'] or 'Sin asignar'} → {person}; especialidad {r['especialidad']}" +
              ('; menor cantidad de tickets activos entre técnicos compatibles' if automatic else ''))


def assignment(actor,only_ids=None):
    require(actor,'Supervisor')
    rows = core.query("""SELECT * FROM tickets WHERE estado='Pendiente'
        AND (fecha_programada='' OR fecha_programada<=?)
        ORDER BY CASE prioridad WHEN 'Critica' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Media' THEN 3 ELSE 4 END,id""",
        (date.today().isoformat(),))
    assigned = []
    if only_ids is not None:rows=[r for r in rows if r['id'] in set(only_ids)]
    for r in rows:
        eligible = [n for n, skill in core.TECHS if skill == r['especialidad']]
        if not eligible:
            continue
        loads = {n: core.query("SELECT COUNT(*) n FROM tickets WHERE tecnico=? AND estado IN ('Asignado','En proceso','En validacion')", (n,))[0]['n'] for n in eligible}
        person = min(eligible, key=lambda n: (loads[n], n))
        assign_ticket(r['id'], person, actor, True)
        assigned.append((r['id'], person))
    return assigned


def load_demo_tickets(actor):
    require(actor,'Supervisor')
    samples=[
        ('Inspeccionar fuga en válvula de alimentación','DEMO-VAL-01','Mecanica','Alta','Correctivo','Se reporta goteo en la válvula de alimentación. Inspeccionar y documentar la condición y el trabajo realizado.'),
        ('Revisar vibración de la bomba principal','DEMO-BOM-02','Mecanica','Alta','Correctivo','Operaciones reportó vibración. Registrar revisión, hallazgos y pruebas que efectivamente se realicen.'),
        ('Revisar indicador del tablero de control','DEMO-TAB-03','Electrica','Media','Correctivo','El indicador luminoso no enciende. Documentar diagnóstico e intervención autorizada.'),
        ('Inspeccionar tubería del sector norte','DEMO-TUB-04','General','Media','Inspeccion','Realizar inspección visual y registrar observaciones y evidencias del sector.'),
        ('Realizar limpieza del filtro de agua','DEMO-FIL-05','Mecanica','Baja','Preventivo','Limpieza programada del filtro. Documentar estado inicial, actividades y resultado.'),
        ('Revisar sello de la bomba auxiliar','DEMO-BOM-06','Mecanica','Media','Correctivo','Se solicita revisar el sello por humedad observada. No asumir la causa antes del diagnóstico.'),
        ('Inspeccionar ventilación del gabinete eléctrico','DEMO-GAB-07','Electrica','Alta','Inspeccion','Verificar la condición del gabinete y documentar las comprobaciones autorizadas.'),
        ('Verificar luminaria del pasillo de servicio','DEMO-LUM-08','Electrica','Baja','Correctivo','La luminaria tiene funcionamiento intermitente. Registrar diagnóstico y resultado.'),
        ('Revisar soporte de tubería en sala técnica','DEMO-SOP-09','General','Media','Inspeccion','Inspeccionar el soporte reportado y dejar constancia de la condición encontrada.'),
        ('Inspeccionar drenaje del área de bombas','DEMO-DRE-10','General','Media','Inspeccion','Se observa acumulación de agua. Revisar y documentar hallazgos sin atribuir causas no verificadas.'),
        ('Verificar condición de la válvula de retorno','DEMO-VAL-11','Mecanica','Media','Inspeccion','Inspeccionar la válvula y registrar las actividades y comprobaciones realizadas.'),
        ('Programar revisión de acople de la bomba','DEMO-ACO-12','Mecanica','Baja','Preventivo','Revisión preventiva del acople para esta jornada. Registrar observaciones y evidencia.'),
    ]
    ids=[];created=0
    with core.conn() as c:
        c.execute('BEGIN IMMEDIATE')
        for index,(title,equipment,skill,priority,kind,description) in enumerate(samples):
            key=f'interfaz_demo_v1_{index}'
            row=c.execute('SELECT id FROM tickets WHERE muestra_clave=?',(key,)).fetchone()
            if row:ids.append(row['id']);continue
            tid=c.execute('''INSERT INTO tickets(titulo,equipo,especialidad,prioridad,tipo,descripcion,fecha_creacion,muestra_clave)
                VALUES(?,?,?,?,?,?,?,?)''',(title,equipment,skill,priority,kind,description,date.today().isoformat(),key)).lastrowid
            event(c,'ticket',tid,actor,'Ejemplo de demostración creado',description);ids.append(tid);created+=1
    assigned=assignment(actor,only_ids=ids)
    return {'creados':created,'asignados':len(assigned),'tickets':ids}


def transition(tid, actor, action, report='', evidence='', reason=''):
    require(actor,'Supervisor' if action=='Solicitar corrección' else 'Tecnico')
    with core.conn() as c:
        expected = {'Iniciar': ('Asignado',), 'Enviar reporte': ('En proceso',), 'Solicitar corrección': ('En validacion',)}
        r = ticket(c, tid, expected[action])
        authorize_ticket(actor,r,technician_only=action!='Solicitar corrección')
        if action == 'Iniciar':
            c.execute("UPDATE tickets SET estado='En proceso', inicio=? WHERE id=?", (datetime.now().isoformat(timespec='seconds'), tid))
        elif action == 'Enviar reporte':
            if len(report.strip()) < 20:
                raise ValueError('Describe actividades, pruebas y resultados (mínimo 20 caracteres).')
            previous=c.execute('SELECT * FROM borradores WHERE ticket_id=? ORDER BY revision DESC LIMIT 1',(tid,)).fetchone()
            metadata=dict(previous) if previous else {}
            write_draft(c,tid,actor,report,evidence,metadata,'Enviado')
            c.execute("UPDATE tickets SET estado='En validacion' WHERE id=?", (tid,))
        else:
            if not reason.strip():
                raise ValueError('Debes indicar el motivo de la corrección.')
            c.execute("UPDATE tickets SET estado='En proceso' WHERE id=?", (tid,))
        event(c, 'ticket', tid, actor, action, reason or (report if action == 'Enviar reporte' else ''))


def write_draft(c,tid,actor,report,evidence,metadata,state='Borrador'):
    authorize_ticket(actor,ticket(c,tid,('En proceso',)),technician_only=True)
    revision=c.execute('SELECT COALESCE(MAX(revision),0)+1 FROM borradores WHERE ticket_id=?',(tid,)).fetchone()[0]
    extraction=metadata.get('extraccion','{}')
    if isinstance(extraction,dict):extraction=json.dumps(extraction,ensure_ascii=False)
    c.execute('''INSERT INTO borradores(ticket_id,revision,contenido,evidencia,fuente,transcripcion_original,audio,extraccion,modelo,actor,estado,fecha)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(tid,revision,report.strip(),evidence,
        metadata.get('fuente',''),metadata.get('transcripcion_original',''),metadata.get('audio',''),
        extraction,metadata.get('modelo',''),actor.username,state,datetime.now().isoformat(timespec='seconds')))
    c.execute('UPDATE tickets SET informe=?, evidencia=? WHERE id=?',(report.strip(),evidence,tid))
    event(c,'ticket',tid,actor,'Borrador guardado' if state=='Borrador' else 'Versión enviada',f'Revisión {revision}')
    return revision


def save_draft(tid,actor,report,evidence='',metadata=None):
    require(actor,'Tecnico')
    if not report.strip():raise ValueError('El borrador está vacío.')
    with core.conn() as c:
        c.execute('BEGIN IMMEDIATE')
        ticket(c,tid,('En proceso',))
        return write_draft(c,tid,actor,report,evidence,metadata or {})


def register_transcription(tid,actor,path,text):
    require(actor,'Tecnico')
    if not text.strip():raise ValueError('La transcripción está vacía.')
    with core.conn() as c:
        authorize_ticket(actor,ticket(c,tid,('En proceso',)),technician_only=True)
        c.execute('INSERT OR IGNORE INTO grabaciones(ticket_id,ruta,transcripcion_original,actor,fecha) VALUES(?,?,?,?,?)',
                  (tid,str(path),text,actor.username,datetime.now().isoformat(timespec='seconds')))
        event(c,'ticket',tid,actor,'Audio transcrito',str(path))


def review_finding(hid, approve, actor, reason='', priority=None, skill='General'):
    require(actor,'Supervisor')
    with core.conn() as c:
        r = c.execute('SELECT * FROM hallazgos WHERE id=?', (hid,)).fetchone()
        if not r or r['estado'] != 'Pendiente':
            raise ValueError('El hallazgo ya fue revisado.')
        if not approve and not reason.strip():
            raise ValueError('Indica el motivo del rechazo.')
        tid = None
        if approve:
            priority = priority or r['prioridad_sugerida']
            if priority not in core.PRIORITIES or skill not in {s for _, s in core.TECHS}:
                raise ValueError('Prioridad o especialidad inválida.')
            tid = c.execute('INSERT INTO tickets(titulo,equipo,especialidad,prioridad,descripcion,fecha_creacion) VALUES(?,?,?,?,?,?)',
                (f"Hallazgo en {r['equipo']}", r['equipo'], skill, priority, r['texto'], date.today().isoformat())).lastrowid
            event(c, 'ticket', tid, actor, 'Creado desde hallazgo', str(hid))
        c.execute('UPDATE hallazgos SET estado=?, motivo=?, ticket_id=? WHERE id=?',
                  ('Aprobado' if approve else 'Rechazado', reason, tid, hid))
        event(c, 'hallazgo', hid, actor, 'Aprobado' if approve else 'Rechazado', reason)
    return tid


def close_ticket(tid, actor, days=0, pdf_writer=None):
    require(actor,'Supervisor')
    if days not in (0, 5, 10, 15, 20, 30):
        raise ValueError('Intervalo preventivo inválido.')
    writer = pdf_writer or core.pdf_for
    staged = None
    final = core.BASE / 'reportes' / f'TK-{int(tid):03d}.pdf'
    try:
        with core.conn() as c:
            c.execute('BEGIN IMMEDIATE')
            r = dict(ticket(c, tid, ('En validacion',)))
            if len(r['informe'].strip()) < 20:
                raise ValueError('El informe está incompleto.')
            r.update(estado='Terminado', fin=datetime.now().isoformat(timespec='seconds'), supervisor=actor.username, preventivo_dias=days)
            staged = writer(r, temporary=True)
            c.execute("UPDATE tickets SET estado='Terminado',fin=?,supervisor=?,verificado=1,preventivo_dias=? WHERE id=?", (r['fin'], actor.username, days, tid))
            if days:
                due = core.workdays(date.fromisoformat(r['fin'][:10]), days).isoformat()
                child = c.execute('''INSERT INTO tickets(titulo,equipo,especialidad,prioridad,descripcion,fecha_creacion,fecha_programada,tipo,padre)
                    VALUES(?,?,?,?,?,?,?,?,?)''', (f"Preventivo {r['equipo']}", r['equipo'], r['especialidad'], 'Media',
                    f'Referencia: TK-{int(tid):03d}', date.today().isoformat(), due, 'Preventivo', tid)).lastrowid
                event(c, 'ticket', child, actor, 'Preventivo autorizado', f'Programado: {due}')
            event(c, 'ticket', tid, actor, 'Cierre validado', f'PDF: {final}; preventivo: {days} días laborales')
            # Publicar antes del commit: un fallo de escritura revierte el cierre.
            os.replace(staged, final)
        return final
    except Exception:
        if staged:
            Path(staged).unlink(missing_ok=True)
        # Ante fallo del commit, el documento puede regenerarse tras revisar el ticket.
        if final.exists() and core.query('SELECT estado FROM tickets WHERE id=?', (tid,))[0]['estado'] != 'Terminado':
            final.unlink(missing_ok=True)
        raise
