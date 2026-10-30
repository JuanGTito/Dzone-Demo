"""Vistas de escritorio: navegación, listados y prioridades operativas."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from statistics import median
from dzone_core import APP, TECHS, STATES, PRIORITIES, query
from dzone_services import visible_tickets, visible_findings
from dzone_auth import require
from dzone_widgets import PageScroller,WheelRouter

NAV = ['Inicio', 'Mi jornada', 'Tickets', 'Tablero Kanban', 'Validaciones', 'Hallazgos y aprobacion', 'Indicadores', 'IA y voz']
LABELS = {'Tablero Kanban': 'Tablero Kanban', 'Hallazgos y aprobacion': 'Hallazgos'}
COLORS = {'Critica': '#b42318', 'Alta': '#b54708', 'Media': '#175cd3', 'Baja': '#475467'}
ORDER = "CASE prioridad WHEN 'Critica' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Media' THEN 3 ELSE 4 END,id"


class WorkspaceViews:
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry('1280x820');self.minsize(1060,680)
        self.configure(bg='#f5f7fb')
        self.wheel=WheelRouter(self)
        self.report_callback_exception = self.callback_error
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('Treeview',font=('Segoe UI',11),rowheight=48,background='white',fieldbackground='white',borderwidth=0,relief='flat')
        style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),background='#f3f5fa',foreground='#64748b',padding=(12,15),borderwidth=0,relief='flat')
        style.map('Treeview',background=[('selected','#eef2ff')],foreground=[('selected','#4338ca')])
        style.configure('TEntry',padding=(10,9),fieldbackground='white',bordercolor='#dfe5ef',lightcolor='#dfe5ef',darkcolor='#dfe5ef')
        style.configure('TCombobox',padding=(8,8),fieldbackground='white',background='#f8fafc',bordercolor='#dfe5ef')
        self.session=None
        self.show_login()

    def build_workspace(self):
        require(self.session)
        self.title(APP)
        self.geometry('1280x820');self.minsize(1060,680)
        self.role=tk.StringVar(value=self.session.role);self.user=tk.StringVar(value=self.session.username)
        self.search=tk.StringVar();self.state_filter=tk.StringVar(value='Todos')
        self.priority_filter=tk.StringVar(value='Todas');self.technician_filter=tk.StringVar(value='Todos')
        self.status=tk.StringVar(value='Listo. Selecciona una tarea para comenzar.')
        self.current_view='Inicio'
        sidebar=tk.Frame(self,bg='#14243b',width=224);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        tk.Label(sidebar,text='DZONE',font=('Segoe UI',25,'bold'),fg='white',bg='#14243b').pack(anchor='w',padx=24,pady=(28,0))
        tk.Label(sidebar,text='Mantenimiento',font=('Segoe UI',11),fg='#a8bdd7',bg='#14243b').pack(anchor='w',padx=24,pady=(0,30))
        self.nav_buttons={}
        self.allowed_nav=[n for n in NAV if self.session.role=='Supervisor' or n not in ('Validaciones','Indicadores','IA y voz')]
        for name in self.allowed_nav:
            button=tk.Button(sidebar,text=LABELS.get(name,name),anchor='w',font=('Segoe UI',11),bg='#14243b',fg='#dce5f2',
                activebackground='#294461',activeforeground='white',relief='flat',bd=0,padx=20,pady=12,cursor='hand2',command=lambda n=name:self.navigate(n))
            button.pack(fill='x',padx=10,pady=2);self.nav_buttons[name]=button
        tk.Label(sidebar,text='DEMO LOCAL\nTu trabajo, en un solo lugar',justify='left',font=('Segoe UI',9),fg='#a8bdd7',bg='#14243b',wraplength=178).pack(side='bottom',anchor='w',padx=24,pady=24)
        main=tk.Frame(self,bg='#f2f5fa');main.pack(side='left',fill='both',expand=True)
        header=tk.Frame(main,bg='white');header.pack(fill='x')
        self.page_title=tk.StringVar(value='Mantenimiento / Inicio')
        tk.Label(header,textvariable=self.page_title,font=('Segoe UI',12,'bold'),fg='#64748b',bg='white').pack(side='left',padx=22,pady=22)
        self.button(header,'Actualizar',self.refresh).pack(side='right',padx=16)
        self.button(header,'Cerrar sesión',self.logout).pack(side='right',padx=8)
        tk.Label(header,text=f'{self.session.username} · {self.session.role}',bg='white',fg='#176b58',font=('Segoe UI',11,'bold')).pack(side='right',padx=12)
        tk.Label(main,textvariable=self.status,anchor='w',font=('Segoe UI',10),bg='#e7f2ee',fg='#235b48',padx=18,pady=9).pack(side='bottom',fill='x')
        self.page_container=tk.Frame(main,bg='#f2f5fa');self.page_container.pack(fill='both',expand=True,padx=18,pady=18)
        self.page_container.rowconfigure(0,weight=1);self.page_container.columnconfigure(0,weight=1)
        self.panes={};self.pages={}
        for name in self.allowed_nav:
            page=PageScroller(self.page_container);page.grid(row=0,column=0,sticky='nsew')
            self.panes[name]=page.content;self.pages[name]=page
        self.refresh();self.navigate('Inicio' if self.session.role=='Supervisor' else 'Mi jornada')

    def callback_error(self,kind,error,tb):
        import traceback
        from dzone_core import BASE
        detail=''.join(traceback.format_exception(kind,error,tb))
        try:
            BASE.mkdir(parents=True,exist_ok=True)
            with (BASE/'errores.log').open('a',encoding='utf-8') as log:log.write(detail+'\n')
        except OSError:pass
        if hasattr(self,'status'):self.status.set('No se pudo completar la acción. Revisa el mensaje de error.')
        messagebox.showerror('Dzone · Error',f'{error}\n\nEl detalle se registra en errores.log.',parent=self)

    def navigate(self,name):
        require(self.session)
        if name not in self.allowed_nav:name='Mi jornada' if self.session.role=='Tecnico' else 'Inicio'
        self.current_view=name;self.pages[name].tkraise()
        self.page_title.set('Mantenimiento / '+LABELS.get(name,name))
        for key,b in self.nav_buttons.items():b.configure(bg='#294461' if key==name else '#14243b',fg='white' if key==name else '#dce5f2')

    def clear(self,name):
        p=self.panes[name]
        for child in p.winfo_children():child.destroy()
        self.pages[name].reset()
        return p

    def titleline(self,parent,title,desc=''):
        background=parent.cget('bg')
        tk.Label(parent,text=title,font=('Segoe UI',24,'bold'),bg=background,fg='#17233b').pack(anchor='w',padx=22,pady=(24,6))
        if desc:tk.Label(parent,text=desc,font=('Segoe UI',11),bg=background,fg='#718096',wraplength=790,justify='left').pack(anchor='w',padx=22,pady=(0,22))

    def button(self,parent,title,command,primary=False):
        base='#4f46e5' if primary else '#eef2f8';hover='#4338ca' if primary else '#e1e7f2'
        button=tk.Button(parent,text=title,command=command,bg=base,fg='white' if primary else '#334155',
            activebackground=hover,activeforeground='white' if primary else '#17233b',relief='flat',bd=0,
            font=('Segoe UI',10,'bold'),padx=18,pady=11,cursor='hand2',highlightthickness=1,highlightbackground=base,highlightcolor='#818cf8')
        button.bind('<Enter>',lambda e:button.configure(bg=hover) if button.cget('state')!='disabled' else None)
        button.bind('<Leave>',lambda e:button.configure(bg=base))
        return button

    def bar(self,parent,bottom=False):
        p=tk.Frame(parent,bg=parent.cget('bg'));p.pack(side='bottom' if bottom else 'top',fill='x',padx=22,pady=(0,14));return p

    def empty(self,parent,title,detail):
        box=tk.Frame(parent,bg='#f5f8fc');box.pack(fill='x',padx=20,pady=20)
        tk.Label(box,text=title,bg='#f5f8fc',fg='#14243b',font=('Segoe UI',13,'bold')).pack(anchor='w',padx=20,pady=(18,6))
        tk.Label(box,text=detail,bg='#f5f8fc',fg='#59697f',wraplength=750,justify='left').pack(anchor='w',padx=20,pady=(0,18))

    def scroll_area(self,parent,bg='white'):
        content=tk.Frame(parent,bg=bg);content.pack(fill='both',expand=True,padx=16,pady=8)
        return content

    def make_table(self,parent,cols,rows,widths=None):
        wrap=tk.Frame(parent,bg='white',highlightbackground='#e3e8f1',highlightthickness=1);wrap.pack(fill='both',expand=True,padx=22,pady=(8,22))
        caption=tk.Frame(wrap,bg='white');caption.grid(row=0,column=0,sticky='ew')
        tk.Label(caption,text='REGISTROS',bg='white',fg='#475569',font=('Segoe UI',9,'bold')).pack(side='left',padx=16,pady=15)
        tk.Label(caption,text=f'{len(rows)} en esta vista',bg='white',fg='#94a3b8',font=('Segoe UI',10)).pack(side='right',padx=16)
        wrap.rowconfigure(1,weight=1);wrap.columnconfigure(0,weight=1)
        tree=ttk.Treeview(wrap,columns=cols,show='headings',selectmode='browse',height=max(1,len(rows)))
        for i,c in enumerate(cols):tree.heading(c,text=c);tree.column(c,width=widths[i] if widths else 140,minwidth=85)
        tree.tag_configure('odd',background='#fafbfe')
        for i,r in enumerate(rows):tree.insert('',tk.END,values=r,tags=('odd',) if i%2 else ())
        tree.grid(row=1,column=0,sticky='nsew')
        return tree

    def selected(self,tree):
        sel=tree.selection()
        if not sel:messagebox.showinfo('Selecciona un ticket','Selecciona una fila o haz doble clic para abrirla.');return None
        value=str(tree.item(sel[0],'values')[0]);return int(value.removeprefix('TK-'))

    def ticket_table(self,parent,records):
        if not records:self.empty(parent,'Sin tickets en esta vista','Prueba otros filtros o crea un ticket desde la vista de supervisión.')
        tree=self.make_table(parent,['Ticket','Actividad','Equipo','Prioridad','Responsable','Estado','Programado'],
            [(f"TK-{r['id']:03d}",r['titulo'],r['equipo'],r['prioridad'],r['tecnico'] or 'Sin asignar',r['estado'],r['fecha_programada'] or '—') for r in records],
            [95,290,110,95,150,130,120])
        tree.bind('<Double-1>',lambda e:self.open_ticket(self.selected(tree)))
        tree.bind('<Return>',lambda e:self.open_ticket(self.selected(tree)))
        return tree

    def refresh(self):
        if self.session is None:return
        require(self.session)
        self.home();self.jornada();self.tickets();self.kanban();self.findings()
        if self.session.role=='Supervisor':self.validations();self.stats();self.ai_settings()
        self.status.set(f"Actualizado a las {datetime.now():%H:%M} · {self.session.role} · {self.session.username}")

    def home(self):
        p=self.clear('Inicio');admin=self.session.role=='Supervisor'
        self.titleline(p,'Tu operación, de un vistazo' if admin else 'Todo listo para tu jornada',f'{date.today():%d/%m/%Y} · Prioriza, documenta y da seguimiento al trabajo.')
        actions=self.bar(p)
        if admin:
            self.button(actions,'+ Crear ticket',self.new_ticket,True).pack(side='left',padx=(0,8))
            self.button(actions,'Asignar pendientes',self.assign_action).pack(side='left',padx=4)
            self.button(actions,'Cargar ejemplos',self.load_examples).pack(side='left',padx=4)
        else:self.button(actions,'Ver mi jornada',lambda:self.navigate('Mi jornada'),True).pack(side='left')
        if not admin:self.button(actions,'Registrar hallazgo',self.new_finding).pack(side='left',padx=8)
        rows=visible_tickets(self.session);today=date.today().isoformat()
        if not admin:rows=[r for r in rows if r['tecnico']==self.session.username]
        ready=[r for r in rows if not r['fecha_programada'] or r['fecha_programada']<=today]
        findings=[r for r in visible_findings(self.session) if r['estado']=='Pendiente']
        metrics=[('Por asignar',sum(r['estado']=='Pendiente' for r in ready),'Tickets','Pendiente'),
            ('Por validar',sum(r['estado']=='En validacion' for r in rows),'Validaciones','Todos'),
            ('Hallazgos pendientes',len(findings),'Hallazgos y aprobacion','Todos'),
            ('En proceso',sum(r['estado']=='En proceso' for r in rows),'Tickets','En proceso')]
        if not admin:
            metrics[0]=('Por iniciar',sum(r['estado']=='Asignado' for r in ready),'Tickets','Asignado')
            metrics[1]=('Reportes enviados',sum(r['estado']=='En validacion' for r in rows),'Tickets','En validacion')
        cards=self.bar(p)
        for i,(label,count,target,state) in enumerate(metrics):
            cards.columnconfigure(i,weight=1)
            def go(t=target,s=state):
                self.search.set('');self.priority_filter.set('Todas')
                self.technician_filter.set('Todos' if admin else self.session.username)
                self.state_filter.set(s);self.tickets();self.navigate(t)
            card=tk.Frame(cards,bg='white',highlightbackground='#e2e8f0',highlightthickness=1)
            card.grid(row=0,column=i,sticky='nsew',padx=(0,10))
            caption=tk.Label(card,text=label,bg='white',fg='#64748b',font=('Segoe UI',10),wraplength=145,anchor='w',justify='left')
            caption.pack(anchor='w',padx=18,pady=(18,2))
            b=tk.Button(card,text=str(count),command=go,font=('Segoe UI',29,'bold'),bg='white',fg='#17233b',relief='flat',anchor='w',bd=0,cursor='hand2',activebackground='#f5f7ff')
            b.pack(fill='x',padx=18,pady=2)
            link=tk.Label(card,text='Ver detalle  →',bg='white',fg='#6366f1',font=('Segoe UI',9,'bold'),cursor='hand2')
            link.pack(anchor='w',padx=18,pady=(0,16))
            for widget in (card,caption,link):widget.bind('<Button-1>',lambda event,command=go:command())
        self.titleline(p,'Qué hacer ahora','Abre un ticket con doble clic o usa las acciones de la barra lateral.')
        important=sorted([r for r in ready if r['estado']!='Terminado'],key=lambda r:(0 if r['estado']=='En validacion' else 1,PRIORITIES.index(r['prioridad']) if r['prioridad'] in PRIORITIES else 9,r['id']))
        bottom=self.bar(p,True)
        tree=self.ticket_table(p,important[:8])
        self.button(bottom,'Abrir ticket seleccionado',lambda:self.open_ticket(self.selected(tree)),True).pack(side='left')

    def jornada(self):
        p=self.clear('Mi jornada');admin=self.session.role=='Supervisor'
        self.titleline(p,'Plan de trabajo de hoy' if admin else f'Jornada de {self.session.username}',
            'Trabajos disponibles por fecha y prioridad. Los preventivos futuros permanecen en Tickets.')
        bar=self.bar(p)
        if admin:self.button(bar,'Asignar automáticamente',self.assign_action,True).pack(side='left',padx=(0,8))
        if not admin:self.button(bar,'Registrar hallazgo',self.new_finding).pack(side='left')
        sql="SELECT * FROM tickets WHERE estado!='Terminado' AND (fecha_programada='' OR fecha_programada<=?)"
        args=[date.today().isoformat()]
        if not admin:sql+=' AND tecnico=?';args.append(self.session.username)
        rows=query(sql+' ORDER BY '+ORDER,args)
        if not rows:
            self.empty(p,'No hay trabajos para hoy','El supervisor debe asignar los pendientes. También puedes registrar un hallazgo desde esta pantalla.');return
        body=self.scroll_area(p)
        for r in rows:self.task_card(body,r)

    def task_card(self,parent,r):
        card=tk.Frame(parent,bg='white',highlightbackground='#e3e8f1',highlightthickness=1)
        card.pack(fill='x',padx=4,pady=8)
        tk.Frame(card,bg=COLORS.get(r['prioridad'],'#64748b'),width=4).pack(side='left',fill='y')
        top=tk.Frame(card,bg='white');top.pack(fill='x',padx=20,pady=(18,10))
        tk.Label(top,text=f"TK-{r['id']:03d}  ·  {r['prioridad'].upper()}",fg=COLORS.get(r['prioridad'],'#475467'),bg='white',font=('Segoe UI',10,'bold')).pack(side='left')
        tk.Label(top,text=r['estado'],fg='#4f46e5',bg='#eef2ff',font=('Segoe UI',10),padx=10,pady=5).pack(side='right')
        tk.Label(card,text=r['titulo'],bg='white',fg='#17233b',font=('Segoe UI',15,'bold'),wraplength=700,justify='left').pack(anchor='w',padx=20)
        tk.Label(card,text=f"{r['equipo']} · {r['especialidad']} · {r['tecnico'] or 'Sin asignar'}",bg='white',fg='#718096',font=('Segoe UI',10)).pack(anchor='w',padx=20,pady=10)
        action={'Pendiente':'Asignar ticket','Asignado':'Abrir e iniciar','En proceso':'Continuar reporte','En validacion':'Revisar reporte' if self.session.role=='Supervisor' else 'Ver reporte enviado','Terminado':'Ver cierre y PDF'}[r['estado']]
        if self.session.role=='Supervisor' and r['estado'] in ('Asignado','En proceso'):action='Ver asignación' if r['estado']=='Asignado' else 'Ver avance'
        self.button(card,action,lambda tid=r['id']:self.open_ticket(tid),True).pack(anchor='e',padx=16,pady=(0,12))

    def tickets(self):
        p=self.clear('Tickets');self.titleline(p,'Tickets','Busca por código, actividad, equipo o responsable. Incluye la programación futura.')
        top=self.bar(p)
        entry=ttk.Entry(top,textvariable=self.search,width=27);entry.pack(side='left',padx=(0,6));entry.bind('<Return>',lambda e:self.tickets())
        self.button(top,'Buscar',self.tickets,True).pack(side='left')
        if self.session.role=='Supervisor':self.button(top,'+ Crear ticket',self.new_ticket).pack(side='right')
        filters=self.bar(p)
        options_list=[('Estado',self.state_filter,['Todos']+STATES),('Prioridad',self.priority_filter,['Todas']+PRIORITIES)]
        if self.session.role=='Supervisor':options_list.append(('Técnico',self.technician_filter,['Todos']+[n for n,_ in TECHS]))
        for label,var,options in options_list:
            tk.Label(filters,text=label,bg='white',fg='#59697f').pack(side='left',padx=(0,5))
            combo=ttk.Combobox(filters,textvariable=var,values=options,state='readonly',width=15);combo.pack(side='left',padx=(0,12));combo.bind('<<ComboboxSelected>>',lambda e:self.tickets())
        self.button(filters,'Limpiar',self.reset_filters).pack(side='left')
        rows=visible_tickets(self.session,ORDER)
        term=self.search.get().casefold().strip()
        rows=[r for r in rows if (not term or term in f"TK-{r['id']:03d} {r['titulo']} {r['equipo']} {r['tecnico']}".casefold())
              and (self.state_filter.get()=='Todos' or r['estado']==self.state_filter.get())
              and (self.priority_filter.get()=='Todas' or r['prioridad']==self.priority_filter.get())
              and (self.technician_filter.get()=='Todos' or r['tecnico']==self.technician_filter.get())]
        tk.Label(p,text=f'{len(rows)} tickets encontrados',bg='white',fg='#59697f').pack(anchor='w',padx=20)
        bottom=self.bar(p,True)
        tree=self.ticket_table(p,rows)
        self.button(bottom,'Abrir ticket seleccionado',lambda:self.open_ticket(self.selected(tree)),True).pack(side='left')

    def reset_filters(self):
        self.search.set('');self.state_filter.set('Todos');self.priority_filter.set('Todas');self.technician_filter.set('Todos');self.tickets()

    def kanban(self):
        p=self.clear('Tablero Kanban');self.titleline(p,'Tablero operativo','Sigue el avance en una sola página. Usa la rueda del mouse en cualquier zona para desplazarte.')
        body=tk.Frame(p,bg='white');body.pack(fill='both',expand=True,padx=12,pady=10)
        for i,state in enumerate(STATES):
            body.columnconfigure(i,weight=1,uniform='kanban')
            col=tk.Frame(body,bg='#f1f4f9');col.grid(row=0,column=i,sticky='nsew',padx=5)
            rows=[r for r in visible_tickets(self.session,ORDER) if r['estado']==state]
            heading=tk.Frame(col,bg='#f1f4f9');heading.pack(fill='x',padx=10,pady=14)
            tk.Label(heading,text=state,bg='#f1f4f9',fg='#475569',font=('Segoe UI',10,'bold'),wraplength=120).pack(side='left')
            tk.Label(heading,text=str(len(rows)),bg='white',fg='#6366f1',font=('Segoe UI',10,'bold'),padx=7,pady=3).pack(side='right')
            inner=self.scroll_area(col,'#f1f4f9')
            if not rows:tk.Label(inner,text='Sin tickets',bg='#f1f4f9',fg='#94a3b8').pack(pady=20)
            for r in rows:
                c=tk.Frame(inner,bg='white',highlightbackground='#e3e8f1',highlightthickness=1);c.pack(fill='x',pady=6)
                tk.Label(c,text=f"TK-{r['id']:03d} · {r['prioridad']}",fg=COLORS.get(r['prioridad']),bg='white',font=('Segoe UI',9,'bold')).pack(anchor='w',padx=8,pady=8)
                tk.Label(c,text=r['titulo'],wraplength=125,justify='left',bg='white',fg='#14243b').pack(anchor='w',padx=8)
                tk.Label(c,text=r['tecnico'] or 'Sin asignar',bg='white',fg='#59697f',wraplength=125).pack(anchor='w',padx=8,pady=5)
                self.button(c,'Abrir',lambda tid=r['id']:self.open_ticket(tid)).pack(fill='x',padx=6,pady=6)
        body.rowconfigure(0,weight=1)

    def validations(self):
        p=self.clear('Validaciones');self.titleline(p,'Reportes por validar','Revisa las actividades y evidencias. Aprueba el cierre o solicita una corrección con motivo.')
        if self.session.role!='Supervisor':self.empty(p,'Vista de supervisión','El supervisor revisa los reportes enviados desde Mi jornada.');return
        rows=query("SELECT * FROM tickets WHERE estado='En validacion' ORDER BY "+ORDER)
        if not rows:self.empty(p,'Estás al día','Los reportes enviados por los técnicos aparecerán aquí para su revisión.');return
        body=self.scroll_area(p)
        for r in rows:self.task_card(body,r)

    def findings(self):
        p=self.clear('Hallazgos y aprobacion');self.titleline(p,'Hallazgos de campo','Una observación se convierte en ticket únicamente después de la aprobación del supervisor.')
        bar=self.bar(p)
        if self.session.role=='Tecnico':self.button(bar,'+ Registrar hallazgo',self.new_finding,True).pack(side='left')
        rows=visible_findings(self.session)
        actions=self.bar(p,True)
        if not rows:self.empty(p,'Todavía no hay hallazgos','Registra una observación de campo. Quedará pendiente de revisión.')
        tree=self.make_table(p,['ID','Técnico','Equipo','Descripción','Prioridad sugerida','Estado','Fecha'],
            [(r['id'],r['tecnico'],r['equipo'],r['texto'][:95],r['prioridad_sugerida'],r['estado'],r['fecha']) for r in rows],[60,140,100,300,140,100,110])
        tree.bind('<Double-1>',lambda e:self.finding_detail(self.selected(tree)))
        self.button(actions,'Ver detalle y decisión',lambda:self.finding_detail(self.selected(tree))).pack(side='left',padx=(0,8))
        if self.session.role=='Supervisor':
            self.button(actions,'Revisar y aprobar',lambda:self.review_finding(self.selected(tree),True),True).pack(side='left',padx=4)
            self.button(actions,'Rechazar con motivo',lambda:self.review_finding(self.selected(tree),False)).pack(side='left',padx=4)

    def stats(self):
        p=self.clear('Indicadores');self.titleline(p,'Indicadores de mantenimiento','Información de la base local. La reincidencia es una señal para investigar.')
        rows=query('SELECT * FROM tickets');bar=self.bar(p)
        for state in STATES:
            tk.Label(bar,text=f"{sum(r['estado']==state for r in rows)}\n{state}",bg='#edf3fb',fg='#14243b',font=('Segoe UI',11,'bold'),padx=14,pady=16).pack(side='left',expand=True,fill='x',padx=3)
        hours=[]
        for r in rows:
            if r['estado']=='Terminado':
                try:hours.append((datetime.fromisoformat(r['fin'])-datetime.fromisoformat(r['inicio'])).total_seconds()/3600)
                except (TypeError,ValueError):pass
        self.empty(p,f'Mediana inicio a cierre: {median(hours):.2f} h' if hours else 'Aún no hay tiempos suficientes',
            'Incluye la espera de validación. La demo todavía no descuenta pausas ni separa tiempo efectivo.')
        alerts=[]
        for equipment in sorted({r['equipo'] for r in rows}):
            count=sum(r['equipo']==equipment and r['tipo']=='Correctivo' for r in rows)
            if count>1:alerts.append((equipment,count,'Investigar causas; no demuestra reparación deficiente'))
        if alerts:self.make_table(p,['Equipo','Correctivos','Seguimiento'],alerts,[150,110,500])
        else:self.empty(p,'Sin alertas de reincidencia','No hay equipos con más de un correctivo registrado.')
