from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
    Ticket,
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

    def test_experiment_lock_expires_all_existing_tickets_at_local_lock_time(self):
        Ticket.objects.create(
            ticket_code='MASTER-OPEN',
            experiment=self.experiment,
        )
        Ticket.objects.create(
            ticket_code='USER-FUTURE',
            experiment=self.experiment,
            type='user',
            expiration_datetime=timezone.now() + timedelta(days=2),
        )
        Ticket.objects.create(
            ticket_code='USER-PAST',
            experiment=self.experiment,
            type='user',
            expiration_datetime=timezone.now() - timedelta(days=2),
        )
        other_experiment = Experiment.objects.create(title='Unrelated study')
        unrelated_ticket = Ticket.objects.create(
            ticket_code='OTHER-OPEN',
            experiment=other_experiment,
        )

        locked = self.lock_experiment()

        expected_expiration = timezone.localtime(locked.locked_at)
        for ticket in Ticket.objects.filter(experiment=self.experiment):
            with self.subTest(ticket=ticket.ticket_code):
                self.assertEqual(ticket.expiration_datetime, expected_expiration)
        unrelated_ticket.refresh_from_db()
        self.assertIsNone(unrelated_ticket.expiration_datetime)

    def test_experiment_lock_action_records_metadata_and_shows_locked_state(self):
        self.experiment.session_reporting_script = 'debug.reporting.summary'
        self.experiment_form.condition_script = 'debug.conditions.should_continue'
        self.experiment.save()
        self.experiment_form.save()
        lock_url = reverse(
            'definition_lock',
            args=('experiment', self.experiment.pk),
        )

        confirmation = self.client.get(lock_url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, 'Confirm production lock')
        self.assertContains(confirmation, 'existing tickets')
        editor_page_before_lock = self.client.get(
            reverse('experiment_update', args=[self.experiment.pk]),
        )
        self.assertContains(editor_page_before_lock, 'Lock for production')

        response = self.client.post(lock_url, {
            'reason': 'Production data collection begins',
            'release_identifier': 'release-2026-01',
        })

        self.assertRedirects(
            response,
            reverse('experiment_update', args=[self.experiment.pk])
            + '?standalone=1',
        )
        locked = Experiment.objects.get(pk=self.experiment.pk)
        self.assertTrue(locked.locked)
        self.assertEqual(locked.locked_by, self.actor)
        self.assertEqual(locked.lock_reason, 'Production data collection begins')
        self.assertEqual(locked.release_identifier, 'release-2026-01')
        self.assertEqual(
            locked.lock_snapshot['experiment']['session_reporting_script'],
            'debug.reporting.summary',
        )
        self.assertEqual(
            locked.lock_snapshot['forms'][0]['relationship'][
                'condition_script'
            ],
            'debug.conditions.should_continue',
        )

        editor_page = self.client.get(response.url)
        self.assertContains(editor_page, 'PyEnsemble - Editors')
        self.assertContains(editor_page, 'class="col-12" id="content-right"')
        self.assertContains(editor_page, 'detailHeader')
        self.assertContains(editor_page, 'class="badge badge-warning">Locked</span>')
        self.assertContains(editor_page, 'data-target="#productionLockInfoModal"')
        self.assertContains(editor_page, 'id="productionLockInfoModal"')
        self.assertContains(editor_page, 'Locked for production.')
        self.assertContains(editor_page, 'release-2026-01')
        self.assertNotContains(editor_page, 'Lock for production')

    def test_locked_experiment_can_generate_new_master_tickets(self):
        self.lock_experiment()

        editor_page = self.client.get(
            reverse('experiment_update', args=[self.experiment.pk])
            + '?standalone=1',
        )
        self.assertEqual(editor_page.status_code, 200)
        self.assertContains(
            editor_page,
            f'action="{reverse("create_ticket")}"',
        )

        response = self.client.post(reverse('create_ticket'), {
            'experiment_id': self.experiment.pk,
            'num_master': 1,
            'master_expiration': '',
            'num_user': 0,
            'user_expiration': '',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Ticket.objects.filter(
                experiment=self.experiment,
                type='master',
            ).count(),
            1,
        )

    def test_locked_definition_editors_disable_editing_controls(self):
        self.lock_experiment()

        for url_name, instance in (
            ('experiment_update', self.experiment),
            ('form_update', self.form),
            ('question_update', self.question),
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=[instance.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    'data-disable-editor-fields="true"',
                )
                self.assertContains(
                    response,
                    '$(".editor-form :input").prop("disabled", true);',
                )
                self.assertTrue(
                    response.context['form'].fields[
                        'title' if url_name == 'experiment_update' else
                        'name' if url_name == 'form_update' else
                        'text'
                    ].disabled,
                )
                self.assertContains(response, 'disabled')
                self.assertNotContains(response, 'id="formTableEditButton"')

        form_page = self.client.get(reverse('form_update', args=[self.form.pk]))
        self.assertContains(form_page, 'This Form is protected by a production lock.')
        question_page = self.client.get(
            reverse('question_update', args=[self.question.pk]),
        )
        self.assertContains(
            question_page,
            'This Question is protected by a production lock.',
        )

    def test_locked_study_editor_disables_editing_controls(self):
        second_experiment = Experiment.objects.create(title='Second study')
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
        lock_study(
            study,
            self.actor,
            'Production data collection begins',
            'release-2026-01',
        )

        response = self.client.get(reverse('study_update', args=[study.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-disable-editor-fields="true"')
        self.assertContains(response, '$(".editor-form :input").prop("disabled", true);')
        self.assertTrue(response.context['form'].fields['title'].disabled)
        self.assertTrue(response.context['formset'].forms[0].fields['experiment'].disabled)
        self.assertRegex(
            response.content.decode(),
            r'<button id="add-study-experiment"[^>]*\sdisabled>',
        )
        self.assertNotContains(response, 'id="formTableEditButton"')

    def test_experiment_lock_action_requires_release_manager_role(self):
        editor = get_user_model().objects.create_user('lock-action-editor')
        editor.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(editor)

        response = self.client.get(reverse(
            'definition_lock',
            args=('experiment', self.experiment.pk),
        ))

        self.assertEqual(response.status_code, 403)
        editor_page = self.client.get(
            reverse('experiment_update', args=[self.experiment.pk]),
        )
        self.assertNotContains(editor_page, 'Lock for production')
        self.assertFalse(Experiment.objects.get(pk=self.experiment.pk).locked)

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

    def test_study_lock_expires_tickets_for_all_included_experiments(self):
        second_experiment = Experiment.objects.create(title='Second study protocol')
        study = Study.objects.create(title='Collection study')
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
        Ticket.objects.create(
            ticket_code='STUDY-FIRST',
            experiment=self.experiment,
        )
        Ticket.objects.create(
            ticket_code='STUDY-SECOND',
            experiment=second_experiment,
            expiration_datetime=timezone.now() + timedelta(days=1),
        )
        unrelated_experiment = Experiment.objects.create(
            title='Outside study protocol',
        )
        unrelated_ticket = Ticket.objects.create(
            ticket_code='OUTSIDE-STUDY',
            experiment=unrelated_experiment,
        )

        locked_study = lock_study(
            study,
            self.actor,
            'Study release',
            'study-release-tickets',
        )

        expected_expiration = timezone.localtime(locked_study.locked_at)
        study_tickets = Ticket.objects.filter(
            experiment__in=(self.experiment, second_experiment),
        )
        self.assertEqual(study_tickets.count(), 2)
        for ticket in study_tickets:
            with self.subTest(ticket=ticket.ticket_code):
                self.assertEqual(ticket.expiration_datetime, expected_expiration)
        unrelated_ticket.refresh_from_db()
        self.assertIsNone(unrelated_ticket.expiration_datetime)

    def test_study_lock_action_locks_study_and_displays_immutable_state(self):
        second_experiment = Experiment.objects.create(title='Second release experiment')
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
        lock_url = reverse('definition_lock', args=('study', study.pk))

        response = self.client.post(lock_url, {
            'reason': 'Production study release',
            'release_identifier': 'study-release-1',
        })

        self.assertRedirects(
            response,
            reverse('study_update', args=[study.pk]) + '?standalone=1',
        )
        study.refresh_from_db()
        self.assertTrue(study.locked)
        self.assertEqual(study.locked_by, self.actor)
        self.assertEqual(study.lock_reason, 'Production study release')
        self.assertEqual(study.release_identifier, 'study-release-1')
        self.assertContains(
            self.client.get(reverse('study_update', args=[study.pk])),
            'Locked for production.',
        )
        with self.assertRaises(LockedDefinitionError):
            self.experiment.title = 'Cannot edit released experiment'
            self.experiment.save()

    def test_study_lock_action_rejects_invalid_study_without_locking(self):
        study = Study.objects.create(title='Incomplete study')
        StudyXExperiment.objects.create(
            study=study,
            experiment=self.experiment,
            experiment_order=1,
        )

        response = self.client.post(
            reverse('definition_lock', args=('study', study.pk)),
            {
                'reason': 'Production release',
                'release_identifier': 'study-release-invalid',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            'A Study must contain at least two distinct Experiments',
            status_code=400,
        )
        self.assertFalse(Study.objects.get(pk=study.pk).locked)

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

    def test_clone_locked_experiment_copies_metadata_and_relationships_only(self):
        self.experiment.description = 'Protocol description'
        self.experiment.params = '{"mode": "production"}'
        self.experiment.is_group = True
        self.experiment.save()
        self.experiment_form.form_handler = 'form_feedback'
        self.experiment_form.condition = 'condition-expression'
        self.experiment_form.stimulus_script = 'stimulus.method'
        self.experiment_form.save()
        self.lock_experiment()
        source_row_id = self.experiment_form.pk
        source_form_id = self.experiment_form.form_id

        response = self.client.post(
            reverse('experiment_copy', args=[self.experiment.pk]),
            {'title': 'Draft protocol'},
        )

        clone = Experiment.objects.get(title='Draft protocol')
        clone_row = ExperimentXForm.objects.get(experiment=clone)
        self.assertRedirects(
            response,
            reverse('experiment_update', args=[clone.pk]),
        )
        self.assertNotEqual(clone.pk, self.experiment.pk)
        self.assertFalse(clone.locked)
        self.assertEqual(clone.description, 'Protocol description')
        self.assertEqual(clone.params, '{"mode": "production"}')
        self.assertTrue(clone.is_group)
        self.assertNotEqual(clone_row.pk, source_row_id)
        self.assertEqual(clone_row.form_id, source_form_id)
        self.assertEqual(clone_row.form_handler, 'form_feedback')
        self.assertEqual(clone_row.condition, 'condition-expression')
        self.assertEqual(clone_row.stimulus_script, 'stimulus.method')
        self.assertTrue(Experiment.objects.get(pk=self.experiment.pk).locked)
        self.assertEqual(
            ExperimentXForm.objects.get(pk=source_row_id).form_id,
            source_form_id,
        )
        clone.title = 'Edited draft protocol'
        clone.save()
        clone_row.form_order = 2
        clone_row.save()
        self.assertEqual(
            Experiment.objects.get(pk=self.experiment.pk).title,
            'Production study',
        )
        self.assertEqual(
            ExperimentXForm.objects.get(pk=source_row_id).form_order,
            1,
        )

    def test_clone_locked_form_copies_question_relationships_only(self):
        self.form.header = 'Instructions'
        self.form.license = 'CC BY 4.0'
        self.form.citation = 'Example attribution'
        self.form.visit_once = True
        self.form.save()
        self.form_question.question_iteration = 3
        self.form_question.required = False
        self.form_question.save()
        self.lock_experiment()
        source_row_id = self.form_question.pk

        response = self.client.post(
            reverse('form_copy', args=[self.form.pk]),
            {'name': 'Consent draft'},
        )

        clone = Form.objects.get(name='Consent draft')
        clone_row = FormXQuestion.objects.get(form=clone)
        self.assertRedirects(
            response,
            reverse('form_update', args=[clone.pk]),
        )
        self.assertNotEqual(clone.pk, self.form.pk)
        self.assertFalse(clone.locked)
        self.assertEqual(clone.header, 'Instructions')
        self.assertEqual(clone.license, 'CC BY 4.0')
        self.assertEqual(clone.citation, 'Example attribution')
        self.assertTrue(clone.visit_once)
        self.assertNotEqual(clone_row.pk, source_row_id)
        self.assertEqual(clone_row.question_id, self.question.pk)
        self.assertEqual(clone_row.question_iteration, 3)
        self.assertFalse(clone_row.required)
        self.assertEqual(
            FormXQuestion.objects.get(pk=source_row_id).form_id,
            self.form.pk,
        )
        self.assertEqual(Question.objects.get(pk=self.question.pk).text, 'Do you agree?')
        clone.name = 'Edited consent draft'
        clone.save()
        clone_row.question_iteration = 4
        clone_row.save()
        self.assertEqual(Form.objects.get(pk=self.form.pk).name, 'Consent')
        self.assertEqual(
            FormXQuestion.objects.get(pk=source_row_id).question_iteration,
            3,
        )

    def test_clone_locked_study_copies_membership_but_reuses_experiments(self):
        second_experiment = Experiment.objects.create(title='Second protocol')
        study = Study.objects.create(title='Production Study', params={'cohort': 'A'})
        source_rows = [
            StudyXExperiment.objects.create(
                study=study,
                experiment=experiment,
                experiment_order=order,
            )
            for order, experiment in enumerate(
                (self.experiment, second_experiment),
                start=1,
            )
        ]
        lock_study(study, self.actor, 'Release', 'study-release-2')

        response = self.client.post(
            reverse('study_copy', args=[study.pk]),
            {'title': 'Draft Study'},
        )

        clone = Study.objects.get(title='Draft Study')
        clone_rows = list(
            StudyXExperiment.objects.filter(study=clone).order_by('experiment_order'),
        )
        self.assertRedirects(response, reverse('study_update', args=[clone.pk]))
        self.assertNotEqual(clone.pk, study.pk)
        self.assertFalse(clone.locked)
        self.assertEqual(clone.params, {'cohort': 'A'})
        self.assertEqual(
            [row.experiment_id for row in clone_rows],
            [row.experiment_id for row in source_rows],
        )
        self.assertTrue(all(
            clone_row.pk != source_row.pk
            for clone_row, source_row in zip(clone_rows, source_rows)
        ))
        self.assertTrue(Study.objects.get(pk=study.pk).locked)
        self.assertEqual(Experiment.objects.count(), 2)
        clone.title = 'Edited draft Study'
        clone.save()
        clone_rows[0].experiment_order = 2
        clone_rows[0].save()
        self.assertEqual(Study.objects.get(pk=study.pk).title, 'Production Study')
        self.assertEqual(
            StudyXExperiment.objects.get(pk=source_rows[0].pk).experiment_order,
            1,
        )

    def test_clone_endpoints_reject_duplicate_names_without_side_effects(self):
        self.lock_experiment()
        experiment_count = Experiment.objects.count()
        form_count = Form.objects.count()

        experiment_response = self.client.post(
            reverse('experiment_copy', args=[self.experiment.pk]),
            {'title': self.experiment.title},
        )
        form_response = self.client.post(
            reverse('form_copy', args=[self.form.pk]),
            {'name': self.form.name},
        )

        self.assertEqual(experiment_response.status_code, 400)
        self.assertEqual(form_response.status_code, 400)
        self.assertEqual(Experiment.objects.count(), experiment_count)
        self.assertEqual(Form.objects.count(), form_count)

    def test_clone_dialogs_use_valid_urls_for_each_object_type(self):
        second_experiment = Experiment.objects.create(title='Second protocol')
        study = Study.objects.create(title='Study with protocols')
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

        cases = (
            ('experiment_update', self.experiment.pk, "fetchNewItemForm('experiments')"),
            ('form_update', self.form.pk, "fetchNewItemForm('forms')"),
            ('study_update', study.pk, "fetchNewItemForm('studies')"),
        )
        for view_name, object_id, expected_script in cases:
            with self.subTest(view=view_name):
                response = self.client.get(reverse(view_name, args=[object_id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_script)

    def test_start_navigation_is_only_shown_for_group_experiments(self):
        response = self.client.get(
            reverse('experiment_update', args=[self.experiment.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            reverse('pyensemble-group:start_groupsession'),
        )
        self.assertContains(response, 'Tickets')

        self.experiment.is_group = True
        self.experiment.save()

        response = self.client.get(
            reverse('experiment_update', args=[self.experiment.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse('pyensemble-group:start_groupsession'),
        )
        self.assertNotContains(response, 'Tickets')

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
