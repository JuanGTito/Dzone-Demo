from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import dzone_core as core
import dzone_services as service
from dzone_auth import authenticate,require,revoke
from reset_demo import reset_demo


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.original=core.BASE,core.DB
        core.BASE=Path(self.tmp.name)/'datos';core.DB=core.BASE/'test.db'
        service.init_db()
        self.supervisor=authenticate('demo0','demo0')
        self.tech1=authenticate('demo1','demo1');self.tech2=authenticate('demo2','demo2')

    def tearDown(self):
        core.BASE,core.DB=self.original;self.tmp.cleanup()

    def test_fresh_database_has_only_five_users_and_no_tickets(self):
        self.assertEqual(len(core.query('SELECT * FROM usuarios')),5)
        self.assertFalse(core.query('SELECT * FROM tickets'))
        for i in range(5):
            s=authenticate(f'demo{i}',f'demo{i}')
            self.assertEqual(s.role,'Supervisor' if i==0 else 'Tecnico')
        row=core.query("SELECT * FROM usuarios WHERE username='demo0'")[0]
        self.assertNotEqual(row['password_hash'],'demo0')

    def test_bad_credentials_and_forged_or_revoked_session_are_rejected(self):
        for user,password in [('demo0','demo1'),('demo9','demo9'),('','')]:
            with self.assertRaises(ValueError):authenticate(user,password)
        with self.assertRaises(ValueError):require(replace(self.tech1,role='Supervisor'))
        with self.assertRaises(ValueError):require('demo0')
        revoke(self.tech1)
        with self.assertRaises(ValueError):require(self.tech1)

    def test_technician_can_neither_create_assign_review_nor_close(self):
        tid=service.create_ticket('Válvula','VAL-1','Mecanica','Alta','Revisar válvula',self.supervisor)
        service.assign_ticket(tid,'demo1',self.supervisor)
        for action in (
            lambda:service.create_ticket('Otro','EQ','General','Media','',self.tech1),
            lambda:service.assignment(self.tech1),
            lambda:service.assign_ticket(tid,'demo2',self.tech1),
            lambda:service.review_finding(1,True,self.tech1),
            lambda:service.close_ticket(tid,self.tech1),
            lambda:service.transition(tid,self.tech1,'Solicitar corrección',reason='No'),
        ):
            with self.assertRaises(ValueError):action()

    def test_assignment_views_and_work_are_scoped_to_owner(self):
        tid=service.create_ticket('Válvula','VAL-1','Mecanica','Alta','Revisar válvula',self.supervisor)
        service.assignment(self.supervisor)
        self.assertEqual([r['id'] for r in service.visible_tickets(self.tech1)],[tid])
        self.assertFalse(service.visible_tickets(self.tech2))
        with self.assertRaises(ValueError):service.read_ticket(tid,self.tech2)
        with self.assertRaises(ValueError):service.transition(tid,self.tech2,'Iniciar')
        with self.assertRaises(ValueError):service.transition(tid,self.supervisor,'Iniciar')
        service.transition(tid,self.tech1,'Iniciar')
        with self.assertRaises(ValueError):service.save_draft(tid,self.tech2,'No es mi reporte')
        service.save_draft(tid,self.tech1,'Mi borrador editable del trabajo realizado.')
        service.transition(tid,self.tech1,'Enviar reporte','Mi borrador editable del trabajo realizado.')
        service.transition(tid,self.supervisor,'Solicitar corrección',reason='Agrega la prueba')
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=?',(tid,))[0][0],'En proceso')

    def test_findings_are_scoped_and_cannot_impersonate_another_user(self):
        hid=service.create_finding('demo1','VAL','Desgaste observado',self.tech1)
        self.assertEqual(len(service.visible_findings(self.tech1)),1)
        self.assertFalse(service.visible_findings(self.tech2))
        with self.assertRaises(ValueError):service.read_finding(hid,self.tech2)
        with self.assertRaises(ValueError):service.create_finding('demo2','VAL','Otro hallazgo',self.tech1)
        service.review_finding(hid,True,self.supervisor,skill='Mecanica')

    def test_reset_backs_up_database_and_files_and_does_not_reseed_tickets(self):
        service.create_ticket('Viejo','EQ','General','Alta','',self.supervisor)
        (core.BASE/'reportes').mkdir();(core.BASE/'reportes'/'viejo.pdf').write_bytes(b'PDF')
        result=reset_demo(Path(self.tmp.name)/'respaldos')
        self.assertEqual(result['tickets'],0);self.assertEqual(result['usuarios'],5)
        self.assertTrue((Path(result['respaldo'])/'test.db').is_file())
        self.assertTrue((Path(result['respaldo'])/'reportes'/'viejo.pdf').is_file())
        self.assertFalse((core.BASE/'reportes').exists())
        service.init_db();self.assertFalse(core.query('SELECT * FROM tickets'))
        with self.assertRaises(ValueError):require(self.supervisor)
        authenticate('demo0','demo0')

    def test_examples_are_ready_idempotent_and_preserve_other_pending_work(self):
        personal=service.create_ticket('Trabajo existente','EQ-ORIGINAL','General','Alta','No modificar',self.supervisor)
        result=service.load_demo_tickets(self.supervisor)
        self.assertEqual(result['creados'],12);self.assertEqual(result['asignados'],12)
        fixtures=[r for r in service.visible_tickets(self.supervisor) if r['id'] in result['tickets']]
        self.assertEqual({r['tecnico'] for r in fixtures},{'demo1','demo2','demo3','demo4'})
        self.assertTrue(all(r['estado']=='Asignado' for r in fixtures))
        self.assertEqual(service.read_ticket(personal,self.supervisor)['estado'],'Pendiente')
        again=service.load_demo_tickets(self.supervisor)
        self.assertEqual(again['creados'],0);self.assertEqual(again['asignados'],0)
        self.assertEqual(len(service.visible_tickets(self.supervisor)),13)
        with self.assertRaises(ValueError):service.load_demo_tickets(self.tech1)


if __name__=='__main__':unittest.main()
