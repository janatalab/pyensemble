from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from pyensemble.access import Role, has_role
from pyensemble.locking import _is_protected
from pyensemble.models import (
    DataFormat,
    DefinitionWriteMutex,
    Experiment,
    ExperimentXForm,
    Form,
    FormXQuestion,
    Question,
)


LOCK_FIELDS = {
    'locked',
    'locked_at',
    'locked_by',
    'lock_reason',
    'lock_snapshot',
    'lock_snapshot_digest',
    'release_identifier',
}
DERIVED_FIELDS = {'_unique_hash', '_range_hash'}
ENTITY_CHILDREN = {
    Experiment: {'exf_instances'},
    Form: {'fxq_instances'},
    Question: {'data_format'},
}
STRUCTURE_KEYS = {
    'model_class',
    'id',
    'experiment',
    'form',
    'question',
    'forms',
    'questions',
}


class ImportConflict(ValueError):
    def __init__(self, message, *, can_rename=False):
        super().__init__(message)
        self.can_rename = can_rename


class _DryRunComplete(Exception):
    def __init__(self, result):
        self.result = result


class _PreflightComplete(Exception):
    pass


def _model_for_payload(payload):
    if not isinstance(payload, dict):
        raise ImportConflict('The import must contain one definition object.')
    model_name = payload.get('model_class')
    models = {
        'Experiment': Experiment,
        'Form': Form,
        'Question': Question,
    }
    try:
        return models[model_name]
    except (KeyError, TypeError) as error:
        raise ImportConflict('The import must contain an Experiment, Form, or Question.') from error


def _field_values(model, payload):
    fields = {
        field.name: field
        for field in model._meta.concrete_fields
        if not field.primary_key
    }
    allowed_keys = (
        set(fields)
        | DERIVED_FIELDS
        | LOCK_FIELDS
        | STRUCTURE_KEYS
        | ENTITY_CHILDREN.get(model, set())
    )
    unknown_keys = set(payload) - allowed_keys
    if unknown_keys:
        raise ImportConflict(
            'Unsupported fields in import: ' + ', '.join(sorted(unknown_keys)),
        )
    missing_fields = {
        name
        for name, field in fields.items()
        if not field.is_relation
        and name not in LOCK_FIELDS
        and name not in DERIVED_FIELDS
        and name not in payload
    }
    if missing_fields:
        raise ImportConflict(
            'The import is missing required definition fields: '
            + ', '.join(sorted(missing_fields)),
        )

    values = {}
    for name, field in fields.items():
        if name not in payload or name in LOCK_FIELDS or name in DERIVED_FIELDS:
            continue
        if field.is_relation:
            continue
        try:
            values[field.attname] = field.to_python(payload[name])
        except (TypeError, ValueError, ValidationError) as error:
            raise ImportConflict(f'Invalid value for {name}.') from error
    return values


def _is_exact(instance, values, relations=None):
    if any(
        getattr(instance, field_name) != value
        for field_name, value in values.items()
    ):
        return False
    for field_name, related in (relations or {}).items():
        if getattr(instance, field_name) != related:
            return False
    return True


def _resolve_data_format(payload):
    values = _field_values(DataFormat, payload)
    if not values.get('df_type'):
        raise ImportConflict('An imported question must specify a data format type.')
    lookup = {
        'df_type': values['df_type'],
        'enum_values': values.get('enum_values'),
    }
    instance = DataFormat.objects.filter(**lookup).first()
    if instance:
        if not _is_exact(instance, values):
            message = 'An existing data format has different range data.'
            if _is_protected(instance):
                message = 'The import conflicts with a locked data format.'
            raise ImportConflict(message)
        return instance
    return DataFormat.objects.create(**values)


def _match_or_create(
    model,
    payload,
    identity_fields,
    *,
    relations=None,
    can_rename_on_conflict=False,
):
    values = _field_values(model, payload)
    relations = relations or {}
    if any(
        name not in values or values[name] in (None, '')
        for name in identity_fields
    ):
        raise ImportConflict(
            f'An imported {model.__name__} is missing its identity fields.',
        )

    lookup = {name: values[name] for name in identity_fields}
    instance = model.objects.filter(**lookup).first()
    if instance:
        if not _is_exact(instance, values, relations):
            message = (
                f'The import conflicts with the existing {model.__name__} '
                f'identified by {", ".join(identity_fields)}.'
            )
            if _is_protected(instance):
                message = f'The import conflicts with a locked {model.__name__}.'
            raise ImportConflict(
                message,
                can_rename=can_rename_on_conflict,
            )
        return instance, False

    return model.objects.create(**values, **relations), True


