"""Comprobación reproducible del paquete sin usar la base ni micrófono reales."""
import json
from pathlib import Path
import tempfile
import time
import dzone_core as core
import dzone_services as service
import dzone_ai as ai
from dzone_auth import authenticate


def verify(output,app_class=None):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    previous_base,previous_db=core.BASE,core.DB
    result={}
    try:
        with tempfile.TemporaryDirectory(dir=output.parent,prefix='verificar_dzone_') as folder:
            core.BASE=Path(folder);core.DB=core.BASE/'test.db';service.init_db(seed_demo=True)
            supervisor=authenticate('demo0','demo0');technician=authenticate('demo1','demo1')
            cfg={'motor':str(ai.ASSETS/'runtime'/'llama'/'llama-server.exe'),
                 'modelo':str(ai.ASSETS/'models'/'Qwen3-4B-Q4_K_M.gguf'),'voz':str(ai.ASSETS/'models'/'whisper-tiny')}
            source='Se ajustó la válvula VAL-101. Se cambió la junta de goma. Se hizo una prueba de estanqueidad. No se observaron fugas.'
            sample=ai.ASSETS/'samples'/'prueba_voz_es.wav'
            if sample.exists():
                start=time.monotonic();source=ai.transcribe(sample,cfg)
                result.update(transcripcion_audio_sintetico=source,segundos_voz=round(time.monotonic()-start,2))
            start=time.monotonic();data=ai.extract(source,cfg)
            result.update(extraccion=data,segundos_qwen=round(time.monotonic()-start,2))
            from faster_whisper import WhisperModel
            if not sample.exists():
                model=WhisperModel(cfg['voz'],device='cpu',compute_type='int8',local_files_only=True)
                del model
            result['modelo_voz_cargado']=True
            if app_class is not None:
                app=app_class()
                try:
                    app.withdraw();app.login('demo0','demo0');app.refresh();app.update()
                    app.logout();app.login('demo1','demo1');app.update()
                    result['permisos_tecnico']=('Validaciones' not in app.nav_buttons and 'Indicadores' not in app.nav_buttons)
                    app.logout();app.login('demo0','demo0');app.update()
                    result['interfaz_probada']=bool(app.winfo_exists())
                finally:app.destroy()
            import sounddevice
            result['biblioteca_microfono']=sounddevice.__version__
            service.assign_ticket(1,'demo1',supervisor);service.transition(1,technician,'Iniciar')
            service.save_draft(1,technician,ai.render_draft(data),metadata={'fuente':source,'extraccion':data,'modelo':'Qwen3-4B-Q4_K_M'})
            service.transition(1,technician,'Enviar reporte',ai.render_draft(data))
            path=service.close_ticket(1,supervisor);result['pdf_generado']=path.read_bytes().startswith(b'%PDF')
            result['ok']=True
    except Exception as exc:
        import traceback
        result.update(ok=False,error=str(exc),detalle=traceback.format_exc())
    finally:
        core.BASE,core.DB=previous_base,previous_db
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
