from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from pyensemble.deletion import (
    DefinitionDeletionBlocked,
    delete_definition,
)
from pyensemble.locking import LockedDefinitionError, lock_experiment
from pyensemble.models import (
    DataFormat,
    DefinitionDeletionLog,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Question,
    Study,
    StudyXExperiment,
    Ticket,
)


class DefinitionDeletionTests(TestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user('delete-editor')
        self.editor.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(self.editor)
        self.data_format = DataFormat.objects.create(
            df_type='enum',
            enum_values='"Yes","No"',
        )
        self.question = Question.objects.create(
            text='Do you agree?',
            data_format=self.data_format,
        )
        self.form = Form.objects.create(name='Consent')
        self.form_question = FormXQuestion.objects.create(
            form=self.form,
            question=self.question,
            form_question_num=1,
        )
        self.experiment = Experiment.objects.create(title='Draft experiment')
        self.experiment_form = ExperimentXForm.objects.create(
            experiment=self.experiment,
            form=self.form,
            form_order=1,
        )

    def delete_url(self, model_name, instance):
        return reverse('definition_delete', args=(model_name, instance.pk))

    def delete_definition(self, instance):
        return delete_definition(instance, self.editor, 'Unused draft cleanup')

    def test_study_delete_removes_membership_only_and_preserves_experiments(self):
        study = Study.objects.create(title='Draft study')
        StudyXExperiment.objects.create(
            study=study,
            experiment=self.experiment,
            experiment_order=1,
        )
        second_experiment = Experiment.objects.create(title='Second experiment')
        StudyXExperiment.objects.create(
            study=study,
            experiment=second_experiment,
            experiment_order=2,
        )

        response = self.client.post(
            self.delete_url('study', study),
            {'reason': 'Unused draft cleanup'},
        )

        self.assertRedirects(response, reverse('editor'))
        self.assertFalse(Study.objects.filter(pk=study.pk).exists())
        self.assertFalse(StudyXExperiment.objects.filter(study=study).exists())
        self.assertTrue(Experiment.objects.filter(pk=self.experiment.pk).exists())
        self.assertTrue(Experiment.objects.filter(pk=second_experiment.pk).exists())
        log = DefinitionDeletionLog.objects.get(
            model_name='Study',
            target_id=str(study.pk),
        )
        self.assertEqual(log.actor, self.editor)
        self.assertEqual(log.target_label, 'Draft study')
        self.assertEqual(log.reason, 'Unused draft cleanup')
        self.assertEqual(log.reference_counts, {'Study memberships removed': 2})

    def test_experiment_referenced_by_study_is_blocked(self):
        study = Study.objects.create(title='Draft study')
        StudyXExperiment.objects.create(
            study=study,
            experiment=self.experiment,
            experiment_order=1,
        )

        response = self.client.get(self.delete_url('experiment', self.experiment))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Study memberships (1)')
        self.assertNotContains(response, 'Permanently delete')
        with self.assertRaises(DefinitionDeletionBlocked):
            self.delete_definition(self.experiment)
        self.assertTrue(Experiment.objects.filter(pk=self.experiment.pk).exists())

    def test_ticket_history_blocks_experiment_deletion(self):
        ticket = Ticket.objects.create(
            ticket_code='DRAFT-TICKET',
            experiment=self.experiment,
        )

        response = self.client.post(
            self.delete_url('experiment', self.experiment),
            {'reason': 'Cleanup'},
        )

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'Tickets (1)', status_code=409)
        self.assertTrue(Experiment.objects.filter(pk=self.experiment.pk).exists())
        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_form_used_by_experiment_cannot_be_deleted(self):
        with self.assertRaises(LockedDefinitionError):
            self.form.delete()
        response = self.client.get(self.delete_url('form', self.form))
        self.assertContains(response, 'Experiment memberships (1)')
        self.assertNotContains(response, 'Permanently delete')

    def test_question_used_by_form_and_enum_used_by_question_cannot_be_deleted(self):
        with self.assertRaises(LockedDefinitionError):
            self.question.delete()
        with self.assertRaises(LockedDefinitionError):
            self.data_format.delete()

        question_response = self.client.get(
            self.delete_url('question', self.question),
        )
        enum_response = self.client.get(
            self.delete_url('enum', self.data_format),
        )
        self.assertContains(question_response, 'Form memberships (1)')
        self.assertContains(enum_response, 'Questions using this data format (1)')

    def test_form_can_be_deleted_after_detaching_without_deleting_questions(self):
        self.experiment_form.delete()

        self.delete_definition(self.form)

        self.assertFalse(Form.objects.filter(pk=self.form.pk).exists())
        self.assertFalse(FormXQuestion.objects.filter(form_id=self.form.pk).exists())
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())
        self.assertTrue(
            DataFormat.objects.filter(pk=self.data_format.pk).exists(),
        )

    def test_experiment_can_be_deleted_after_detaching_without_deleting_forms(self):
        self.experiment_form.delete()

        self.delete_definition(self.experiment)

        self.assertFalse(Experiment.objects.filter(pk=self.experiment.pk).exists())
        self.assertTrue(Form.objects.filter(pk=self.form.pk).exists())
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_question_and_enum_can_be_deleted_after_detaching(self):
        self.form_question.delete()

        self.delete_definition(self.question)
        self.delete_definition(self.data_format)

        self.assertFalse(Question.objects.filter(pk=self.question.pk).exists())
        self.assertFalse(DataFormat.objects.filter(pk=self.data_format.pk).exists())

    def test_enum_delete_route_rejects_non_enum_data_formats(self):
        text_format = DataFormat.objects.create(df_type='text')

        response = self.client.get(self.delete_url('enum', text_format))

        self.assertEqual(response.status_code, 404)

    def test_locked_definitions_cannot_be_deleted_from_confirmation_or_post(self):
        release_manager = get_user_model().objects.create_user(
            'delete-release-manager',
        )
        release_manager.groups.add(Group.objects.get(name='Release manager'))
        self.client.force_login(release_manager)
        lock_experiment(
            self.experiment,
            release_manager,
            'Test production release',
            'delete-policy-test',
        )

        response = self.client.get(
            self.delete_url('experiment', self.experiment),
        )
        self.assertContains(response, 'locked for production')
        self.assertNotContains(response, 'Permanently delete')

        response = self.client.post(
            self.delete_url('experiment', self.experiment),
            {'reason': 'Cleanup attempt'},
        )
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Experiment.objects.filter(pk=self.experiment.pk).exists())

    def test_delete_endpoint_requires_editor_role(self):
        unassigned = get_user_model().objects.create_user('unassigned-delete-user')
        self.client.force_login(unassigned)

        response = self.client.post(
            self.delete_url('study', Study.objects.create(title='Draft')),
            {'reason': 'Test'},
        )

        self.assertEqual(response.status_code, 403)


class RestrictiveForeignKeyTests(TransactionTestCase):
    def test_database_protects_form_relationships_from_raw_deletion(self):
        data_format = DataFormat.objects.create(
            df_type='enum',
            enum_values='"Yes","No"',
        )
        question = Question.objects.create(
            text='Do you agree?',
            data_format=data_format,
        )
        form = Form.objects.create(name='Consent')
        form_question = FormXQuestion.objects.create(
            form=form,
            question=question,
            form_question_num=1,
        )

        with self.assertRaises(IntegrityError):
            Form.objects.filter(pk=form.pk)._raw_delete('default')

        self.assertTrue(Form.objects.filter(pk=form.pk).exists())
        self.assertTrue(FormXQuestion.objects.filter(pk=form_question.pk).exists())
        self.assertTrue(Question.objects.filter(pk=question.pk).exists())