def _relationship_values(model, payload, excluded):
    values = _field_values(model, payload)
    for name in excluded:
        field = model._meta.get_field(name)
        values.pop(field.attname, None)
    return values


def _relationship_is_exact(instance, values, relation_fields):
    if not _is_exact(instance, values):
        return False
    return all(
        getattr(instance, f'{field_name}_id') == related.pk
        for field_name, related in relation_fields.items()
    )


def _resolve_question(payload):
    data_format_payload = payload.get('data_format')
    if not isinstance(data_format_payload, dict):
        raise ImportConflict('An imported question is missing its data format.')
    data_format = _resolve_data_format(data_format_payload)
    values = _field_values(Question, payload)
    if 'text' not in values:
        raise ImportConflict('An imported question is missing its text.')
    return _match_or_create(
        Question,
        payload,
        ('text',),
        relations={'data_format': data_format},
    )[0]


def _resolve_form(payload, *, can_rename_on_conflict=False):
    rows = payload.get('fxq_instances', [])
    if not isinstance(rows, list):
        raise ImportConflict('Form question memberships must be a list.')
    question_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ImportConflict('Each form membership must be an object.')
        question_payload = row.get('question')
        if not isinstance(question_payload, dict):
            raise ImportConflict('A form membership is missing its question.')
        question = _resolve_question(question_payload)
        values = _relationship_values(FormXQuestion, row, {'form', 'question'})
        question_rows.append((question, values))
    question_rows.sort(
        key=lambda item: (
            item[1].get('form_question_num', 0),
            item[1].get('question_iteration', 1),
            item[0].pk,
        ),
    )

    form, created = _match_or_create(
        Form,
        payload,
        ('name',),
        can_rename_on_conflict=can_rename_on_conflict,
    )
    if created:
        for question, values in question_rows:
            FormXQuestion.objects.create(
                form=form,
                question=question,
                **values,
            )
        return form

    existing_rows = list(
        FormXQuestion.objects.filter(form=form).order_by(
            'form_question_num',
            'question_iteration',
            'pk',
        ),
    )
    exact = len(existing_rows) == len(question_rows) and all(
        _relationship_is_exact(row, values, {'question': question})
        for row, (question, values) in zip(existing_rows, question_rows)
    )
    if not exact:
        message = 'The import conflicts with the existing Form questions.'
        if _is_protected(form):
            message = 'The import conflicts with a locked Form.'
        raise ImportConflict(
            message,
            can_rename=can_rename_on_conflict,
        )
    return form


def _resolve_experiment(payload):
    rows = payload.get('exf_instances', [])
    if not isinstance(rows, list):
        raise ImportConflict('Experiment form memberships must be a list.')
    form_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ImportConflict('Each experiment membership must be an object.')
        form_payload = row.get('form')
        if not isinstance(form_payload, dict):
            raise ImportConflict('An experiment membership is missing its Form.')
        form = _resolve_form(form_payload)
        values = _relationship_values(ExperimentXForm, row, {'experiment', 'form'})
        form_rows.append((form, values))
    form_rows.sort(key=lambda item: (item[1].get('form_order', 0), item[0].pk))

    experiment, created = _match_or_create(
        Experiment,
        payload,
        ('title',),
        can_rename_on_conflict=True,
    )
    if created:
        for form, values in form_rows:
            ExperimentXForm.objects.create(
                experiment=experiment,
                form=form,
                **values,
            )
        return experiment

    existing_rows = list(
        ExperimentXForm.objects.filter(experiment=experiment).order_by(
            'form_order',
            'pk',
        ),
    )
    exact = len(existing_rows) == len(form_rows) and all(
        _relationship_is_exact(row, values, {'form': form})
        for row, (form, values) in zip(existing_rows, form_rows)
    )
    if not exact:
        message = 'The import conflicts with the existing Experiment forms.'
        if _is_protected(experiment):
            message = 'The import conflicts with a locked Experiment.'
        raise ImportConflict(message, can_rename=True)
    return experiment


