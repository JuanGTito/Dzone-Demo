"""Interfaz Windows de Dzone."""
import os
import sys
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import date, datetime
from statistics import median
from dzone_core import APP, BASE, TECHS, STATES, PRIORITIES, query, suggested_priority, pdf_for
from dzone_services import (init_db, assignment, assign_ticket, transition, close_ticket,
                            review_finding, create_ticket, create_finding, save_draft, read_ticket, read_finding,load_demo_tickets)

from dzone_views import WorkspaceViews
from dzone_ai_ui import AIActions
from dzone_login_ui import LoginActions
from dzone_auth import require
from dzone_widgets import PageScroller

class App(AIActions, LoginActions, WorkspaceViews, tk.Tk):
    def load_examples(self):
        try:result=load_demo_tickets(self.session)
        except (ValueError,sqlite3.Error) as exc:messagebox.showerror('No se pudieron cargar los ejemplos',str(exc));return
        self.refresh();self.status.set(f"Ejemplos: {result['creados']} creados, {result['asignados']} asignados. No se duplican al repetir.")

    def assign_action(self):
        if self.session.role!='Supervisor':return
        try:assigned=assignment(self.session)
        except (ValueError,sqlite3.Error) as exc:
            messagebox.showerror('No se pudo asignar',str(exc));return
        self.refresh()
        messagebox.showinfo('Asignacion',f'Se asignaron {len(assigned)} tickets segun prioridad, especialidad y carga de trabajo.\n\nLa asignacion es una regla simple, no inteligencia artificial.')

    def dialog(self,title):
        previous=self.grab_current()
        w=tk.Toplevel(self);w.title(title);w.geometry('740x760');w.minsize(650,560);w.transient(self);w.grab_set();w.configure(bg='white')
        def restore(event):
            if event.widget==w and previous is not None:
                try:
                    if previous.winfo_exists():previous.grab_set()
                except tk.TclError:pass
        w.bind('<Destroy>',restore,add='+')
        footer=tk.Frame(w,bg='#edf3fb');footer.pack(side='bottom',fill='x')
        self.button(footer,'Cerrar ventana',w.destroy).pack(side='right',padx=16,pady=8)
        page=PageScroller(w,bg='white');page.pack(fill='both',expand=True)
        return page.content

    def field(self,window,label,default='',options=None):
        tk.Label(window,text=label,bg='white',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=18,pady=(9,3))
        var=tk.StringVar(value=default)
        if options:ttk.Combobox(window,textvariable=var,values=options,state='readonly').pack(fill='x',padx=18)
        else:ttk.Entry(window,textvariable=var).pack(fill='x',padx=18)
        return var

    def textfield(self,window,label,height=5):
        tk.Label(window,text=label,bg='white',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=18,pady=(9,3))
        t=tk.Text(window,height=height,wrap='word',font=('Segoe UI',11),bg='white',fg='#334155',relief='flat',bd=0,
            highlightthickness=1,highlightbackground='#dfe5ef',highlightcolor='#818cf8',padx=12,pady=10,insertbackground='#4f46e5',undo=True)
        t.pack(fill='x',padx=18)
        return t

    def new_ticket(self):
        if self.session.role!='Supervisor':return
        w=self.dialog('Nuevo ticket')
        title=self.field(w,'Actividad / titulo')
        eq=self.field(w,'Codigo de equipo')
        skill=self.field(w,'Especialidad','General',['General','Mecanica','Electrica'])
        prio=self.field(w,'Prioridad','Media',PRIORITIES)
        desc=self.textfield(w,'Descripcion')
        def save():
            if not title.get().strip() or not eq.get().strip():messagebox.showerror('Error','Completa titulo y equipo.',parent=w);return
            if not self.attempt(lambda:create_ticket(title.get(),eq.get(),skill.get(),prio.get(),desc.get('1.0','end'),self.session)):return
            w.winfo_toplevel().destroy();self.refresh()
        self.button(w,'Guardar ticket',save,True).pack(pady=14)

    def new_finding(self):
        if self.session is None or self.session.role!='Tecnico':return
        w=self.dialog('Nuevo hallazgo del tecnico')
        tk.Label(w,text='Técnico que informa: '+self.session.username,bg='white').pack(anchor='w',padx=18,pady=12)
        eq=self.field(w,'Equipo / ubicacion')
        desc=self.textfield(w,'Describe lo encontrado (puedes dictarlo con Windows + H en un campo de texto)',8)
        suggested=tk.StringVar(value='Sin evaluar')
        tk.Label(w,textvariable=suggested,bg='white',fg='#1c6487').pack(pady=8)
        def preview():suggested.set('Prioridad sugerida (reglas): '+suggested_priority(desc.get('1.0','end')))
        self.button(w,'Analizar prioridad',preview).pack(pady=5)
        def save():
            txt=desc.get('1.0','end').strip()
            if not txt or not eq.get().strip():messagebox.showerror('Error','Equipo y descripcion son obligatorios.',parent=w);return
            if not self.attempt(lambda:create_finding(self.session.username,eq.get(),txt,self.session)):return
            w.winfo_toplevel().destroy();self.refresh();messagebox.showinfo('Enviado','Hallazgo registrado. Espera aprobacion del supervisor.')
        self.button(w,'Enviar a supervision',save,True).pack(pady=8)

    def review_finding(self,hid,approve):
        if not hid or self.session.role!='Supervisor':return
        rr=query('SELECT * FROM hallazgos WHERE id=?',(hid,))
        if not rr or rr[0]['estado']!='Pendiente':messagebox.showwarning('Aviso','Este hallazgo ya fue revisado.');return
        r=rr[0]
        w=self.dialog('Revisar hallazgo')
        text=self.textfield(w,'Descripción completa',8);text.insert('1.0',r['texto']);text.configure(state='disabled')
        priority=self.field(w,'Prioridad aprobada',r['prioridad_sugerida'],PRIORITIES)
        skill=self.field(w,'Especialidad requerida','General',['General','Mecanica','Electrica'])
        reason=self.textfield(w,'Motivo (obligatorio al rechazar)',3)
        def save():
            if not self.attempt(lambda:review_finding(hid,approve,self.session,reason.get('1.0','end').strip(),priority.get(),skill.get())):return
            w.winfo_toplevel().destroy();self.refresh()
        tk.Label(w,text=f"Estado: {r['estado']} | Ticket: {r['ticket_id'] or 'Sin ticket'}\nMotivo: {r['motivo'] or 'Sin motivo registrado'}",bg='white',wraplength=580).pack(pady=6)
        self.button(w,'Confirmar aprobación' if approve else 'Confirmar rechazo',save,True).pack(pady=12)

    def finding_detail(self,hid):
        if not hid:return
        try:r=read_finding(hid,self.session)
        except ValueError as exc:messagebox.showerror('Acceso no permitido',str(exc));return
        w=self.dialog('Detalle del hallazgo')
        text=self.textfield(w,'Hallazgo y decisión',18)
        text.insert('1.0',f"Equipo: {r['equipo']}\nTécnico: {r['tecnico']}\n\n{r['texto']}\n\nEstado: {r['estado']}\nMotivo: {r['motivo'] or 'Sin motivo registrado'}\nTicket generado: {r['ticket_id'] or 'Ninguno'}")
        for e in query("SELECT * FROM eventos WHERE entidad='hallazgo' AND referencia=? ORDER BY id",(hid,)):
            text.insert('end',f"\n\n{e['fecha']} | {e['actor']} | {e['accion']}\n{e['detalle']}")
        text.configure(state='disabled')

    def open_ticket(self,tid):
        if not tid:return
        try:r=read_ticket(tid,self.session)
        except ValueError as exc:messagebox.showerror('Acceso no permitido',str(exc));return
        admin=self.session.role=='Supervisor';w=self.dialog(f'Ticket TK-{r["id"]:03d}')
        steps=tk.Frame(w,bg='#edf3fb');steps.pack(fill='x',padx=18,pady=(14,0))
        for state in STATES:
            tk.Label(steps,text=state,fg='white' if r['estado']==state else '#59697f',
                bg='#176b58' if r['estado']==state else '#edf3fb',font=('Segoe UI',9,'bold'),padx=7,pady=9).pack(side='left',expand=True,fill='x')
        tk.Label(w,text=f'TK-{r["id"]:03d}  {r["titulo"]}',bg='white',font=('Segoe UI',14,'bold'),wraplength=570).pack(anchor='w',padx=18,pady=12)
        tk.Label(w,text=f'Equipo: {r["equipo"]}    Prioridad: {r["prioridad"]}    Estado: {r["estado"]}',bg='white').pack(anchor='w',padx=18)
        tk.Label(w,text=f'Tecnico: {r["tecnico"] or "Sin asignar"}',bg='white').pack(anchor='w',padx=18)
        if admin and r['estado'] in ('Pendiente','Asignado'):
            opts=[name for name,skill in TECHS if skill==r['especialidad']]
            if not opts:opts=['Sin técnico compatible']
            ass=self.field(w,'Asignar manualmente',r['tecnico'] if r['tecnico'] in opts else opts[0],opts)
            def assign_manual():
                if not self.attempt(lambda:assign_ticket(tid,ass.get(),self.session)):return
                w.winfo_toplevel().destroy();self.refresh()
            self.button(w,'Guardar asignacion',assign_manual,True).pack(pady=4)
        if r['estado']=='Asignado' and not admin and r['tecnico']==self.session.username:
            def start():
                if not self.attempt(lambda:transition(tid,self.session,'Iniciar')):return
                w.winfo_toplevel().destroy();self.refresh()
            self.button(w,'Iniciar trabajo',start,True).pack(pady=8)
        if r['estado']=='En proceso' and not admin and r['tecnico']==self.session.username:
            corrections=query("SELECT detalle FROM eventos WHERE entidad='ticket' AND referencia=? AND accion='Solicitar corrección' ORDER BY id DESC LIMIT 1",(tid,))
            if corrections:tk.Label(w,text='Corrección solicitada: '+corrections[0]['detalle'],bg='#fff3e0',fg='#93370d',wraplength=590,justify='left',padx=10,pady=10).pack(fill='x',padx=18,pady=10)
            report=self.textfield(w,'Reporte tecnico: actividades, pruebas y resultado',6)
            report.insert('1.0',r['informe'])
            latest=query('SELECT * FROM borradores WHERE ticket_id=? ORDER BY revision DESC LIMIT 1',(tid,))
            metadata=dict(latest[0]) if latest else {}
            evidence=tk.StringVar(value=r['evidencia'])
            self.button(w,'Generar desde voz o texto',lambda:self.voice_editor(tid,report,metadata),True).pack(pady=6)
            def draft():
                if self.attempt(lambda:save_draft(tid,self.session,report.get('1.0','end'),evidence.get(),metadata)):
                    self.status.set('Borrador guardado. Puedes cerrar y continuar después.')
                    messagebox.showinfo('Borrador guardado','Guardado sin enviar a supervisión. Puedes seguir corrigiendo.',parent=w)
            self.button(w,'Guardar borrador',draft,True).pack(pady=6)
            self.button(w,'Adjuntar evidencia (ruta a archivo)',lambda:evidence.set(filedialog.askopenfilename(parent=w) or evidence.get())).pack(pady=4)
            tk.Label(w,textvariable=evidence,bg='white',wraplength=560).pack()
            def send():
                self.preview_submission(tid,report,evidence,metadata,w)
            self.button(w,'Enviar reporte a validacion',send,True).pack(pady=8)
        if (r['estado'] in ('En validacion','Terminado') and not (r['estado']=='En validacion' and admin)) or (admin and r['estado']=='En proceso'):
            submitted=self.textfield(w,'Reporte registrado',7)
            submitted.insert('1.0',r['informe']);submitted.configure(state='disabled')
            if r['evidencia']:self.button(w,'Abrir evidencia',lambda:self.open_evidence(r['evidencia'])).pack(pady=6)
        if r['estado']=='En validacion' and admin:
            report=self.textfield(w,'Informe enviado por el técnico',8)
            report.insert('1.0',r['informe']);report.configure(state='disabled')
            tk.Label(w,text='Evidencia: '+(r['evidencia'] or 'Sin evidencia adjunta'),bg='white',wraplength=580).pack(padx=18,pady=8)
            if r['evidencia']:self.button(w,'Abrir evidencia',lambda:self.open_evidence(r['evidencia'])).pack(pady=5)
            days=self.field(w,'Autorizar preventivo (0 = sin preventivo; días laborales)','0',['0','5','10','15','20','30'])
            def finish():
                try:path=close_ticket(tid,self.session,int(days.get()))
                except Exception as exc:
                    messagebox.showerror('No se pudo cerrar',f'El ticket permanece en validación.\n{exc}');return
                w.winfo_toplevel().destroy();self.refresh()
                messagebox.showinfo('Cerrado',f'Ticket cerrado.\nPDF: {path}\nPreventivo: {days.get()} días laborales.')
            self.button(w,'Validar, cerrar y generar PDF',finish,True).pack(pady=7)
            self.button(w,'Devolver al tecnico',lambda:self.return_to_tech(tid,w)).pack(pady=4)
        if r['estado']=='Terminado':
            self.button(w,'Abrir PDF',lambda:self.show_pdf(r)).pack(pady=10)
        self.button(w,'Ver historial de decisiones',lambda:self.history(tid)).pack(pady=6)
        self.button(w,'Ver versiones del borrador',lambda:self.draft_history(tid)).pack(pady=6)
        tk.Label(w,text=f'Fecha programada: {r["fecha_programada"] or "Sin programación futura"}',bg='white').pack(pady=4)
        tk.Label(w,text=f'Descripcion inicial: {r["descripcion"]}',bg='white',wraplength=580,justify='left').pack(anchor='w',padx=18,pady=10)

    def return_to_tech(self,tid,w):
        reason=simpledialog.askstring('Solicitar corrección','¿Qué debe corregir el técnico?',parent=w.winfo_toplevel())
        if reason is None:return
        if not self.attempt(lambda:transition(tid,self.session,'Solicitar corrección',reason=reason)):return
        w.winfo_toplevel().destroy();self.refresh()

    def attempt(self, action):
        try:action();return True
        except (ValueError,sqlite3.Error,OSError) as exc:
            messagebox.showerror('Acción no realizada',str(exc));return False

    def open_evidence(self,path):
        if not Path(path).is_file():
            messagebox.showwarning('Evidencia no disponible','El archivo fue movido o eliminado.');return
        if sys.platform=='win32':self.attempt(lambda:os.startfile(path))

    def history(self,tid):
        read_ticket(tid,self.session)
        w=self.dialog('Historial del ticket')
        text=self.textfield(w,'Eventos registrados desde esta entrega',22)
        rows=query("SELECT * FROM eventos WHERE entidad='ticket' AND referencia=? ORDER BY id",(tid,))
        for r in rows:text.insert('end',f"{r['fecha']} | {r['actor']} | {r['accion']}\n{r['detalle']}\n\n")
        if not rows:text.insert('end','No hay eventos registrados para este ticket anterior a la entrega.')
        text.configure(state='disabled')

    def show_pdf(self,r):
        read_ticket(r['id'],self.session)
        path=BASE/'reportes'/f'TK-{r["id"]:03d}.pdf'
        if not path.exists():
            try:path=pdf_for(r)
            except ImportError:messagebox.showerror('Error','Instala reportlab primero.');return
        if sys.platform=='win32':os.startfile(path)
        else:messagebox.showinfo('PDF',str(path))

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--verificar-paquete':
        from dzone_diagnostic import verify
        result=verify(sys.argv[2],App);sys.exit(0 if result.get('ok') else 1)
    try:
        init_db();App().mainloop()
    except Exception as exc:
        import traceback
        try:
            BASE.mkdir(parents=True,exist_ok=True)
            with (BASE/'errores.log').open('a',encoding='utf-8') as log:log.write(traceback.format_exc()+'\n')
        except OSError:pass
        messagebox.showerror('Dzone no pudo iniciar',f'{exc}\n\nRevisa errores.log en {BASE}')
        raise
