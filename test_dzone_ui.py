from dzone_auth import authenticate
"""Regresiones de ventanas Tkinter usando una base temporal aislada."""
import tempfile
import unittest
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
import dzone_core as core
import dzone_services as services
from dzone import App
from tkinter import ttk
from dzone_views import NAV

class WindowTests(unittest.TestCase):

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
        self.errors = []
        self.handler = patch.object(App, 'callback_error', lambda app, kind, error, tb: self.errors.append(error))
        self.handler.start()
        self.app = App()
        self.app.withdraw()
        self.app.login('demo0', 'demo0')
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.handler.stop()
        core.BASE, core.DB = (self.old_base, self.old_db)
        self.tmp.cleanup()
        self.assertEqual(self.errors, [])

    def descendants(self, parent):
        for child in parent.winfo_children():
            yield child
            yield from self.descendants(child)

    def test_refresh_and_identity_do_not_destroy_root(self):
        for _ in range(3):
            self.app.refresh()
            self.app.update()
        self.assertTrue(self.app.winfo_exists())
        for name in NAV:
            self.app.navigate(name)
            self.app.update()
            self.assertTrue(self.app.panes[name].winfo_children(), name)
        self.app.logout()
        self.app.login('demo2', 'demo2')
        self.app.update()
        self.assertEqual(self.app.current_view, 'Mi jornada')
        self.app.logout()
        self.app.login('demo0', 'demo0')
        self.app.update()
        self.assertEqual(self.app.current_view, 'Inicio')

    def test_ticket_search_and_filters(self):
        self.app.search.set('TK-001')
        self.app.tickets()
        self.app.update()
        table = next((w for w in self.descendants(self.app.panes['Tickets']) if isinstance(w, ttk.Treeview)))
        self.assertEqual(len(table.get_children()), 1)
        self.app.state_filter.set('Terminado')
        self.app.tickets()
        self.app.update()
        table = next((w for w in self.descendants(self.app.panes['Tickets']) if isinstance(w, ttk.Treeview)))
        self.assertEqual(len(table.get_children()), 0)
        self.app.reset_filters()
        self.app.update()

    def test_login_rejects_bad_password_and_logout_requires_login_again(self):
        from dzone_auth import require
        old=self.app.session
        self.app.logout();self.app.update()
        self.assertIsNone(self.app.session)
        with self.assertRaises(ValueError):require(old)
        self.assertFalse(self.app.login('demo0','incorrecta'))
        self.assertIsNone(self.app.session)
        self.assertTrue(self.app.login_error.get())
        self.assertTrue(self.app.login('demo1','demo1'));self.app.update()
        self.assertNotIn('Validaciones',self.app.nav_buttons)
        self.assertNotIn('Indicadores',self.app.nav_buttons)
        self.app.navigate('Validaciones')
        self.assertEqual(self.app.current_view,'Mi jornada')

    def test_technician_tables_only_show_their_assignments(self):
        services.assignment(self.supervisor)
        self.app.logout();self.app.login('demo1','demo1');self.app.update()
        self.app.navigate('Tickets')
        table=next(w for w in self.descendants(self.app.panes['Tickets']) if isinstance(w,ttk.Treeview))
        self.assertTrue(table.get_children())
        for row in table.get_children():self.assertEqual(table.item(row,'values')[4],'demo1')
        foreign=core.query("SELECT id FROM tickets WHERE tecnico='demo2'")[0]['id']
        with patch('dzone.messagebox.showerror') as error:
            self.app.open_ticket(foreign);error.assert_called_once()
        self.assertFalse([w for w in self.app.winfo_children() if w.winfo_class()=='Toplevel'])

    def test_page_scrolls_from_outside_table_without_bars_or_idle_movement(self):
        import time
        services.load_demo_tickets(self.supervisor)
        self.app.refresh();self.app.navigate('Tickets');self.app.deiconify();self.app.update()
        page=self.app.pages['Tickets']
        self.assertGreater(page.content.winfo_height(),page.canvas.winfo_height())
        label=next(w for w in self.app.panes['Tickets'].winfo_children() if isinstance(w,tk.Label))
        before=page.canvas.canvasy(0)
        label.event_generate('<MouseWheel>',delta=-120)
        deadline=time.monotonic()+2
        while page.animation is not None and time.monotonic()<deadline:
            self.app.update();time.sleep(.02)
        self.assertIsNone(page.animation)
        after=page.canvas.canvasy(0);self.assertGreater(after,before)
        time.sleep(.08);self.app.update();self.assertEqual(page.canvas.canvasy(0),after)
        label.event_generate('<MouseWheel>',delta=120)
        deadline=time.monotonic()+2
        while page.animation is not None and time.monotonic()<deadline:
            self.app.update();time.sleep(.02)
        self.assertLess(page.canvas.canvasy(0),after)
        self.assertFalse([w for w in self.descendants(self.app) if isinstance(w,ttk.Scrollbar)])

    def test_ia_configuration_is_only_in_supervisor_menu(self):
        self.assertIn('IA y voz',self.app.nav_buttons)
        self.app.logout();self.app.login('demo1','demo1');self.app.update()
        self.assertNotIn('IA y voz',self.app.nav_buttons)

    def test_dialogs_use_wheel_and_keep_close_button_outside_page(self):
        from dzone_widgets import PageScroller
        self.app.new_ticket();self.app.update()
        window=next(w for w in self.app.winfo_children() if w.winfo_class()=='Toplevel')
        pages=[w for w in self.descendants(window) if isinstance(w,PageScroller)]
        self.assertEqual(len(pages),1)
        self.assertFalse([w for w in self.descendants(window) if isinstance(w,ttk.Scrollbar)])
        close=next(w for w in self.descendants(window) if isinstance(w,tk.Button) and w.cget('text')=='Cerrar ventana')
        self.assertIsNone(self.app.wheel.find(close))
        window.destroy()

    def test_technician_cannot_create_ticket_or_choose_hallazgo_author(self):
        self.app.logout();self.app.login('demo1','demo1');self.app.update()
        self.app.new_ticket()
        self.assertFalse([w for w in self.app.winfo_children() if w.winfo_class()=='Toplevel'])
        self.app.new_finding();self.app.update()
        window=next(w for w in self.app.winfo_children() if w.winfo_class()=='Toplevel')
        self.assertFalse([w for w in self.descendants(window) if isinstance(w,ttk.Combobox)])
        window.destroy()

    def test_open_ticket_for_every_operational_state(self):
        for state in core.STATES:
            core.update('UPDATE tickets SET estado=?,tecnico=?,informe=? WHERE id=1', (state, 'demo1', 'Informe de prueba con actividades y resultados.'))
            self.app.refresh()
            self.app.open_ticket(1)
            self.app.update()
            windows = [w for w in self.app.winfo_children() if w.winfo_class() == 'Toplevel']
            self.assertEqual(len(windows), 1)
            windows[0].destroy()
            self.app.update()
        self.assertTrue(self.app.winfo_exists())

    def test_finding_forms_and_empty_views(self):
        self.app.new_ticket()
        self.app.update()
        for w in self.app.winfo_children():
            if w.winfo_class() == 'Toplevel':
                w.destroy()
        self.app.new_finding()
        self.app.update()
        for w in self.app.winfo_children():
            if w.winfo_class() == 'Toplevel':
                w.destroy()
        hid = services.create_finding('demo1', 'VAL-1', 'Fuga en válvula auxiliar', self.tech1)
        self.app.review_finding(hid, True)
        self.app.update()
        for w in self.app.winfo_children():
            if w.winfo_class() == 'Toplevel':
                w.destroy()
        self.app.finding_detail(hid)
        self.app.update()
        for w in self.app.winfo_children():
            if w.winfo_class() == 'Toplevel':
                w.destroy()
        self.app.refresh()
        self.app.update()

    def test_buttons_complete_create_assign_work_validate_pdf_flow(self):

        def dialog():
            return next((w for w in self.app.winfo_children() if w.winfo_class() == 'Toplevel'))

        def press(label):
            button = next((w for w in self.descendants(self.app) if isinstance(w, tk.Button) and w.cget('text') == label))
            button.invoke()
            self.app.update()
        with patch('dzone.messagebox.showinfo'), patch('dzone.messagebox.showerror') as error:
            self.app.new_ticket()
            self.app.update()
            entries = [w for w in self.descendants(dialog()) if isinstance(w, ttk.Entry) and (not isinstance(w, ttk.Combobox))]
            entries[0].insert(0, 'Prueba de flujo desde botones')
            entries[1].insert(0, 'DEMO-UI')
            press('Guardar ticket')
            tid = core.query("SELECT id FROM tickets WHERE equipo='DEMO-UI'")[0]['id']
            self.app.open_ticket(tid)
            self.app.update()
            press('Guardar asignacion')
            assigned = core.query('SELECT tecnico FROM tickets WHERE id=?', (tid,))[0]['tecnico']
            self.app.logout()
            self.app.login(assigned, assigned)
            self.app.update()
            self.app.open_ticket(tid)
            self.app.update()
            press('Iniciar trabajo')
            self.app.open_ticket(tid)
            self.app.update()
            report = next((w for w in self.descendants(dialog()) if isinstance(w, tk.Text)))
            report.insert('1.0', 'Se inspeccionó el equipo y se documentaron los resultados de la prueba.')
            press('Enviar reporte a validacion')
            self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=?', (tid,))[0]['estado'], 'En proceso')
            press('Confirmar envío a supervisión')
            self.app.logout()
            self.app.login('demo0', 'demo0')
            self.app.update()
            self.app.open_ticket(tid)
            self.app.update()
            press('Validar, cerrar y generar PDF')
            self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=?', (tid,))[0]['estado'], 'Terminado')
            self.assertTrue((core.BASE / 'reportes' / f'TK-{tid:03d}.pdf').is_file())
            self.assertTrue(self.app.winfo_exists())
            error.assert_not_called()

    def test_local_extraction_remains_editable_draft_until_confirmed(self):
        import time
        import dzone_ai as ai
        from dzone_services import assign_ticket, transition
        assign_ticket(1, 'demo1', self.supervisor)
        transition(1, self.tech1, 'Iniciar')
        self.app.logout()
        self.app.login('demo1', 'demo1')
        self.app.update()
        self.app.open_ticket(1)
        self.app.update()
        editor = next((w for w in self.app.winfo_children() if w.winfo_class() == 'Toplevel'))
        button = next((w for w in self.descendants(editor) if isinstance(w, tk.Button) and w.cget('text') == 'Generar desde voz o texto'))
        button.invoke()
        self.app.update()
        voice = next((w for w in self.app.winfo_children() if w.winfo_class() == 'Toplevel' and w != editor))
        text = next((w for w in self.descendants(voice) if isinstance(w, tk.Text)))
        text.insert('1.0', 'Se ajustó la válvula.')
        data = {key: [] for key in ai.FIELDS}
        data['actividades'] = ['Se ajustó la válvula.']
        with patch('dzone_ai.extract', return_value=data):
            next((w for w in self.descendants(voice) if isinstance(w, tk.Button) and w.cget('text') == 'Extraer con Qwen3 4B')).invoke()
            use = next((w for w in self.descendants(voice) if isinstance(w, tk.Button) and w.cget('text') == 'Usar como borrador'))
            deadline = time.monotonic() + 3
            while use.cget('state') == 'disabled' and time.monotonic() < deadline:
                self.app.update()
                time.sleep(0.02)
            self.assertEqual(use.cget('state'), 'normal')
            use.invoke()
            self.app.update()
        with patch('dzone.messagebox.showinfo'):
            next((w for w in self.descendants(editor) if isinstance(w, tk.Button) and w.cget('text') == 'Guardar borrador')).invoke()
            self.app.update()
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=1')[0]['estado'], 'En proceso')
        self.assertIn('Se ajustó la válvula.', core.query('SELECT informe FROM tickets WHERE id=1')[0]['informe'])
        for child in self.app.winfo_children():
            if child.winfo_class() == 'Toplevel':
                child.destroy()
if __name__ == '__main__':
    unittest.main()
