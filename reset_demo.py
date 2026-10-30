"""Reinicio explícito de datos de prueba con respaldo recuperable."""
from datetime import datetime
from pathlib import Path
import json
import shutil
import sqlite3
import sys
from contextlib import closing
import dzone_core as core
import dzone_services as services
from dzone_auth import invalidate_all


def reset_demo(backup_root):
    base=core.BASE.resolve();database=core.DB.resolve()
    if database.parent!=base or database.name not in ('dzone.db','test.db'):
        raise ValueError('La base no es una base de Dzone dentro de su carpeta de datos.')
    backup_root=Path(backup_root).resolve()
    if backup_root==base or backup_root.is_relative_to(base):raise ValueError('El respaldo debe quedar fuera de la carpeta que se reinicia.')
    backup=backup_root/datetime.now().strftime('%Y%m%d_%H%M%S_%f');backup.mkdir(parents=True)
    if database.exists():
        with closing(sqlite3.connect(database)) as source,closing(sqlite3.connect(backup/database.name)) as destination:source.backup(destination)
    for name in ('ia.json','errores.log','motor_ia.log'):
        path=base/name
        if path.is_file() and path.resolve().parent==base:shutil.copy2(path,backup/name)
    services.init_db()
    with core.conn() as c:
        c.execute('BEGIN EXCLUSIVE')
        for table in ('eventos','grabaciones','borradores','hallazgos','tickets','usuarios'):
            c.execute('DELETE FROM '+table)
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('tickets','hallazgos')")
    for name in ('audio','reportes'):
        source=base/name;target=backup/name
        if source.exists():
            if source.resolve().parent!=base or source.is_symlink():raise ValueError('Carpeta de datos fuera de la ubicación esperada: '+name)
            if target.resolve().parent!=backup.resolve():raise ValueError('Destino de respaldo inválido.')
            shutil.move(str(source),str(target))
    invalidate_all();services.init_db()
    result={'respaldo':str(backup),'tickets':len(core.query('SELECT id FROM tickets')),
            'hallazgos':len(core.query('SELECT id FROM hallazgos')),'usuarios':len(core.query('SELECT username FROM usuarios'))}
    (backup/'REINICIO.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:]!=['--reiniciar']:
        raise SystemExit('Uso explícito: python reset_demo.py --reiniciar. Cierra Dzone antes de ejecutarlo.')
    print(json.dumps(reset_demo(Path(__file__).resolve().parent/'.respaldos_demo'),ensure_ascii=False,indent=2))
