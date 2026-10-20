import json

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
            new_name='New draft',
        )

        experiment = Experiment.objects.get(pk=result['id'])
        form = Form.objects.get(name='Consent form')
        question = Question.objects.get(text='Consent?')
        data_format = DataFormat.objects.get(df_type='text')
        self.assertEqual(result['action'], 'created or reused')
        self.assertFalse(experiment.locked)
        self.assertFalse(form.locked)
        self.assertFalse(question.locked)
        self.assertEqual(experiment.release_identifier, '')
        self.assertIsNone(experiment.lock_snapshot)
        self.assertTrue(
            ExperimentXForm.objects.filter(experiment=experiment, form=form).exists(),
        )
        self.assertTrue(
            FormXQuestion.objects.filter(form=form, question=question).exists(),
        )
        self.assertEqual(question.data_format, data_format)

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
