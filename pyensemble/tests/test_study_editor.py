from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from pyensemble.models import Experiment, Study, StudyXExperiment


class StudyEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user('study-editor')
        cls.editor.groups.add(Group.objects.get(name='Editor'))
        cls.experiments = [
            Experiment.objects.create(title=f'Experiment {index}')
            for index in range(1, 5)
        ]

    def setUp(self):
        self.client.force_login(self.editor)

    @staticmethod
    def formset_data(experiments, initial_rows=None, deleted_rows=()):
        initial_rows = initial_rows or []
        deleted_rows = set(deleted_rows)
        data = {
            'title': 'Ordered study',
            'params': '',
            'studyxexperiment_set-TOTAL_FORMS': str(max(
                2, len(experiments), len(initial_rows),
            )),
            'studyxexperiment_set-INITIAL_FORMS': str(len(initial_rows)),
            'studyxexperiment_set-MIN_NUM_FORMS': '2',
            'studyxexperiment_set-MAX_NUM_FORMS': '100',
        }
        for index, experiment_id in enumerate(experiments):
            prefix = f'studyxexperiment_set-{index}'
            data[f'{prefix}-experiment'] = str(experiment_id) if experiment_id else ''
            if experiment_id:
                data[f'{prefix}-ORDER'] = str(index + 1)
            data[f'{prefix}-DELETE'] = 'on' if index in deleted_rows else ''
            if index < len(initial_rows):
                data[f'{prefix}-id'] = str(initial_rows[index].pk)
        return data

    def test_study_list_and_editor_navigation_are_available(self):
        study = Study.objects.create(title='Existing study')
        StudyXExperiment.objects.create(
            study=study, experiment=self.experiments[0], experiment_order=1,
        )
        StudyXExperiment.objects.create(
            study=study, experiment=self.experiments[1], experiment_order=2,
        )

        response = self.client.get(reverse('study_list'))
        self.assertContains(response, 'Existing study')
        self.assertContains(response, reverse('study_update', args=[study.pk]))
        self.assertContains(response, 'data-toggle="table"')
        self.assertNotContains(response, '<html')
        self.assertNotContains(response, 'jquery-3.4.1.min.js')

    def test_create_study_with_two_or_more_ordered_experiments(self):
        data = self.formset_data([self.experiments[2].pk, self.experiments[0].pk, self.experiments[3].pk])
        response = self.client.post(reverse('study_create'), data)
        study = Study.objects.get(title='Ordered study')
        self.assertRedirects(response, reverse('study_update', args=[study.pk]))
        self.assertEqual(
            list(study.studyxexperiment_set.order_by('experiment_order').values_list(
                'experiment_id', 'experiment_order',
            )),
            [
                (self.experiments[2].pk, 1),
                (self.experiments[0].pk, 2),
                (self.experiments[3].pk, 3),
            ],
        )

    def test_create_page_can_add_arbitrary_number_of_experiments(self):
        response = self.client.get(reverse('study_create'))
        self.assertContains(response, 'id="id_studyxexperiment_set-TOTAL_FORMS"')
        self.assertContains(response, 'Add another experiment')
        self.assertContains(response, 'study-empty-form')
        self.assertNotContains(response, 'null</textarea>')
        self.assertEqual(
            [row['ORDER'].value() for row in response.context['formset'].forms],
            [1, 2],
        )

    def test_study_relationship_can_reference_an_experiment_already_marked_locked(self):
        locked_experiment = self.experiments[0]
        locked_experiment.locked = True
        locked_experiment.save(update_fields=['locked'])
        study = Study.objects.create(title='Study containing locked experiment')
        StudyXExperiment.objects.create(
            study=study, experiment=locked_experiment, experiment_order=1,
        )
        StudyXExperiment.objects.create(
            study=study, experiment=self.experiments[1], experiment_order=2,
        )

        response = self.client.get(reverse('study_update', args=[study.pk]))
        self.assertContains(response, 'Locked')
        self.assertContains(response, f'value="{locked_experiment.pk}" selected')

    def test_study_must_have_at_least_two_experiments(self):
        response = self.client.post(
            reverse('study_create'),
            self.formset_data([self.experiments[0].pk, None]),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Study.objects.exists())
        self.assertContains(
            response, 'A study must contain at least two experiments.',
            status_code=400,
        )

    def test_duplicate_experiment_is_rejected(self):
        response = self.client.post(
            reverse('study_create'),
            self.formset_data([self.experiments[0].pk, self.experiments[0].pk]),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Study.objects.exists())
        self.assertContains(
            response, 'An experiment can appear only once', status_code=400,
        )

    def test_update_reorders_experiments_and_compacts_order(self):
        study = Study.objects.create(title='Ordered study')
        links = [
            StudyXExperiment.objects.create(
                study=study, experiment=experiment, experiment_order=index,
            )
            for index, experiment in enumerate(self.experiments[:3], start=1)
        ]
        data = self.formset_data(
            [link.experiment_id for link in links],
            initial_rows=links,
        )
        # The formset's ORDER values control ordering independently from row order.
        data['studyxexperiment_set-0-ORDER'] = '3'
        data['studyxexperiment_set-1-ORDER'] = '1'
        data['studyxexperiment_set-2-ORDER'] = '2'
        data['title'] = 'Reordered study'

        response = self.client.post(reverse('study_update', args=[study.pk]), data)
        self.assertEqual(
            response.status_code, 302,
            'Study update should redirect after a valid reordered formset.',
        )
        self.assertEqual(response['Location'], reverse('study_update', args=[study.pk]))
        self.assertEqual(
            list(study.studyxexperiment_set.order_by('experiment_order').values_list(
                'experiment_id', flat=True,
            )),
            [self.experiments[1].pk, self.experiments[2].pk, self.experiments[0].pk],
        )

    def test_update_can_remove_and_add_experiments_without_modifying_experiments(self):
        study = Study.objects.create(title='Ordered study')
        links = [
            StudyXExperiment.objects.create(
                study=study, experiment=experiment, experiment_order=index,
            )
            for index, experiment in enumerate(self.experiments[:3], start=1)
        ]
        original_titles = list(Experiment.objects.values_list('pk', 'title'))
        data = self.formset_data(
            [link.experiment_id for link in links] + [self.experiments[3].pk],
            initial_rows=links,
            deleted_rows=(2,),
        )

        response = self.client.post(reverse('study_update', args=[study.pk]), data)
        self.assertRedirects(response, reverse('study_update', args=[study.pk]))
        self.assertEqual(
            list(study.studyxexperiment_set.order_by('experiment_order').values_list(
                'experiment_id', flat=True,
            )),
            [self.experiments[0].pk, self.experiments[1].pk, self.experiments[3].pk],
        )
        self.assertEqual(list(Experiment.objects.values_list('pk', 'title')), original_titles)

    def test_failed_formset_does_not_partially_update_study(self):
        study = Study.objects.create(title='Original title')
        existing = [
            StudyXExperiment.objects.create(
                study=study, experiment=experiment, experiment_order=index,
            )
            for index, experiment in enumerate(self.experiments[:2], start=1)
        ]
        data = self.formset_data(
            [existing[0].experiment_id, self.experiments[0].pk],
            initial_rows=existing,
        )
        data['title'] = 'Should not be saved'

        response = self.client.post(reverse('study_update', args=[study.pk]), data)
        self.assertEqual(response.status_code, 400)
        study.refresh_from_db()
        self.assertEqual(study.title, 'Original title')
        self.assertEqual(study.studyxexperiment_set.count(), 2)

    def test_editor_access_is_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('study_list')).status_code, 302)
        user = get_user_model().objects.create_user('unassigned')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('study_list')).status_code, 403)
        self.assertEqual(self.client.post(reverse('study_create'), {}).status_code, 403)
