from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from pyensemble.locking import LockedDefinitionError, lock_experiment, lock_study
from pyensemble.models import (
    DataFormat,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Question,
    Study,
    StudyXExperiment,
)


class DefinitionLockingTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user('release-manager')
        self.actor.groups.add(Group.objects.get(name='Release manager'))
        self.client.force_login(self.actor)
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
        self.experiment = Experiment.objects.create(title='Production study')
        self.experiment_form = ExperimentXForm.objects.create(
            experiment=self.experiment,
            form=self.form,
            form_order=1,
        )

    def lock_experiment(self):
        return lock_experiment(
            self.experiment,
            self.actor,
            'Production data collection begins',
            'release-2026-01',
        )

    def test_standalone_experiment_can_be_locked_without_a_study(self):
        self.assertFalse(Study.objects.exists())

        locked = self.lock_experiment()

        self.assertTrue(locked.locked)
        self.assertEqual(locked.locked_by, self.actor)
        self.assertEqual(locked.lock_reason, 'Production data collection begins')
        self.assertEqual(locked.release_identifier, 'release-2026-01')
        self.assertEqual(len(locked.lock_snapshot_digest), 64)
        self.assertEqual(
            locked.lock_snapshot['forms'][0]['form']['form']['name'],
            'Consent',
        )
        self.assertEqual(
            locked.lock_snapshot['forms'][0]['form']['questions'][0]
            ['question']['question']['text'],
            'Do you agree?',
        )
        self.assertTrue(
            Experiment.objects.get(pk=self.experiment.pk).locked,
        )

    def test_experiment_lock_protects_reachable_definition_and_relationships(self):
        self.lock_experiment()

        locked_experiment = Experiment.objects.get(pk=self.experiment.pk)
        locked_experiment.title = 'Changed title'
        with self.assertRaises(LockedDefinitionError):
            locked_experiment.save()

        locked_form = Form.objects.get(pk=self.form.pk)
        locked_form.name = 'Changed form'
        with self.assertRaises(LockedDefinitionError):
            locked_form.save()

        locked_question = Question.objects.get(pk=self.question.pk)
        locked_question.text = 'Changed question'
        with self.assertRaises(LockedDefinitionError):
            locked_question.save()

        locked_data_format = DataFormat.objects.get(pk=self.data_format.pk)
        locked_data_format.enum_values = '"No","Yes"'
        with self.assertRaises(LockedDefinitionError):
            locked_data_format.save()

        experiment_form = ExperimentXForm.objects.get(pk=self.experiment_form.pk)
        experiment_form.form_order = 2
        with self.assertRaises(LockedDefinitionError):
            experiment_form.save()

        form_question = FormXQuestion.objects.get(pk=self.form_question.pk)
        form_question.required = False
        with self.assertRaises(LockedDefinitionError):
            form_question.save()

    def test_protected_queryset_mutation_and_deletion_are_rejected(self):
        self.lock_experiment()

        with self.assertRaises(LockedDefinitionError):
            Form.objects.filter(pk=self.form.pk).update(name='Changed by update')
        locked_form = Form.objects.get(pk=self.form.pk)
        locked_form.name = 'Changed by bulk update'
        with self.assertRaises(LockedDefinitionError):
            Form.objects.bulk_update([locked_form], ['name'])
        with self.assertRaises(LockedDefinitionError):
            ExperimentXForm.objects.filter(
                pk=self.experiment_form.pk,
            ).delete()
        with self.assertRaises(LockedDefinitionError):
            Form.objects.filter(pk=self.form.pk).delete()
        additional_form = Form.objects.create(name='Additional locked form')
        with self.assertRaises(LockedDefinitionError):
            ExperimentXForm.objects.bulk_create([
                ExperimentXForm(
                    experiment=self.experiment,
                    form=additional_form,
                    form_order=2,
                ),
            ])
        with self.assertRaises(LockedDefinitionError):
            self.experiment.forms.add(additional_form)

    def test_unlocked_relationship_rows_can_reference_locked_children(self):
        self.lock_experiment()
        editable_experiment = Experiment.objects.create(title='Draft clone')
        editable_experiment_form = ExperimentXForm.objects.create(
            experiment=editable_experiment,
            form=self.form,
            form_order=1,
        )
        editable_experiment_form.form_order = 2
        editable_experiment_form.save()

        editable_form = Form.objects.create(name='Draft form')
        editable_form_question = FormXQuestion.objects.create(
            form=editable_form,
            question=self.question,
            form_question_num=1,
        )
        editable_form_question.required = False
        editable_form_question.save()

        self.assertEqual(
            ExperimentXForm.objects.get(pk=editable_experiment_form.pk).form_id,
            self.form.pk,
        )
        self.assertFalse(
            FormXQuestion.objects.get(pk=editable_form_question.pk).required,
        )
        self.assertEqual(Form.objects.get(pk=self.form.pk).name, 'Consent')
        self.assertEqual(
            Question.objects.get(pk=self.question.pk).text,
            'Do you agree?',
        )

    def test_study_lock_protects_membership_and_included_experiment_graph(self):
        second_experiment = Experiment.objects.create(title='Second experiment')
        study = Study.objects.create(title='Production study')
        StudyXExperiment.objects.create(
            study=study,
            experiment=self.experiment,
            experiment_order=1,
        )
        StudyXExperiment.objects.create(
            study=study,
            experiment=second_experiment,
            experiment_order=2,
        )

        locked_study = lock_study(
            study,
            self.actor,
            'Study release',
            'study-release-1',
        )
        self.assertTrue(locked_study.locked)

        locked_study.title = 'Changed study'
        with self.assertRaises(LockedDefinitionError):
            locked_study.save()

        membership = StudyXExperiment.objects.get(
            study=study,
            experiment=self.experiment,
        )
        membership.experiment_order = 2
        with self.assertRaises(LockedDefinitionError):
            membership.save()

        included_experiment = Experiment.objects.get(pk=self.experiment.pk)
        included_experiment.title = 'Changed through study'
        with self.assertRaises(LockedDefinitionError):
            included_experiment.save()

        included_form = Form.objects.get(pk=self.form.pk)
        included_form.name = 'Changed through study'
        with self.assertRaises(LockedDefinitionError):
            included_form.save()

    def test_direct_lock_metadata_changes_are_not_allowed(self):
        self.experiment.locked = True
        with self.assertRaises(LockedDefinitionError):
            self.experiment.save(update_fields=['locked'])

    def test_lock_requires_reason_and_release_identifier(self):
        with self.assertRaises(ValueError):
            lock_experiment(self.experiment, self.actor, ' ', 'release-1')
        with self.assertRaises(ValueError):
            lock_experiment(self.experiment, self.actor, 'Reason', '')

        self.assertFalse(Experiment.objects.get(pk=self.experiment.pk).locked)

    def test_editor_role_cannot_lock_production_definitions(self):
        editor = get_user_model().objects.create_user('editor')
        editor.groups.add(Group.objects.get(name='Editor'))

        with self.assertRaises(PermissionDenied):
            lock_experiment(
                self.experiment,
                editor,
                'Production release',
                'release-1',
            )
        self.assertFalse(Experiment.objects.get(pk=self.experiment.pk).locked)

    def test_editor_formsets_are_validated_before_parent_updates(self):
        response = self.client.post(
            reverse('experiment_update', args=[self.experiment.pk]),
            {'title': 'Changed experiment'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Experiment.objects.get(pk=self.experiment.pk).title,
            'Production study',
        )

        response = self.client.post(
            reverse('form_update', args=[self.form.pk]),
            {'name': 'Changed form'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Form.objects.get(pk=self.form.pk).name, 'Consent')
