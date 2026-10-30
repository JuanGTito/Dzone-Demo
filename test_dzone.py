from dzone_auth import authenticate
"""Pruebas de reglas con SQLite temporal: no modifica datos del usuario."""
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta
import dzone_core as core
import dzone_services as services

class WorkflowTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.old_base, self.old_db = (core.BASE, core.DB)
        core.BASE = Path(self.tmp.name)
        core.DB = core.BASE / 'test.db'
        services.init_db(seed_demo=True)
        self.supervisor = authenticate('demo0', 'demo0')
        self.tech1 = authenticate('demo1', 'demo1')
        self.tech2 = authenticate('demo2', 'demo2')
        self.tech3 = authenticate('demo3', 'demo3')
        self.tech4 = authenticate('demo4', 'demo4')

    def tearDown(self):
        core.BASE, core.DB = (self.old_base, self.old_db)
        self.tmp.cleanup()

    def submitted(self):
        services.assign_ticket(1, 'demo1', self.supervisor)
        services.transition(1, self.tech1, 'Iniciar')
        services.transition(1, self.tech1, 'Enviar reporte', 'Válvula ajustada y prueba de estanqueidad realizada.')

    def fake_pdf(self, row, temporary=False):
        folder = core.BASE / 'reportes'
        folder.mkdir(exist_ok=True)
        path = folder / 'staged.pdf'
        path.write_bytes(b'%PDF-test')
        return path

    def test_assignment_respects_date_and_skill(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        core.update('UPDATE tickets SET fecha_programada=? WHERE id=1', (future,))
        with self.assertRaises(ValueError):
            services.assign_ticket(1, 'demo1', self.supervisor)
        with self.assertRaises(ValueError):
            services.assign_ticket(3, 'demo4', self.supervisor)
        assignments = services.assignment(self.supervisor)
        self.assertNotIn(1, [tid for tid, _ in assignments])
        self.assertEqual(core.query('SELECT tecnico FROM tickets WHERE id=3')[0]['tecnico'], 'demo2')

    def test_failed_pdf_does_not_close_or_create_preventive(self):
        self.submitted()

        def fail(*args, **kwargs):
            raise OSError('Disco lleno')
        with self.assertRaises(OSError):
            services.close_ticket(1, self.supervisor, 15, fail)
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=1')[0]['estado'], 'En validacion')
        self.assertFalse(core.query('SELECT * FROM tickets WHERE padre=1'))

    def test_close_with_authorized_preventive_is_persistent(self):
        self.submitted()
        pdf = services.close_ticket(1, self.supervisor, 5, self.fake_pdf)
        self.assertTrue(pdf.exists())
        child = core.query('SELECT * FROM tickets WHERE padre=1')[0]
        self.assertEqual(child['fecha_creacion'], date.today().isoformat())
        self.assertGreater(child['fecha_programada'], child['fecha_creacion'])
        self.assertNotIn(child['id'], [tid for tid, _ in services.assignment(self.supervisor)])
        with self.assertRaises(ValueError):
            services.close_ticket(1, self.supervisor, 5, self.fake_pdf)
        services.init_db(seed_demo=True)
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=1')[0]['estado'], 'Terminado')

    def test_default_close_does_not_create_preventive(self):
        self.submitted()
        services.close_ticket(1, self.supervisor, pdf_writer=self.fake_pdf)
        self.assertFalse(core.query('SELECT * FROM tickets WHERE padre=1'))

    def test_correction_requires_reason_and_preserves_report_history(self):
        self.submitted()
        with self.assertRaises(ValueError):
            services.transition(1, self.supervisor, 'Solicitar corrección')
        services.transition(1, self.supervisor, 'Solicitar corrección', reason='Falta resultado de la prueba')
        events = core.query("SELECT * FROM eventos WHERE referencia=1 AND entidad='ticket'")
        self.assertTrue(any(('Válvula ajustada' in e['detalle'] for e in events)))
        self.assertEqual(events[-1]['detalle'], 'Falta resultado de la prueba')

    def test_finding_review_is_atomic_and_links_ticket(self):
        hid = core.update('INSERT INTO hallazgos(tecnico,equipo,texto,prioridad_sugerida,fecha) VALUES(?,?,?,?,?)', ('demo1', 'VAL-1', 'Fuga detectada', 'Alta', date.today().isoformat()))
        with self.assertRaises(ValueError):
            services.review_finding(hid, False, self.supervisor)
        tid = services.review_finding(hid, True, self.supervisor, priority='Media', skill='Mecanica')
        self.assertEqual(core.query('SELECT ticket_id FROM hallazgos WHERE id=?', (hid,))[0]['ticket_id'], tid)
        with self.assertRaises(ValueError):
            services.review_finding(hid, True, self.supervisor)

    def test_migration_keeps_existing_preventive_schedule(self):
        core.update("UPDATE tickets SET tipo='Preventivo',fecha_programada='',fecha_creacion='2030-01-01' WHERE id=2")
        services.init_db(seed_demo=True)
        self.assertEqual(core.query('SELECT fecha_programada FROM tickets WHERE id=2')[0]['fecha_programada'], '2030-01-01')

    def test_real_pdf(self):
        self.submitted()
        pdf = services.close_ticket(1, self.supervisor)
        self.assertTrue(pdf.read_bytes().startswith(b'%PDF'))

    def test_database_failure_rolls_back_close_and_removes_staged_pdf(self):
        self.submitted()
        with core.conn() as c:
            c.execute("CREATE TRIGGER reject_preventive BEFORE INSERT ON tickets\n                WHEN NEW.tipo='Preventivo' BEGIN SELECT RAISE(ABORT,'Error simulado'); END")
        with self.assertRaises(core.sqlite3.Error):
            services.close_ticket(1, self.supervisor, 5, self.fake_pdf)
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=1')[0]['estado'], 'En validacion')
        self.assertFalse((core.BASE / 'reportes' / 'staged.pdf').exists())

    def test_legacy_database_migration(self):
        core.DB = core.BASE / 'legacy.db'
        core.init_db(seed_demo=True)
        core.update("UPDATE tickets SET tipo='Preventivo',fecha_creacion='2030-01-01' WHERE id=1")
        services.init_db(seed_demo=True)
        services.init_db(seed_demo=True)
        self.assertEqual(len(core.query('SELECT * FROM tickets')), 5)
        self.assertEqual(core.query('SELECT fecha_programada FROM tickets WHERE id=1')[0]['fecha_programada'], '2030-01-01')
if __name__ == '__main__':
    unittest.main()
