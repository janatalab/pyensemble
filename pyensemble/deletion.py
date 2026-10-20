from django.core.exceptions import PermissionDenied
from django.db import transaction

from pyensemble.access import Role, has_role
from pyensemble.locking import (
    LockedDefinitionError,
    _is_protected,
    definition_deletion,
)
from pyensemble.models import (
    DataFormat,
    DefinitionDeletionLog,
    DefinitionWriteMutex,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Question,
    Study,
    StudyXExperiment,
)


class DefinitionDeletionBlocked(PermissionDenied):
    def __init__(self, blockers):
        self.blockers = blockers
        super().__init__('This definition cannot be deleted: ' + '; '.join(blockers))


DELETABLE_MODELS = {
    'study': Study,
    'experiment': Experiment,
    'form': Form,
    'question': Question,
    'enum': DataFormat,
}


def definition_label(instance):
    if isinstance(instance, Study):
        return instance.title
    if isinstance(instance, Experiment):
        return instance.title
    if isinstance(instance, Form):
        return instance.name
    if isinstance(instance, Question):
        return instance.text
    if isinstance(instance, DataFormat):
        return instance.choice()
    if isinstance(instance, (ExperimentXForm, FormXQuestion, StudyXExperiment)):
        return str(instance)
    return str(instance)


def _reference_blocker(label, queryset):
    count = queryset.count()
    if count:
        return f'{label} ({count})'
    return None


def get_deletion_blockers(instance):
    from pyensemble.models import (
        ExperimentFile,
        ExperimentXAttribute,
        ExperimentXForm,
        ExperimentXStimulus,
        FormXQuestion,
        Notification,
        Response,
        Session,
        StudyXExperiment,
        Ticket,
    )
    from pyensemble.group.models import GroupSession

    blockers = []
    if _is_protected(instance):
        return ['The object or one of its locked parents is locked for production']

    if isinstance(instance, (ExperimentXForm, FormXQuestion, StudyXExperiment)):
        return blockers
    if isinstance(instance, Study):
        return blockers

    if isinstance(instance, Experiment):
        references = (
            ('Study memberships', StudyXExperiment.objects.filter(experiment=instance)),
            ('Participant sessions', Session.objects.filter(experiment=instance)),
            ('Group sessions', GroupSession.objects.filter(experiment=instance)),
            ('Responses', Response.objects.filter(experiment=instance)),
            ('Tickets', Ticket.objects.filter(experiment=instance)),
            ('Notifications', Notification.objects.filter(experiment=instance)),
            ('Experiment attributes', ExperimentXAttribute.objects.filter(experiment=instance)),
            ('Stimulus assignments', ExperimentXStimulus.objects.filter(experiment=instance)),
            ('Experiment files', ExperimentFile.objects.filter(experiment=instance)),
        )
    elif isinstance(instance, Form):
        references = (
            ('Experiment memberships', ExperimentXForm.objects.filter(form=instance)),
            ('Responses', Response.objects.filter(form=instance)),
        )
    elif isinstance(instance, Question):
        references = (
            ('Form memberships', FormXQuestion.objects.filter(question=instance)),
            ('Responses', Response.objects.filter(question=instance)),
        )
    elif isinstance(instance, DataFormat):
        references = (
            ('Questions using this data format', Question.objects.filter(data_format=instance)),
        )
    else:
        return [f'Unsupported definition type: {instance.__class__.__name__}']

    for label, queryset in references:
        blocker = _reference_blocker(label, queryset)
        if blocker:
            blockers.append(blocker)
    return blockers


def get_deletion_reference_counts(instance):
    from pyensemble.models import (
        ExperimentXForm,
        FormXQuestion,
        StudyXExperiment,
    )

    if isinstance(instance, Study):
        references = {
            'Study memberships removed': StudyXExperiment.objects.filter(study=instance),
        }
    elif isinstance(instance, Experiment):
        references = {
            'Experiment/form memberships removed': ExperimentXForm.objects.filter(experiment=instance),
        }
    elif isinstance(instance, Form):
        references = {
            'Form/question memberships removed': FormXQuestion.objects.filter(form=instance),
        }
    else:
        references = {}
    return {label: queryset.count() for label, queryset in references.items()}


def delete_definition(instance, actor, reason):
    if not getattr(actor, 'is_authenticated', False):
        raise PermissionDenied('An authenticated actor is required.')
    if not has_role(actor, Role.EDITOR):
        raise PermissionDenied('Editor access is required to delete definitions.')
    if not reason or not reason.strip():
        raise ValueError('A deletion reason is required.')

    with transaction.atomic():
        DefinitionWriteMutex.objects.select_for_update().get(pk=1)
        model = instance.__class__
        locked_instance = model.objects.select_for_update().get(pk=instance.pk)
        if _is_protected(locked_instance):
            raise DefinitionDeletionBlocked(
                ['The object or one of its locked parents is locked for production'],
            )

        blockers = get_deletion_blockers(locked_instance)
        if blockers:
            raise DefinitionDeletionBlocked(blockers)

        try:
            DefinitionDeletionLog.objects.create(
                actor=actor,
                model_name=locked_instance.__class__.__name__,
                target_id=str(locked_instance.pk),
                target_label=definition_label(locked_instance),
                reason=reason.strip(),
                reference_counts=get_deletion_reference_counts(locked_instance),
            )
            with definition_deletion():
                if isinstance(locked_instance, Study):
                    StudyXExperiment.objects.filter(
                        study=locked_instance,
                    ).delete()
                elif isinstance(locked_instance, Experiment):
                    ExperimentXForm.objects.filter(
                        experiment=locked_instance,
                    ).delete()
                elif isinstance(locked_instance, Form):
                    FormXQuestion.objects.filter(form=locked_instance).delete()
                return locked_instance.delete()
        except LockedDefinitionError as error:
            raise DefinitionDeletionBlocked([str(error)]) from error
