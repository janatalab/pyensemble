import csv
import io
import json
import os

from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from pyensemble.access import Role, role_required
from pyensemble.importers.definitions import (
    ImportConflict,
    import_definition,
    legacy_rows_to_payload,
)
from pyensemble.importers.forms import ImportForm


def _submit_import(request, *, legacy=False):
    template = 'pyensemble/importers/import_generic.html'
    if request.method == 'GET':
        return render(request, template, {'form': ImportForm()})

    form = ImportForm(request.POST, request.FILES)
    if form.is_valid():
        uploaded_file = form.cleaned_data['file']
        extension = os.path.splitext(uploaded_file.name)[1].lower()
        try:
            if legacy:
                if extension == '.csv':
                    uploaded_file.seek(0)
                    csv_text = uploaded_file.read().decode('utf-8-sig')
                    try:
                        dialect = csv.Sniffer().sniff(
                            csv_text[:1024],
                            delimiters=';,',
                        )
                    except csv.Error as error:
                        raise ImportConflict(
                            'Could not determine the legacy CSV delimiter.',
                        ) from error
                    rows = list(
                        csv.DictReader(
                            io.StringIO(csv_text),
                            dialect=dialect,
                        ),
                    )
                    if any(None in row for row in rows):
                        raise ImportConflict(
                            'A legacy CSV row contains more values than its header.',
                        )
                    rows = [
                        {key.strip(): value for key, value in row.items()}
                        for row in rows
                    ]
                elif extension == '.json':
                    rows = json.load(uploaded_file)
                    if not isinstance(rows, list):
                        raise ImportConflict(
                            'Legacy JSON imports must contain a list of rows.',
                        )
                else:
                    raise ImportConflict('Choose a .csv or .json legacy file.')
                payload = legacy_rows_to_payload(rows)
            else:
                if extension != '.json':
                    raise ImportConflict('Choose a JSON definition export.')
                payload = json.load(uploaded_file)
                if not isinstance(payload, dict):
                    raise ImportConflict('The JSON file must contain one definition.')

            result = import_definition(
                payload,
                mode=form.cleaned_data['mode'],
                actor=request.user,
                target_id=form.cleaned_data.get('target_id'),
                new_name=form.cleaned_data.get('new_name', ''),
            )
        except (ImportConflict, json.JSONDecodeError, UnicodeDecodeError) as error:
            form.add_error(None, str(error))
            return render(request, template, {'form': form}, status=400)
        except PermissionDenied:
            raise

        if result['dry_run']:
            message = (
                f"Validation succeeded for {result['model']} "
                f"'{result['label']}'. No changes were saved."
            )
        else:
            message = (
                f"{result['model']} '{result['label']}' "
                f"was {result['action']}."
            )
        return render(request, 'pyensemble/message.html', {'msg': message})

    return render(request, template, {'form': form}, status=400)


@role_required(Role.EDITOR)
@require_http_methods(['GET', 'POST'])
def import_experiment_structure(request):
    return _submit_import(request, legacy=True)


@role_required(Role.EDITOR)
@require_http_methods(['GET', 'POST'])
def import_json(request):
    return _submit_import(request)