def _update_root(target, payload):
    model = _model_for_payload(payload)
    if not isinstance(target, model):
        raise ImportConflict(
            f'The selected target is not an imported {model.__name__}.',
        )
    if _is_protected(target):
        raise ImportConflict(
            f'The selected {model.__name__} is locked and cannot be updated.',
        )

    values = _field_values(model, payload)
    if model is Question:
        data_format = _resolve_data_format(payload.get('data_format', {}))
        target.data_format = data_format
    for name, value in values.items():
        setattr(target, name, value)
    identity_field = {
        Experiment: 'title',
        Form: 'name',
        Question: 'text',
    }[model]
    if model.objects.filter(
        **{identity_field: getattr(target, identity_field)},
    ).exclude(pk=target.pk).exists():
        raise ImportConflict(
            f'Another {model.__name__} already uses that {identity_field}.',
        )
    target.save()

    if model is Form:
        rows = payload.get('fxq_instances', [])
        if not isinstance(rows, list):
            raise ImportConflict('Form question memberships must be a list.')
        parsed_rows = []
        for row in rows:
            if not isinstance(row, dict):
                raise ImportConflict('Each form membership must be an object.')
            question = _resolve_question(row.get('question', {}))
            values = _relationship_values(FormXQuestion, row, {'form', 'question'})
            parsed_rows.append((question, values))
        target.formxquestion_set.all().delete()
        for question, row_values in parsed_rows:
            FormXQuestion.objects.create(
                form=target,
                question=question,
                **row_values,
            )
    elif model is Experiment:
        rows = payload.get('exf_instances', [])
        if not isinstance(rows, list):
            raise ImportConflict('Experiment form memberships must be a list.')
        parsed_rows = []
        for row in rows:
            if not isinstance(row, dict):
                raise ImportConflict('Each experiment membership must be an object.')
            form = _resolve_form(row.get('form', {}))
            values = _relationship_values(ExperimentXForm, row, {'experiment', 'form'})
            parsed_rows.append((form, values))
        target.experimentxform_set.all().delete()
        for form, row_values in parsed_rows:
            ExperimentXForm.objects.create(
                experiment=target,
                form=form,
                **row_values,
            )
    return target


def import_definition(payload, *, mode, actor, target_id=None, new_name=''):
    """Import an exported definition graph under the shared definition mutex."""
    if not getattr(actor, 'is_authenticated', False) or not has_role(
        actor,
        Role.EDITOR,
    ):
        raise PermissionDenied('Editor access is required to import definitions.')
    if mode not in {'create', 'update', 'validate'}:
        raise ImportConflict('Choose create, update, or validate mode.')
    model = _model_for_payload(payload)
    new_name = (new_name or '').strip()
    is_create_validation = mode == 'validate' and target_id is None
    if (
        model in {Experiment, Form}
        and (mode == 'create' or is_create_validation)
        and new_name
    ):
        payload = dict(payload)
        payload['title' if model is Experiment else 'name'] = new_name

    def execute():
        update_mode = mode == 'update' or (
            mode == 'validate' and target_id is not None
        )
        if update_mode:
            if not target_id:
                raise ImportConflict('Select the draft to update.')
            try:
                target = model.objects.select_for_update().get(pk=target_id)
            except model.DoesNotExist as error:
                raise ImportConflict(
                    f'No {model.__name__} with that ID exists.',
                ) from error
            result = _update_root(target, payload)
            action = 'updated'
        elif model is Experiment:
            identity_field = 'title'
            already_exists = model.objects.filter(
                **{identity_field: payload.get(identity_field)},
            ).exists()
            result = _resolve_experiment(payload)
            action = 'already existed' if already_exists else 'created'
        elif model is Form:
            identity_field = 'name'
            already_exists = model.objects.filter(
                **{identity_field: payload.get(identity_field)},
            ).exists()
            result = _resolve_form(
                payload,
                can_rename_on_conflict=True,
            )
            action = 'already existed' if already_exists else 'created'
        else:
            already_exists = model.objects.filter(
                text=payload.get('text'),
            ).exists()
            result = _resolve_question(payload)
            action = 'already existed' if already_exists else 'created'
        return {
            'model': model.__name__,
            'id': result.pk,
            'label': str(result),
            'action': action,
            'dry_run': mode == 'validate',
        }

    try:
        with transaction.atomic():
            DefinitionWriteMutex.objects.select_for_update().get(pk=1)
            if mode == 'validate':
                raise _DryRunComplete(execute())
            try:
                with transaction.atomic():
                    execute()
                    raise _PreflightComplete()
            except _PreflightComplete:
                pass
            return execute()
    except _DryRunComplete as complete:
        return complete.result


