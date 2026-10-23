import copy
import csv
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from pyensemble.importers.definitions import ImportConflict, import_definition
from pyensemble.locking import lock_experiment
from pyensemble.models import (
    DataFormat,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Question,
)
from pyensemble.utils.serializers import (
    ExperimentSerializer,
    FormSerializer,
    QuestionSerializer,
)


def experiment_payload(*, title='Imported study', question_text='Consent?'):
    return {
        'model_class': 'Experiment',
        'title': title,
        'description': 'Study description',
        'irb_id': '',
        'sona_url': '',
        'start_date': None,
        'end_date': None,
        'language': 'en',
        'play_question_audio': False,
        'params': '',
        'locked': True,
        'release_identifier': 'untrusted-release',
        'lock_snapshot': {'untrusted': True},
        'is_group': False,
        'user_ticket_expected': False,
        'session_reporting_script': '',
        'post_session_callback': '',
        'exf_instances': [
            {
                'model_class': 'ExperimentXForm',
                'form_order': 1,
                'form_handler': 'form_generic',
                'goto': None,
                'repeat': None,
                'condition': '',
                'condition_script': '',
                'stimulus_script': '',
                'record_response_script': '',
                'break_loop_button': False,
                'break_loop_button_text': '',
                'continue_button_text': 'Next',
                'use_clientside_validation': False,
                'form': {
                    'model_class': 'Form',
                    'name': 'Consent form',
                    'category': '',
                    'header': '',
                    'footer': '',
                    'header_audio_path': '',
                    'footer_audio_path': '',
                    'version': None,
                    'locked': True,
                    'visit_once': False,
                    'fxq_instances': [
                        {
                            'model_class': 'FormXQuestion',
                            'form_question_num': 1,
                            'question_iteration': 1,
                            'required': True,
                            'question': {
                                'model_class': 'Question',
                                '_unique_hash': 'not-trusted',
                                'text': question_text,
                                'category': '',
                                'value_range': '',
                                'value_default': '',
                                'html_field_type': 'text',
                                'audio_path': '',
                                'locked': True,
                                'data_format': {
                                    'model_class': 'DataFormat',
                                    'df_type': 'text',
                                    'enum_values': None,
                                    '_range_hash': 'not-trusted',
                                    'range_data': None,
                                },
                            },
                        },
                    ],
                },
            },
        ],
    }


class DefinitionImportTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user('definition-importer')
        self.editor.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(self.editor)

    def import_payload(self, payload, **kwargs):
        return import_definition(payload, actor=self.editor, **kwargs)

    def test_create_ignores_uploaded_lock_metadata_and_creates_draft_graph(self):
        result = self.import_payload(
            experiment_payload(),
            mode='create',
        )

        experiment = Experiment.objects.get(pk=result['id'])
        form = Form.objects.get(name='Consent form')
        question = Question.objects.get(text='Consent?')
        data_format = DataFormat.objects.get(df_type='text')
        self.assertEqual(result['action'], 'created')
        self.assertFalse(experiment.locked)
        self.assertFalse(form.locked)
        self.assertFalse(question.locked)
        self.assertEqual(experiment.release_identifier, '')
        self.assertEqual(experiment.title, 'Imported study')
        self.assertIsNone(experiment.lock_snapshot)
        self.assertTrue(
            ExperimentXForm.objects.filter(experiment=experiment, form=form).exists(),
        )
        self.assertTrue(
            FormXQuestion.objects.filter(form=form, question=question).exists(),
        )
        self.assertEqual(question.data_format, data_format)

    def test_create_uses_json_title_and_exact_reimport_is_idempotent(self):
        payload = experiment_payload(title='Imported by title')

        first = self.import_payload(payload, mode='create')
        second = self.import_payload(payload, mode='create')

        self.assertEqual(first['id'], second['id'])
        self.assertEqual(first['action'], 'created')
        self.assertEqual(second['action'], 'already existed')
        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(Form.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 1)

    def test_rename_is_available_only_for_root_identity_conflicts(self):
        self.import_payload(
            experiment_payload(title='Existing example'),
            mode='create',
        )
        changed_payload = experiment_payload(title='Existing example')
        changed_payload['description'] = 'Changed experiment description'

        with self.assertRaises(ImportConflict) as caught:
            self.import_payload(changed_payload, mode='create')

        self.assertTrue(caught.exception.can_rename)

        changed_payload['title'] = 'Renamed example'
        result = self.import_payload(changed_payload, mode='create')

        self.assertEqual(result['label'], 'Renamed example')
        self.assertEqual(Experiment.objects.count(), 2)

    def test_form_import_uses_json_name_and_can_be_renamed_on_conflict(self):
        form_payload = copy.deepcopy(
            experiment_payload()['exf_instances'][0]['form'],
        )
        form_payload['name'] = 'Imported form name'

        first = self.import_payload(form_payload, mode='create')
        second = self.import_payload(form_payload, mode='create')
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(first['action'], 'created')
        self.assertEqual(second['action'], 'already existed')
        self.assertEqual(Form.objects.get(pk=first['id']).name, 'Imported form name')

        changed_payload = copy.deepcopy(form_payload)
        changed_payload['header'] = 'A changed header'
        with self.assertRaises(ImportConflict) as caught:
            self.import_payload(changed_payload, mode='create')
        self.assertTrue(caught.exception.can_rename)

        renamed = self.import_payload(
            changed_payload,
            mode='create',
            new_name='Separate form draft',
        )
        self.assertEqual(renamed['label'], 'Separate form draft')

    def test_nested_form_conflict_does_not_offer_root_rename(self):
        self.import_payload(
            experiment_payload(title='First experiment'),
            mode='create',
        )
        changed_payload = experiment_payload(title='Second experiment')
        changed_payload['exf_instances'][0]['form']['header'] = (
            'Conflicting form content'
        )

        with self.assertRaises(ImportConflict) as caught:
            self.import_payload(changed_payload, mode='create')

        self.assertFalse(caught.exception.can_rename)

    def test_exact_import_reuses_locked_graph_without_duplicates(self):
        payload = experiment_payload()
        imported = self.import_payload(
            payload,
            mode='create',
            new_name='Production import',
        )
        release_manager = get_user_model().objects.create_user('import-release-manager')
        release_manager.groups.add(Group.objects.get(name='Release manager'))
        experiment = Experiment.objects.get(pk=imported['id'])
        lock_experiment(experiment, release_manager, 'Release', 'release-1')
        form = Form.objects.get(name='Consent form')
        question = Question.objects.get(text='Consent?')

        result = self.import_payload(
            payload,
            mode='create',
            new_name='Production import',
        )
        form_payload = payload['exf_instances'][0]['form']
        question_payload = form_payload['fxq_instances'][0]['question']
        imported_form = self.import_payload(
            form_payload,
            mode='create',
            new_name='Consent form',
        )
        imported_question = self.import_payload(
            question_payload,
            mode='create',
        )

        self.assertEqual(result['id'], experiment.pk)
        self.assertEqual(result['action'], 'already existed')
        self.assertEqual(imported_form['id'], form.pk)
        self.assertEqual(imported_question['id'], question.pk)
        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(Form.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 1)
        self.assertEqual(DataFormat.objects.count(), 1)

    def test_mismatched_locked_import_rolls_back_entire_graph(self):
        payload = experiment_payload()
        imported = self.import_payload(
            payload,
            mode='create',
            new_name='Production import',
        )
        release_manager = get_user_model().objects.create_user('import-release-manager')
        release_manager.groups.add(Group.objects.get(name='Release manager'))
        lock_experiment(
            Experiment.objects.get(pk=imported['id']),
            release_manager,
            'Release',
            'release-1',
        )
        changed_payload = experiment_payload(question_text='Changed text?')
        changed_payload['title'] = 'Production import'
        changed_payload['exf_instances'][0]['form']['fxq_instances'][0][
            'question'
        ]['data_format'] = {
            'model_class': 'DataFormat',
            'df_type': 'enum',
            'enum_values': '"Yes","No"',
            'range_data': None,
        }

        with self.assertRaises(ImportConflict):
            self.import_payload(
                changed_payload,
                mode='create',
                new_name='Production import',
            )

        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(Form.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 1)
        self.assertEqual(DataFormat.objects.count(), 1)
        self.assertFalse(Question.objects.filter(text='Changed text?').exists())

    def test_validate_dry_run_leaves_no_rows(self):
        result = self.import_payload(
            experiment_payload(),
            mode='validate',
            new_name='Dry run',
        )

        self.assertTrue(result['dry_run'])
        self.assertFalse(Experiment.objects.exists())
        self.assertFalse(Form.objects.exists())
        self.assertFalse(Question.objects.exists())
        self.assertFalse(DataFormat.objects.exists())

    def test_model_exports_are_accepted_by_lock_aware_importer(self):
        result = self.import_payload(
            experiment_payload(),
            mode='create',
            new_name='Serializer source',
        )
        experiment = Experiment.objects.get(pk=result['id'])
        form = Form.objects.get(name='Consent form')
        question = Question.objects.get(text='Consent?')

        imported_experiment = self.import_payload(
            dict(ExperimentSerializer(experiment).data),
            mode='create',
            new_name='Serializer copy',
        )
        imported_form = self.import_payload(
            dict(FormSerializer(form).data),
            mode='create',
            new_name='Serializer form copy',
        )
        imported_question = self.import_payload(
            dict(QuestionSerializer(question).data),
            mode='create',
        )

        self.assertTrue(
            Experiment.objects.filter(pk=imported_experiment['id']).exists(),
        )
        self.assertTrue(Form.objects.filter(pk=imported_form['id']).exists())
        self.assertEqual(imported_question['id'], question.pk)

    def test_tracked_example_exports_pass_validate_only_import(self):
        exports_dir = (
            Path(__file__).resolve().parents[1]
            / 'experiments'
            / 'debug'
            / 'assets'
            / 'definition-exports'
        )
        export_files = sorted(exports_dir.glob('*.json'))
        self.assertEqual(len(export_files), 9)

        for export_file in export_files:
            with self.subTest(export=export_file.name):
                payload = json.loads(export_file.read_text(encoding='utf-8'))
                result = self.import_payload(payload, mode='validate')

                self.assertTrue(result['dry_run'])
                self.assertIn(
                    result['model'],
                    {'Experiment', 'Form', 'Question'},
                )

    def test_examples_home_links_to_definition_import(self):
        response = self.client.get(reverse('experiments:debug:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PyEnsemble Examples')
        self.assertContains(response, 'Test Input Types')
        self.assertContains(
            response,
            reverse('importers:import-json'),
            html=False,
        )

    def test_audio_example_manifest_matches_callback_and_bundled_files(self):
        assets_dir = (
            Path(__file__).resolve().parents[1]
            / 'experiments'
            / 'debug'
            / 'assets'
        )
        with (assets_dir / 'audio-stimuli.csv').open(
            encoding='utf-8',
            newline='',
        ) as manifest_file:
            stimuli = list(csv.DictReader(manifest_file))

        self.assertEqual(
            {stimulus['name'] for stimulus in stimuli},
            {'Jazz7', 'Folk8'},
        )
        for stimulus in stimuli:
            with self.subTest(stimulus=stimulus['name']):
                self.assertTrue(
                    (assets_dir / 'audio' / stimulus['location']).is_file(),
                )

        audio_export = json.loads(
            (
                assets_dir
                / 'definition-exports'
                / 'experiment_test-audio.json'
            ).read_text(encoding='utf-8'),
        )
        self.assertIn(
            "name='Jazz7'",
            audio_export['exf_instances'][1]['stimulus_script'],
        )

    def test_definition_exports_are_pretty_and_use_safe_descriptive_filenames(self):
        experiment = Experiment.objects.create(title='Test Audio / Example')
        form = Form.objects.create(name='Audio feedback')
        question = Question.objects.create(
            text='Did you hear the audio play?',
            data_format=DataFormat.objects.create(
                df_type='enum',
                enum_values='"Yes","No"',
            ),
        )

        exports = (
            (
                'export_experiment_json',
                experiment,
                'experiment_test-audio-example.json',
            ),
            ('export_form_json', form, 'form_audio-feedback.json'),
            (
                'export_question_json',
                question,
                'question_did-you-hear-the-audio-play.json',
            ),
        )

        for route_name, instance, filename in exports:
            with self.subTest(model=route_name):
                response = self.client.get(
                    reverse(route_name, args=[instance.pk]),
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response['Content-Disposition'],
                    f'attachment; filename="{filename}"',
                )
                self.assertIn(b'\n  ', response.content)
                self.assertIsInstance(json.loads(response.content), dict)

    def test_update_changes_only_an_unlocked_selected_draft(self):
        draft = Experiment.objects.create(title='Existing draft')
        payload = experiment_payload(title='Imported name')
        payload['description'] = 'Updated description'

        result = self.import_payload(
            payload,
            mode='update',
            target_id=draft.pk,
        )

        draft.refresh_from_db()
        self.assertEqual(result['id'], draft.pk)
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(draft.title, 'Imported name')
        self.assertEqual(draft.description, 'Updated description')
        self.assertEqual(ExperimentXForm.objects.filter(experiment=draft).count(), 1)

    def test_update_rejects_locked_selected_draft_without_changes(self):
        draft = Experiment.objects.create(title='Draft')
        release_manager = get_user_model().objects.create_user('import-release-manager')
        release_manager.groups.add(Group.objects.get(name='Release manager'))
        lock_experiment(draft, release_manager, 'Release', 'release-1')
        payload = experiment_payload(title='Overwrite')

        with self.assertRaises(ImportConflict):
            self.import_payload(
                payload,
                mode='update',
                target_id=draft.pk,
            )

        draft.refresh_from_db()
        self.assertEqual(draft.title, 'Draft')
        self.assertFalse(Form.objects.exists())

    def test_validate_can_dry_run_an_update_target(self):
        draft = Experiment.objects.create(title='Draft')

        result = self.import_payload(
            experiment_payload(title='Imported'),
            mode='validate',
            target_id=draft.pk,
        )

        draft.refresh_from_db()
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(draft.title, 'Draft')

    def test_json_import_view_exposes_create_update_and_validate_modes(self):
        payload = experiment_payload()
        upload = SimpleUploadedFile(
            'experiment.json',
            json.dumps(payload).encode(),
            content_type='application/json',
        )
        response = self.client.post(
            reverse('pyensemble-importers:import-json'),
            {
                'file': upload,
                'mode': 'validate',
                'new_name': 'Preview only',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No changes were saved')
        self.assertFalse(Experiment.objects.exists())

    def test_json_import_view_uses_json_name_and_hides_optional_fields_by_default(self):
        get_response = self.client.get(
            reverse('pyensemble-importers:import-json'),
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'Draft ID')
        self.assertRegex(
            get_response.content.decode(),
            r'<div id="target-id-field" hidden>',
        )
        self.assertNotContains(
            get_response,
            'id="new-name-field"',
            html=False,
        )

        upload = SimpleUploadedFile(
            'example.json',
            json.dumps(experiment_payload(title='JSON title')).encode(),
            content_type='application/json',
        )
        response = self.client.post(
            reverse('pyensemble-importers:import-json'),
            {'file': upload, 'mode': 'create'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Experiment.objects.filter(title='JSON title').exists())
        self.assertContains(
            response,
            "Experiment 'JSON title' was created.",
        )

        repeat_upload = SimpleUploadedFile(
            'example.json',
            json.dumps(experiment_payload(title='JSON title')).encode(),
            content_type='application/json',
        )
        repeat_response = self.client.post(
            reverse('pyensemble-importers:import-json'),
            {'file': repeat_upload, 'mode': 'create'},
        )
        self.assertEqual(repeat_response.status_code, 200)
        self.assertContains(
            repeat_response,
            "Experiment 'JSON title' already existed. The existing definition was reused.",
        )

    def test_json_import_view_offers_rename_after_root_conflict(self):
        self.import_payload(
            experiment_payload(title='Existing example'),
            mode='create',
        )
        conflicting_payload = experiment_payload(title='Existing example')
        conflicting_payload['description'] = 'Changed experiment description'
        upload = SimpleUploadedFile(
            'example.json',
            json.dumps(conflicting_payload).encode(),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('pyensemble-importers:import-json'),
            {'file': upload, 'mode': 'create'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            'Import using a different title or name',
            status_code=400,
        )
        self.assertContains(
            response,
            'conflicts with an existing',
            status_code=400,
        )

    def test_legacy_import_view_uses_atomic_definition_import(self):
        upload = SimpleUploadedFile(
            'legacy.csv',
            b'experiment_title,form_name,question_text,type,locked\n'
            b'Old title,Legacy consent,Agree?,text,T\n',
            content_type='text/csv',
        )

        response = self.client.post(
            reverse('pyensemble-importers:import-experiment-structure'),
            {
                'file': upload,
                'mode': 'create',
                'new_name': 'Imported legacy draft',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Imported legacy draft')
        experiment = Experiment.objects.get(title='Imported legacy draft')
        self.assertFalse(experiment.locked)
        self.assertTrue(Form.objects.filter(name='Legacy consent').exists())
        self.assertTrue(Question.objects.filter(text='Agree?').exists())

    def test_import_views_require_editor_role(self):
        self.client.force_login(get_user_model().objects.create_user('no-import-role'))

        response = self.client.get(reverse('pyensemble-importers:import-json'))

        self.assertEqual(response.status_code, 403)
