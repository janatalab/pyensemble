# importers.py
import os, csv, io
import json

from django.shortcuts import render

from pyensemble.models import Experiment, Form, Question, ExperimentXForm, FormXQuestion, DataFormat

from .forms import ImportForm
from pyensemble.importers import tasks

import pdb


def import_experiment_structure(request):
    # This method imports legacy Ensemble experiments for which information is exported using the following query.
    #
    # SELECT e.experiment_title, e.start_date, e.experiment_description, e.irb_id, e.end_date, e.language, e.play_question_audio, e.params, e.locked as experiment_locked,
    # f.form_name, f.form_category, f.header, f.footer, f.header_audio_path, f.footer_audio_path, f.version, f.locked as form_locked, f.visit_once, 
    # exf.form_order, exf.form_handler, exf.goto, exf.repeat, exf.condition, exf.condition_matlab, exf.stimulus_matlab,
    # fxq.form_question_num, fxq.question_iteration, 
    # q.question_text, q.question_category, q.heading_format, wq.locked as question_locked, 
    # qdf.subquestion, qdf.heading, qdf.range, qdf.default, qdf.html_field_type, qdf.audio_path, qdf.required,
    # df.*
    # FROM 
    # ensemble_main.experiment as e
    # LEFT JOIN ensemble_main.experiment_x_form as exf
    # ON exf.experiment_id = e.experiment_id
    # LEFT JOIN ensemble_main.form as f
    # ON f.form_id = exf.form_id
    # LEFT JOIN ensemble_main.form_x_question as fxq
    # ON fxq.form_id = f.form_id
    # LEFT JOIN ensemble_main.question as q
    # ON q.question_id = fxq.question_id
    # LEFT JOIN ensemble_main.question_x_data_format as qdf
    # ON qdf.question_id = q.question_id
    # LEFT JOIN ensemble_main.data_format as df
    # ON df.data_format_id = qdf.answer_format_id
    # WHERE e.experiment_title = 'musmemfmri_bio_pilot'
    # ORDER BY exf.form_order
    # ;

    template = 'pyensemble/importers/import_generic.html'

    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)

        if form.is_valid():
            content = None

            # Get our file
            filename = request.FILES['file'].name
            fstub,fext = os.path.splitext(filename)

            file = request.FILES['file'].file

            # Figure out what kind of file we're dealing with. JSON is a git better
            if fext == '.csv':
                csv_file = io.TextIOWrapper(file)  # python 3 only
                dialect = csv.Sniffer().sniff(csv_file.read(1024), delimiters=";,")
                csv_file.seek(0)
                reader = csv.reader(csv_file, dialect)

                # Get the column headers
                columns = next(reader)

                # Get a dictionary of column indexes
                cid = {col:idx for idx, col in enumerate(columns)}

                # Iterate over the rows
                for row in reader:
                    # Get or create our Experiment instance
                    experiment, created = Experiment.objects.get_or_create(
                        title=row[cid['experiment_title']],
                        description=row[cid['experiment_description']],
                        start_date=row[cid['start_date']],
                        end_date=row[cid['end_date']],
                        irb_id=row[cid['irb_id']],
                        language=row[cid['language']],
                        params=row[cid['params']],
                        locked=row[cid['locked']],
                        )

                    # Get or create our Form instance
                    form, created = Form.objects.get_or_create(
                        name=row[cid['form_name']],
                        category=row[cid['form_category']],
                        header=row[cid['header']],
                        footer=row[cid['footer']],
                        header_audio_path=row[cid['header_audio_path']],
                        footer_audio_path=row[cid['footer_audio_path']],
                        version=row[cid['version']],
                        locked=row[cid['locked']],
                        visit_once=row[cid['visit_once']],
                        )

                    # Create the Experiment X Form entry
                    exf, created = ExperimentXForm.objects.get_or_create(
                        experiment=experiment,
                        form=form,
                        form_order=row[cid['form_order']],
                        form_handler=row[cid['form_handler']],
                        goto=row[cid['goto']],
                        repeat=row[cid['repeat']],
                        )

                    # Create our DataFormat entry since we need to insert this into our question
                    data_format, created = DataFormat.objects.get_or_create(
                        df_type=row[cid['type']],
                        enum_values=row[cid['enum_values']],
                        )

                    # Create the Question entry
                    question, created = Question.objects.get_or_create(
                        text=row[cid['question_text']],
                        category=row[cid['question_category']],
                        locked=row[cid['locked']],
                        value_range=row[cid['range']],
                        value_default=row[cid['default']],
                        html_field_type=row[cid['html_field_type']],
                        audio_path=row[cid['audio_path']],
                        data_format=data_format,
                        )

                    # Create the FormxQuestion entry
                    fxq, created = FormXQuestion.objects.get_or_create(
                        form=form,
                        question=question,
                        form_question_num=row[cid['form_question_num']],
                        question_iteration=row[cid['question_iteration']],
                        required=row[cid['required']]
                        )

            elif fext == '.json':
                json_file = io.TextIOWrapper(file)
                jsondata = json.load(json_file)

                for row in jsondata:
                    if row['heading_format'] == 'multi-question':
                        print('multi-question import not supported')
                        continue

                    experiment, created = Experiment.objects.get_or_create(
                        title=row['experiment_title'],
                        description=tasks.clean_string(row['experiment_description']),
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        irb_id=tasks.clean_string(row['irb_id']),
                        language=tasks.clean_string(row['language']),
                        params=tasks.clean_string(row['params']),
                        locked=tasks.clean_boolean(row['experiment_locked']),
                        )

                    # Get or create our Form instance
                    form, created = Form.objects.get_or_create(
                        name=row['form_name'],
                        category=tasks.clean_string(row['form_category']),
                        header=tasks.clean_string(row['header']),
                        footer=tasks.clean_string(row['footer']),
                        header_audio_path=tasks.clean_string(row['header_audio_path']),
                        footer_audio_path=tasks.clean_string(row['footer_audio_path']),
                        version=row['version'],
                        locked=tasks.clean_boolean(row['form_locked']),
                        visit_once=tasks.clean_boolean(row['visit_once']),
                        )

                    # Create the Experiment X Form entry
                    exf, created = ExperimentXForm.objects.get_or_create(
                        experiment=experiment,
                        form=form,
                        form_order=row['form_order'],
                        form_handler=row['form_handler'],
                        goto=row['goto'],
                        repeat=row['repeat'],
                        condition=tasks.clean_string(row['condition']),
                        condition_script=tasks.clean_string(row['condition_matlab']),
                        stimulus_script=tasks.clean_string(row['stimulus_matlab']),
                        )

                    # Make sure we actually have a question in order to try to create entries
                    if not row['question_text']:
                        continue

                    # Create our DataFormat entry since we need to insert this into our question
                    data_format, created = DataFormat.objects.get_or_create(
                        df_type=row['type'],
                        enum_values=tasks.clean_string(row['enum_values']),
                        )

                    # Create the Question entry
                    # Have to handle this a bit differently due to the unique hash
                    try:
                        question = Question.objects.get(
                            text=row['question_text'],
                            category=tasks.clean_string(row['question_category']),
                            locked=tasks.clean_boolean(row['question_locked']),
                            value_range=tasks.clean_string(row['range']),
                            value_default=tasks.clean_string(row['default']),
                            html_field_type=tasks.clean_string(row['html_field_type']),
                            audio_path=tasks.clean_string(row['audio_path']),
                            data_format=data_format,
                            )

                    except:
                        question = Question(text=row['question_text'],
                            category=tasks.clean_string(row['question_category']),
                            locked=tasks.clean_boolean(row['question_locked']),
                            value_range=tasks.clean_string(row['range']),
                            value_default=tasks.clean_string(row['default']),
                            html_field_type=tasks.clean_string(row['html_field_type']),
                            audio_path=tasks.clean_string(row['audio_path']),
                            data_format=data_format,)

                        # Generate the question's hash
                        question.unique_hash

                        # Save it
                        question.save()

                    # Create the FormxQuestion entry
                    fxq, created = FormXQuestion.objects.get_or_create(
                        form=form,
                        question=question,
                        form_question_num=row['form_question_num'],
                        question_iteration=row['question_iteration'],
                        required=tasks.clean_boolean(row['required']),
                        )

            else:
                raise ValueError('Bad file type')

            return render(request,'pyensemble/message.html',{'msg':'Successfully imported the file contents'})

    else:
        form = ImportForm()

    context = {'form': form}

    return render(request, template, context)


def import_stimulus_table(request):
    template = 'pyensemble/importers/import_stimuli.html'

    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)

        if form.is_valid():
            result = tasks.process_stimulus_table(request.FILES['file'])

            context = {
                'result': result,
            }

            return render(request, 'pyensemble/importers/import_results.html', context)
    else:
        form = ImportForm()

    context = {'form': form}

    return render(request, template, context)