def legacy_rows_to_payload(rows):
    """Convert flattened legacy rows into the exported-definition structure."""
    if not rows:
        raise ImportConflict('The legacy import file contains no data rows.')

    def value(row, *keys, default=''):
        for key in keys:
            if key in row:
                return row[key]
        return default

    def boolean(raw, default=None):
        if raw in (None, ''):
            return default
        if isinstance(raw, bool):
            return raw
        value = str(raw).strip().lower()
        if value in {'t', 'true', '1', 'yes'}:
            return True
        if value in {'f', 'false', '0', 'no'}:
            return False
        raise ImportConflict(f'Invalid boolean value in legacy import: {raw}')

    first = rows[0]
    experiment = {
        'model_class': 'Experiment',
        'title': value(first, 'experiment_title'),
        'description': value(first, 'experiment_description'),
        'start_date': value(first, 'start_date') or None,
        'end_date': value(first, 'end_date') or None,
        'irb_id': value(first, 'irb_id'),
        'language': value(first, 'language', default='en') or 'en',
        'play_question_audio': boolean(value(first, 'play_question_audio'), False),
        'params': value(first, 'params'),
        'is_group': boolean(value(first, 'is_group'), False),
        'user_ticket_expected': boolean(
            value(first, 'user_ticket_expected'),
            False,
        ),
        'sona_url': value(first, 'sona_url'),
        'session_reporting_script': value(first, 'session_reporting_script'),
        'post_session_callback': value(first, 'post_session_callback'),
        'exf_instances': [],
    }
    forms_by_key = {}
    if any(not isinstance(row, dict) for row in rows):
        raise ImportConflict('Each legacy import row must be an object.')

    for row in rows:
        if value(row, 'heading_format') == 'multi-question':
            raise ImportConflict(
                'Legacy multi-question headings are not supported; no data was imported.',
            )

        order = value(row, 'form_order', default='1')
        form_name = value(row, 'form_name')
        form_key = (str(order), str(form_name))
        if form_key not in forms_by_key:
            form_payload = {
                'model_class': 'Form',
                'name': form_name,
                'category': value(row, 'form_category'),
                'header': value(row, 'header'),
                'footer': value(row, 'footer'),
                'header_audio_path': value(row, 'header_audio_path'),
                'footer_audio_path': value(row, 'footer_audio_path'),
                'version': value(row, 'version') or None,
                'visit_once': boolean(value(row, 'visit_once'), False),
                'fxq_instances': [],
            }
            exf_payload = {
                'model_class': 'ExperimentXForm',
                'form_order': order,
                'form_handler': value(row, 'form_handler', default='form_generic'),
                'goto': value(row, 'goto') or None,
                'repeat': value(row, 'repeat') or None,
                'condition': value(row, 'condition'),
                'condition_script': value(row, 'condition_script', 'condition_matlab'),
                'stimulus_script': value(row, 'stimulus_script', 'stimulus_matlab'),
                'record_response_script': value(row, 'record_response_script'),
                'break_loop_button': boolean(
                    value(row, 'break_loop_button'),
                    False,
                ),
                'break_loop_button_text': value(row, 'break_loop_button_text'),
                'continue_button_text': value(
                    row,
                    'continue_button_text',
                    default='Next',
                ) or 'Next',
                'use_clientside_validation': boolean(
                    value(row, 'use_clientside_validation'),
                    False,
                ),
                'form': form_payload,
            }
            forms_by_key[form_key] = exf_payload
            experiment['exf_instances'].append(exf_payload)

        question_text = value(row, 'question_text')
        if not question_text:
            continue
        data_format = {
            'model_class': 'DataFormat',
            'df_type': value(row, 'type', default='text') or 'text',
            'enum_values': value(row, 'enum_values') or None,
            'range_data': None,
        }
        question = {
            'model_class': 'Question',
            'text': question_text,
            'category': value(row, 'question_category'),
            'value_range': value(row, 'range'),
            'value_default': value(row, 'default'),
            'html_field_type': value(row, 'html_field_type', default='text') or 'text',
            'audio_path': value(row, 'audio_path'),
            'data_format': data_format,
        }
        forms_by_key[form_key]['form']['fxq_instances'].append({
            'model_class': 'FormXQuestion',
            'form_question_num': value(row, 'form_question_num', default='1'),
            'question_iteration': value(row, 'question_iteration', default='1'),
            'required': boolean(value(row, 'required'), True),
            'question': question,
        })
    return experiment
