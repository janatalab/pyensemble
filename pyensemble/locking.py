import copy
import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Manager, QuerySet
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from pyensemble.access import Role, has_role


_lock_transition = ContextVar('pyensemble_lock_transition', default=False)
_definition_deletion = ContextVar('pyensemble_definition_deletion', default=False)


class LockedDefinitionError(PermissionDenied):
    pass


def _locked_queryset(model, instance):
    from pyensemble.models import Experiment, Form, Study, StudyXExperiment

    pk = instance.pk

    if model == 'Study':
        return _has_locked_flag(instance)
    if model == 'Experiment':
        return _has_locked_flag(instance) or (
            pk is not None and instance.studyxexperiment_set.filter(
                study__locked=True,
            ).exists()
        )
    if model == 'Form':
        return _has_locked_flag(instance) or (
            pk is not None and (
                instance.experimentxform_set.filter(
                    experiment__locked=True,
                ).exists() or instance.experimentxform_set.filter(
                    experiment__studyxexperiment__study__locked=True,
                ).exists()
            )
        )
    if model == 'Question':
        return _has_locked_flag(instance) or (
            pk is not None and (
                instance.formxquestion_set.filter(
                    form__locked=True,
                ).exists() or instance.formxquestion_set.filter(
                    form__experimentxform__experiment__locked=True,
                ).exists() or instance.formxquestion_set.filter(
                    form__experimentxform__experiment__studyxexperiment__study__locked=True,
                ).exists()
            )
        )
    if model == 'DataFormat':
        from pyensemble.models import Question

        return pk is not None and Question.objects.filter(
            data_format=instance,
        ).filter(
            _protected_question_filter(),
        ).exists()
    if model == 'StudyXExperiment':
        return instance.study_id is not None and Study.objects.filter(
            pk=instance.study_id,
            locked=True,
        ).exists()
    if model == 'ExperimentXForm':
        return instance.experiment_id is not None and (
            Experiment.objects.filter(
                pk=instance.experiment_id,
                locked=True,
            ).exists() or StudyXExperiment.objects.filter(
                experiment_id=instance.experiment_id,
                study__locked=True,
            ).exists()
        )
    if model == 'FormXQuestion':
        return instance.form_id is not None and (
            Form.objects.filter(pk=instance.form_id, locked=True).exists()
            or instance.form.experimentxform_set.filter(
                experiment__locked=True,
            ).exists()
            or instance.form.experimentxform_set.filter(
                experiment__studyxexperiment__study__locked=True,
            ).exists()
        )
    return False


def _has_locked_flag(instance):
    if getattr(instance, 'locked', False):
        return True
    return instance.pk is not None and instance.__class__._base_manager.filter(
        pk=instance.pk,
        locked=True,
    ).exists()


def _protected_question_filter():
    from django.db.models import Q

    return Q(locked=True) | Q(
        formxquestion__form__locked=True,
    ) | Q(
        formxquestion__form__experimentxform__experiment__locked=True,
    ) | Q(
        formxquestion__form__experimentxform__experiment__studyxexperiment__study__locked=True,
    )


def _is_protected(instance):
    model_name = instance.__class__.__name__
    return _locked_queryset(model_name, instance)


def _values_differ(instance, previous):
    if previous is None:
        return True
    return any(
        getattr(instance, field.attname) != getattr(previous, field.attname)
        for field in instance._meta.concrete_fields
    )


def _assert_definition_write_allowed(instance, previous=None):
    if _lock_transition.get():
        return

    if previous is None and instance.pk is not None:
        previous = instance.__class__._base_manager.filter(pk=instance.pk).first()

    protected_before = previous is not None and _is_protected(previous)
    protected_after = _is_protected(instance)
    fields_changed = _values_differ(instance, previous)

    lock_fields = {
        'locked', 'locked_at', 'locked_by_id', 'lock_reason',
        'lock_snapshot', 'lock_snapshot_digest', 'release_identifier',
    }
    lock_fields_changed = any(
        getattr(instance, field.attname) != getattr(previous, field.attname)
        for field in instance._meta.concrete_fields
        if field.attname in lock_fields and previous is not None
    )
    if previous is None:
        lock_fields_changed = any(
            getattr(instance, field.attname) not in (None, False, '', {})
            for field in instance._meta.concrete_fields
            if field.attname in lock_fields
        )

    if lock_fields_changed:
        raise LockedDefinitionError(
            'Lock state and lock metadata can only be changed by the locking service.',
        )
    if fields_changed and (protected_before or protected_after):
        raise LockedDefinitionError(
            'This definition is locked for production and cannot be changed.',
        )


def _assert_delete_allowed(instance):
    if _lock_transition.get():
        return
    if _is_protected(instance):
        raise LockedDefinitionError(
            'This definition is locked for production and cannot be deleted.',
        )
    from pyensemble.deletion import get_deletion_blockers

    blockers = get_deletion_blockers(instance)
    if blockers:
        raise LockedDefinitionError(
            'This definition cannot be deleted: ' + '; '.join(blockers),
        )
    if instance.__class__.__name__ in {
        'Study', 'Experiment', 'Form', 'Question', 'DataFormat',
    } and not _definition_deletion.get():
        raise LockedDefinitionError(
            'Definitions must be deleted through the audited deletion service.',
        )


class DefinitionWriteMixin:
    def save(self, *args, **kwargs):
        from pyensemble.models import DefinitionWriteMutex

        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            previous = None
            if self.pk is not None:
                previous = self.__class__._base_manager.filter(pk=self.pk).first()
            _assert_definition_write_allowed(self, previous)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from pyensemble.models import DefinitionWriteMutex

        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            _assert_delete_allowed(self)
            return super().delete(*args, **kwargs)


