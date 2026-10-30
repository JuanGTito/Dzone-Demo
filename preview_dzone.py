"""Vista de comprobación con datos temporales; no usa la base del usuario."""
import tempfile
from pathlib import Path
import dzone_core as core
import dzone_services as services
from dzone import App
from dzone_auth import authenticate

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='dzone_preview_',dir=Path(__file__).parent) as folder:
        core.BASE=Path(folder);core.DB=core.BASE/'preview.db'
        services.init_db()
        supervisor=authenticate('demo0','demo0');technician=authenticate('demo1','demo1')
        services.load_demo_tickets(supervisor)
        services.transition(1,technician,'Iniciar')
        services.transition(1,technician,'Enviar reporte','Se ajustó la válvula de alimentación y se realizó prueba de estanqueidad. No se observaron fugas durante la prueba.')
        person=core.query('SELECT tecnico FROM tickets WHERE id=2')[0]['tecnico']
        services.transition(2,authenticate(person,person),'Iniciar')
        services.create_finding('demo1','VAL-102','Desgaste observado en la válvula auxiliar. Se propone inspección.',technician)
        app=App();app.login('demo0','demo0');app.title('Dzone | Vista de comprobación · datos temporales');app.mainloop()
