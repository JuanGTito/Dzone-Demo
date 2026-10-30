"""Editor de narración por micrófono/texto y borrador verificable."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import dzone_ai as ai
from dzone_core import query
from dzone_services import save_draft, register_transcription, transition, read_ticket
from dzone_auth import require


class AIActions:
    def ai_settings(self):
        p=self.clear('IA y voz')
        self.titleline(p,'IA y voz en este equipo','Qwen3 4B organiza el texto; Whisper Tiny transcribe el micrófono. Los dos motores se ejecutan localmente.')
        p=self.scroll_area(p)
        self.empty(p,'Primero un borrador, después la validación','Abre un ticket en proceso → Generar desde voz o texto → revisa la transcripción → extrae → usa y guarda el borrador. No se envía al supervisor automáticamente.')
        cfg=ai.settings();fields={}
        if self.session.role!='Supervisor':
            self.empty(p,'Voz y borradores de tus tickets','Los controles de grabación y extracción están dentro de cada ticket en proceso. El supervisor administra las rutas de los modelos.')
            return
        for key,label,directory in [('motor','Motor portátil llama-server.exe',False),('modelo','Modelo Qwen3 4B (.gguf)',False),('voz','Carpeta del modelo de transcripción',True)]:
            fields[key]=self.field(p,label,cfg[key])
            def choose(k=key,is_directory=directory):
                value=filedialog.askdirectory(parent=self) if is_directory else filedialog.askopenfilename(parent=self)
                if value:fields[k].set(value)
            self.button(p,'Seleccionar carpeta' if directory else 'Seleccionar archivo',choose).pack(anchor='e',padx=18,pady=3)
        paths=[('Motor',Path(cfg['motor']).is_file()),('Qwen3 4B',Path(cfg['modelo']).is_file()),('Voz', (Path(cfg['voz'])/'model.bin').is_file())]
        tk.Label(p,text=' · '.join(label+(': disponible' if exists else ': falta') for label,exists in paths),bg='white',fg='#59697f',wraplength=750).pack(anchor='w',padx=18,pady=12)
        def save():
            require(self.session,'Supervisor')
            if self.attempt(lambda:ai.save_settings({key:v.get() for key,v in fields.items()})):
                self.ai_settings();self.status.set('Configuración local guardada.')
        self.button(p,'Guardar configuración',save,True).pack(anchor='w',padx=18,pady=8)

    def voice_editor(self,tid,report,metadata):
        require(self.session,'Tecnico');read_ticket(tid,self.session)
        w=self.dialog('Narración y extracción local · borrador');top=w.winfo_toplevel()
        self.titleline(w,'Tu narración, convertida en borrador','Graba, detén y transcribe. Revisa el texto antes de extraer. También puedes escribirlo directamente.')
        status=tk.StringVar(value='Micrófono apagado. No se graba hasta pulsar Grabar.')
        tk.Label(w,textvariable=status,bg='#edf3fb',fg='#14243b',wraplength=620,padx=12,pady=12).pack(fill='x',padx=18,pady=8)
        bar=tk.Frame(w,bg='white');bar.pack(fill='x',padx=18,pady=12)
        tools=tk.Frame(w,bg='white');tools.pack(fill='x',padx=18,pady=(0,6))
        source=self.textfield(w,'Narración editable: revisa nombres y cifras; separa actividades con puntos',7)
        last_audio=query('SELECT * FROM grabaciones WHERE ticket_id=? ORDER BY id DESC LIMIT 1',(tid,))
        source.insert('1.0',metadata.get('fuente','') or (last_audio[0]['transcripcion_original'] if last_audio else ''))
        preview=self.textfield(w,'Propuesta de borrador (no enviada)',8);preview.configure(state='disabled')
        recorder=ai.Recorder();context=dict(metadata);result={};busy={'value':False};buttons=[]
        if last_audio and not context.get('audio'):
            context.update(audio=last_audio[0]['ruta'],transcripcion_original=last_audio[0]['transcripcion_original'])

        def set_buttons():
            recording=recorder.stream is not None
            record.configure(state='disabled' if busy['value'] or recording else 'normal')
            stop.configure(state='normal' if recording and not busy['value'] else 'disabled')
            generate.configure(state='disabled' if busy['value'] or recording else 'normal')
            apply.configure(state='normal' if result and not busy['value'] and not recording else 'disabled')

        def run(task,done):
            if busy['value']:return
            busy['value']=True;set_buttons();mail=queue.Queue()
            def work():
                try:mail.put((True,task()))
                except Exception as exc:mail.put((False,str(exc)))
            threading.Thread(target=work,daemon=True).start()
            def poll():
                if not top.winfo_exists():return
                try:ok,value=mail.get_nowait()
                except queue.Empty:self.after(100,poll);return
                busy['value']=False;set_buttons()
                if ok:
                    try:done(value)
                    except Exception as exc:status.set(str(exc))
                else:status.set(value)
            self.after(100,poll)

        def start():
            try:recorder.start(tid)
            except Exception as exc:status.set(f'No se pudo grabar: {exc}');return
            status.set('Grabando con el micrófono · máximo 5 minutos. Pulsa Detener y transcribir al terminar.');set_buttons()

        def stop_recording():
            try:path=recorder.stop()
            except Exception as exc:status.set(str(exc));set_buttons();return
            context['audio']=str(path)
            status.set('Audio guardado. Transcribiendo localmente… Puede tardar unos segundos.')
            def done(text):
                register_transcription(tid,self.session,path,text)
                context['transcripcion_original']=text
                source.delete('1.0','end');source.insert('1.0',text);result.clear();set_buttons()
                status.set('Transcripción lista. Corrige lo necesario antes de extraer. El audio y el texto original se conservan.')
            run(lambda:ai.transcribe(path),done)

        def generate_report():
            snapshot=source.get('1.0','end').strip()
            if not snapshot:status.set('Graba o escribe una narración primero.');return
            result.clear();status.set('Extrayendo con Qwen3 4B en este equipo…');set_buttons()
            def done(data):
                if source.get('1.0','end').strip()!=snapshot:
                    status.set('La narración cambió durante el análisis. Vuelve a extraer.');return
                result.update(data=data,source=snapshot)
                preview.configure(state='normal');preview.delete('1.0','end');preview.insert('1.0',ai.render_draft(data));preview.configure(state='disabled')
                status.set('Extracción lista. Revisa la propuesta y pulsa Usar como borrador.');set_buttons()
            run(lambda:ai.extract(snapshot),done)

        def use():
            if not result or source.get('1.0','end').strip()!=result['source']:
                status.set('La fuente cambió. Extrae de nuevo antes de usar el resultado.');return
            if report.get('1.0','end').strip() and not messagebox.askyesno('Reemplazar borrador','¿Reemplazar el texto del editor con esta propuesta? Guarda antes el borrador actual si quieres conservar su versión.',parent=top):return
            report.delete('1.0','end');report.insert('1.0',ai.render_draft(result['data']))
            metadata.update(context,fuente=result['source'],extraccion=result['data'],modelo='Qwen3-4B-Q4_K_M')
            top.destroy();self.status.set('Propuesta aplicada al editor. Revísala y guarda el borrador.')

        record=self.button(bar,'Grabar micrófono',start,True);record.pack(side='left',padx=(0,8))
        stop=self.button(bar,'Detener y transcribir',stop_recording);stop.pack(side='left')
        generate=self.button(tools,'Extraer con Qwen3 4B',generate_report,True);generate.pack(side='left')
        apply=self.button(w,'Usar como borrador',use,True);apply.pack(pady=6);set_buttons()
        tk.Label(w,text='La extracción conserva citas de tu narración. Los datos no mencionados quedan como No informado. El borrador todavía requiere tu revisión.',bg='white',fg='#59697f',wraplength=620,justify='left').pack(padx=18,pady=10)
        def close(event):
            if event.widget==top and recorder.stream is not None:
                try:recorder.stop()
                except Exception:pass
        top.bind('<Destroy>',close,add='+')

    def preview_submission(self,tid,report,evidence,metadata,editor):
        body=report.get('1.0','end').strip()
        if len(body)<20:messagebox.showwarning('Borrador incompleto','Describe actividades, pruebas y resultados (mínimo 20 caracteres).');return
        # Guardar primero: cancelar la vista previa no pierde lo que escribió el técnico.
        if not self.attempt(lambda:save_draft(tid,self.session,body,evidence.get(),metadata)):return
        w=self.dialog('Vista previa · pendiente de envío')
        self.titleline(w,'Revisa tu borrador','Aún no lo has enviado. Puedes volver para corregirlo; solo Confirmar envío lo pasa a validación.')
        text=self.textfield(w,'Reporte que verá el supervisor',16);text.insert('1.0',body);text.configure(state='disabled')
        tk.Label(w,text='Evidencia: '+(evidence.get() or 'Sin evidencia adjunta'),bg='white',wraplength=600).pack(padx=18,pady=8)
        def send():
            if not self.attempt(lambda:transition(tid,self.session,'Enviar reporte',body,evidence.get())):return
            w.winfo_toplevel().destroy();editor.winfo_toplevel().destroy();self.refresh()
            self.status.set('Reporte enviado a supervisión. El supervisor revisará el cierre.')
        self.button(w,'Confirmar envío a supervisión',send,True).pack(pady=10)
        self.button(w,'Volver y corregir',w.winfo_toplevel().destroy).pack(pady=6)

    def draft_history(self,tid):
        read_ticket(tid,self.session)
        w=self.dialog('Versiones del borrador')
        text=self.textfield(w,'Borradores guardados y versiones enviadas',24)
        for row in query('SELECT * FROM borradores WHERE ticket_id=? ORDER BY revision DESC',(tid,)):
            text.insert('end',f"Revisión {row['revision']} · {row['estado']} · {row['actor']} · {row['fecha']}\n{row['contenido']}\n\nFuente revisada: {row['fuente']}\nTranscripción original: {row['transcripcion_original']}\nAudio: {row['audio']}\nModelo: {row['modelo']}\n\n")
        text.configure(state='disabled')
