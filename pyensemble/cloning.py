from django.db import transaction

from pyensemble.models import (
    DefinitionWriteMutex,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Study,
    StudyXExperiment,
)


_LOCK_FIELDS = {
    'locked',
    'locked_at',
    'locked_by',
    'lock_reason',
    'lock_snapshot',
    'lock_snapshot_digest',
    'release_identifier',
}


def _copy_model_fields(instance, *, excluded_fields):
    return {
        field.attname: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if not field.primary_key and field.name not in excluded_fields
    }


def clone_experiment(source, title):
    with transaction.atomic():
        DefinitionWriteMutex.objects.select_for_update().get(pk=1)
        source = Experiment.objects.select_for_update().get(pk=source.pk)
        values = _copy_model_fields(
            source,
            excluded_fields=_LOCK_FIELDS | {'title'},
        )
        clone = Experiment.objects.create(title=title, **values)

        rows = [
            ExperimentXForm(
                **_copy_model_fields(
                    row,
                    excluded_fields={'experiment'},
                ),
                experiment=clone,
            )
            for row in source.experimentxform_set.order_by('form_order', 'pk')
        ]
        ExperimentXForm.objects.bulk_create(rows)
        return clone


def clone_form(source, name):
    with transaction.atomic():
        DefinitionWriteMutex.objects.select_for_update().get(pk=1)
        source = Form.objects.select_for_update().get(pk=source.pk)
        values = _copy_model_fields(
            source,
            excluded_fields=_LOCK_FIELDS | {'name'},
        )
        clone = Form.objects.create(name=name, **values)

        rows = [
            FormXQuestion(
                **_copy_model_fields(
                    row,
                    excluded_fields={'form'},
                ),
                form=clone,
            )
            for row in source.formxquestion_set.order_by(
                'form_question_num',
                'question_iteration',
                'pk',
            )
        ]
        FormXQuestion.objects.bulk_create(rows)
        return clone


def clone_study(source, title):
    with transaction.atomic():
        DefinitionWriteMutex.objects.select_for_update().get(pk=1)
        source = Study.objects.select_for_update().get(pk=source.pk)
        values = _copy_model_fields(
            source,
            excluded_fields=_LOCK_FIELDS | {'title'},
        )
        clone = Study.objects.create(title=title, **values)

        rows = [
            StudyXExperiment(
                **_copy_model_fields(
                    row,
                    excluded_fields={'study'},
                ),
                study=clone,
            )
            for row in source.studyxexperiment_set.order_by(
                'experiment_order',
                'pk',
            )
        ]
        StudyXExperiment.objects.bulk_create(rows)
        return clone
