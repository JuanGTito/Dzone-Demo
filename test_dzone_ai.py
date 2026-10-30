from dzone_auth import authenticate
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import dzone_core as core
import dzone_services as service
import dzone_ai as ai

class DraftTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.old_base, self.old_db = (core.BASE, core.DB)
        core.BASE = Path(self.tmp.name)
        core.DB = core.BASE / 'test.db'
        service.init_db(seed_demo=True)
        self.supervisor = authenticate('demo0', 'demo0')
        self.tech1 = authenticate('demo1', 'demo1')
        self.tech2 = authenticate('demo2', 'demo2')
        self.tech3 = authenticate('demo3', 'demo3')
        self.tech4 = authenticate('demo4', 'demo4')
        service.assign_ticket(1, 'demo1', self.supervisor)
        service.transition(1, self.tech1, 'Iniciar')

    def tearDown(self):
        core.BASE, core.DB = (self.old_base, self.old_db)
        self.tmp.cleanup()

    def test_draft_is_persistent_editable_and_versioned_before_submission(self):
        metadata = {'fuente': 'Se ajustó la válvula.', 'transcripcion_original': 'Se ajusto la valvula.', 'modelo': 'Qwen3-4B-Q4_K_M'}
        service.save_draft(1, self.tech1, 'Borrador preliminar con actividades de mantenimiento.', metadata=metadata)
        service.init_db(seed_demo=True)
        self.assertEqual(core.query('SELECT estado FROM tickets WHERE id=1')[0]['estado'], 'En proceso')
        service.save_draft(1, self.tech1, 'Borrador corregido sin afirmar una prueba no realizada.', metadata=metadata)
        service.transition(1, self.tech1, 'Enviar reporte', 'Borrador corregido sin afirmar una prueba no realizada.')
        rows = core.query('SELECT * FROM borradores WHERE ticket_id=1 ORDER BY revision')
        self.assertEqual([r['estado'] for r in rows], ['Borrador', 'Borrador', 'Enviado'])
        self.assertEqual(rows[-1]['transcripcion_original'], metadata['transcripcion_original'])
        with self.assertRaises(ValueError):
            service.save_draft(1, self.tech1, 'Edición después del envío')

    def test_audio_original_is_not_overwritten(self):
        service.register_transcription(1, self.tech1, 'audio.wav', 'Transcripción original')
        service.register_transcription(1, self.tech1, 'audio.wav', 'Texto modificado')
        self.assertEqual(core.query('SELECT transcripcion_original FROM grabaciones')[0][0], 'Transcripción original')

    def test_only_source_quotes_are_accepted(self):
        data = {field: [] for field in ai.FIELDS}
        data['actividades'] = ['Se ajustó la válvula']
        ai.validate_extraction(data, 'Se ajustó la válvula. Se revisó el filtro.')
        data['resultados'] = ['Presión 10 bar']
        with self.assertRaises(ValueError):
            ai.validate_extraction(data, 'Se ajustó la válvula y se revisó el filtro.')

    def test_cannot_omit_negation_or_planned_work_context(self):
        data = {field: [] for field in ai.FIELDS}
        data['pruebas'] = ['Se midió la presión.']
        with self.assertRaises(ValueError):
            ai.validate_extraction(data, 'No se midió la presión.')
        data['pruebas'] = ['se midió la presión.']
        with self.assertRaises(ValueError):
            ai.validate_extraction(data, 'No se midió la presión.')

    def test_schema_rejects_added_fields_and_wrong_types(self):
        data = {field: [] for field in ai.FIELDS}
        data['estado'] = 'Terminado'
        with self.assertRaises(ValueError):
            ai.validate_extraction(data, 'Fuente')
        del data['estado']
        data['materiales'] = 'Repuesto'
        with self.assertRaises(ValueError):
            ai.validate_extraction(data, 'Fuente')

    def test_missing_models_do_not_attempt_network(self):
        with patch('urllib.request.build_opener') as network:
            with self.assertRaises(ValueError):
                ai.extract('Trabajo realizado', {'motor': 'no.exe', 'modelo': 'no.gguf'})
            network.assert_not_called()

    def test_empty_fields_are_marked_not_informed(self):
        result = ai.render_draft({field: [] for field in ai.FIELDS})
        self.assertEqual(result.count('No informado'), 6)

    def test_model_only_selects_original_sentences(self):
        units = ai.source_units('No se midió presión. Se cambió la junta.')
        categories = {field: [] for field in ai.FIELDS}
        categories['observaciones'] = [0]
        self.assertEqual(ai.resolve_categories(categories, units)['observaciones'], ['No se midió presión.'])
        categories['observaciones'] = [999]
        with self.assertRaises(ValueError):
            ai.resolve_categories(categories, units)

    def test_dictated_clauses_keep_negations_and_material_lists(self):
        units = ai.source_units('Se ajustó la válvula, se cambió la junta, no se midió presión.')
        self.assertEqual(units, ['Se ajustó la válvula', 'se cambió la junta', 'no se midió presión.'])
        self.assertEqual(len(ai.source_units('No se midió presión, ni se hizo una prueba.')), 1)
        self.assertEqual(len(ai.source_units('Se usaron juntas, tornillos y cinta.')), 1)

    def test_transcription_uses_only_local_files(self):
        directory = core.BASE / 'voz'
        directory.mkdir()
        (directory / 'model.bin').touch()
        engine = MagicMock()
        engine.return_value.transcribe.return_value = ([MagicMock(text='Se revisó el filtro.')], None)
        with patch.dict('sys.modules', {'faster_whisper': MagicMock(WhisperModel=engine)}):
            text = ai.transcribe('audio.wav', {'voz': str(directory)})
        self.assertEqual(text, 'Se revisó el filtro.')
        self.assertTrue(engine.call_args.kwargs['local_files_only'])
if __name__ == '__main__':
    unittest.main()