class DefinitionWriteQuerySet(QuerySet):
    def update(self, **kwargs):
        from pyensemble.models import DefinitionWriteMutex

        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            for instance in self.select_for_update():
                proposed = copy.copy(instance)
                for field, value in kwargs.items():
                    setattr(proposed, field, value)
                _assert_definition_write_allowed(proposed, instance)
            return super().update(**kwargs)

    def delete(self):
        from pyensemble.models import DefinitionWriteMutex

        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            for instance in self.select_for_update():
                _assert_delete_allowed(instance)
            return super().delete()

    def bulk_create(self, objs, *args, **kwargs):
        from pyensemble.models import DefinitionWriteMutex

        objs = list(objs)
        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            for instance in objs:
                _assert_definition_write_allowed(instance)
            return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):
        from pyensemble.models import DefinitionWriteMutex

        objs = list(objs)
        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            for instance in objs:
                previous = self.model._base_manager.filter(pk=instance.pk).first()
                _assert_definition_write_allowed(instance, previous)
            return super().bulk_update(objs, fields, *args, **kwargs)


class DefinitionWriteManager(Manager.from_queryset(DefinitionWriteQuerySet)):
    pass


@contextmanager
def lock_transition():
    token = _lock_transition.set(True)
    try:
        yield
    finally:
        _lock_transition.reset(token)


@contextmanager
def definition_deletion():
    token = _definition_deletion.set(True)
    try:
        yield
    finally:
        _definition_deletion.reset(token)


_LOCK_METADATA_FIELDS = {
    'locked', 'locked_at', 'locked_by', 'lock_reason',
    'lock_snapshot', 'lock_snapshot_digest', 'release_identifier',
}


def _model_fields(instance):
    return {
        field.attname: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if field.name not in _LOCK_METADATA_FIELDS
    }


def _question_snapshot(question):
    return {
        'question': _model_fields(question),
        'data_format': _model_fields(question.data_format),
    }


def _form_snapshot(form):
    return {
        'form': _model_fields(form),
        'questions': [
            {
                'relationship': _model_fields(row),
                'question': _question_snapshot(row.question),
            }
            for row in form.formxquestion_set.select_related(
                'question__data_format',
            ).order_by('form_question_num', 'pk')
        ],
    }


def _experiment_snapshot(experiment):
    return {
        'experiment': _model_fields(experiment),
        'forms': [
            {
                'relationship': _model_fields(row),
                'form': _form_snapshot(row.form),
            }
            for row in experiment.experimentxform_set.select_related(
                'form',
            ).order_by('form_order', 'pk')
        ],
    }


def _definition_snapshot(instance):
    if instance.__class__.__name__ == 'Study':
        return {
            'study': _model_fields(instance),
            'experiments': [
                {
                    'relationship': _model_fields(row),
                    'experiment': _experiment_snapshot(row.experiment),
                }
                for row in instance.studyxexperiment_set.select_related(
                    'experiment',
                ).order_by('experiment_order', 'pk')
            ],
        }
    return _experiment_snapshot(instance)


def _lock_definition(instance, actor, reason, release_identifier):
    from pyensemble.models import DefinitionWriteMutex

    if not getattr(actor, 'is_authenticated', False):
        raise ValueError('An authenticated lock actor is required.')
    if not has_role(actor, Role.RELEASE_MANAGER):
        raise PermissionDenied(
            'Release manager access is required to lock production definitions.',
        )
    if not reason or not reason.strip():
        raise ValueError('A lock reason is required.')
    if not release_identifier or not release_identifier.strip():
        raise ValueError('A release identifier is required.')

    with transaction.atomic():
        DefinitionWriteMutex.objects.select_for_update().get(pk=1)
        instance = instance.__class__.objects.select_for_update().get(pk=instance.pk)
        if instance.locked:
            raise LockedDefinitionError('This definition is already locked.')
        if instance.__class__.__name__ == 'Study':
            experiment_ids = list(
                instance.studyxexperiment_set.order_by().values_list(
                    'experiment_id',
                    flat=True,
                ),
            )
            if len(experiment_ids) < 2 or len(experiment_ids) != len(set(experiment_ids)):
                raise ValueError(
                    'A Study must contain at least two distinct Experiments before locking.',
                )

        snapshot = _definition_snapshot(instance)
        serialized = json.dumps(
            snapshot,
            cls=DjangoJSONEncoder,
            sort_keys=True,
            separators=(',', ':'),
        )
        instance.locked = True
        instance.locked_at = timezone.now()
        instance.locked_by = actor
        instance.lock_reason = reason.strip()
        instance.lock_snapshot = snapshot
        instance.lock_snapshot_digest = hashlib.sha256(
            serialized.encode('utf-8'),
        ).hexdigest()
        instance.release_identifier = release_identifier.strip()

        with lock_transition():
            instance.save(update_fields=(
                'locked',
                'locked_at',
                'locked_by',
                'lock_reason',
                'lock_snapshot',
                'lock_snapshot_digest',
                'release_identifier',
            ))
    return instance


def lock_experiment(experiment, actor, reason, release_identifier):
    if experiment.__class__.__name__ != 'Experiment':
        raise TypeError('lock_experiment requires an Experiment.')
    return _lock_definition(experiment, actor, reason, release_identifier)


def lock_study(study, actor, reason, release_identifier):
    if study.__class__.__name__ != 'Study':
        raise TypeError('lock_study requires a Study.')
    return _lock_definition(study, actor, reason, release_identifier)
