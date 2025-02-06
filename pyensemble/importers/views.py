# importers.py
import os, csv, io
import json

from django.shortcuts import render

from pyensemble.models import Experiment, Form, Question, ExperimentXForm, FormXQuestion, DataFormat

from .forms import ImportForm, ImportStimuliForm
from pyensemble.importers import tasks

import pdb

def import_home(request):
    return render(request, 'pyensemble/importers/import_home.html')


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


def import_stimuli(request):
    template = 'pyensemble/importers/import_stimuli.html'

    if request.method == 'POST':
        form = ImportStimuliForm(request.POST, request.FILES)

        if form.is_valid():
            result = form.extract_and_save_stimuli()

            context = {
                'result': result,
            }

            return render(request, 'pyensemble/importers/import_results.html', context)
    else:
        form = ImportStimuliForm()

    context = {'form': form}

    return render(request, template, context)


def import_stimulus_table(request):
    template = 'pyensemble/importers/import_stimuli.html'

    if request.method == 'POST':
        form = ImportStimuliForm(request.POST, request.FILES)

        if form.is_valid():
            result = tasks.process_stimulus_table(form.cleaned_data)

            context = {
                'result': result,
            }

            return render(request, 'pyensemble/importers/import_results.html', context)
    else:
        form = ImportStimuliForm()

    context = {'form': form}

    return render(request, template, context)


# Experiment importer that uses the ExperimentSerializer
def import_json(request):
    # Define our GET method
    if request.method == 'POST':
        # Create a new form instance
        form = ImportForm(request.POST, request.FILES)

        # Check if the form is valid
        if form.is_valid():
            # Get the file
            file = request.FILES['file']

            # Get the file extension
            _, file_extension = os.path.splitext(file.name)

            # Check if the file is a JSON file
            if file_extension == '.json':
                # Load the JSON file
                json_data = json.load(file)

                # Determine the model class of the JSON data
                model_class = json_data.get('model_class', None)

                if model_class == 'Experiment':
                    new_experiment = import_json_experiment(json_data)

                elif model_class == 'Form':
                    new_form = import_json_form(json_data)

                elif model_class == 'Question':
                    new_question = import_json_question(json_data)

                else:
                    raise ValueError('Invalid model class')
               
            else:
                raise ValueError('Invalid file type')
            
            # Return a success message
            return render(request, 'pyensemble/message.html', {'msg': 'Successfully imported the file contents'})

    elif request.method == 'GET':
        # Create a new form
        form = ImportForm()

        # Render the form
        return render(request, 'pyensemble/importers/import_generic.html', {'form': form})
    

def import_json_experiment(json_data):
    # Create an Experiment instance
    experiment, created = Experiment.objects.get_or_create(
        title=json_data['title'],
        description=json_data['description'],
        start_date=json_data['start_date'],
        end_date=json_data['end_date'],
        irb_id=json_data['irb_id'],
        language=json_data['language'],
        params=json_data['params'],
        locked=json_data['locked'],
        is_group=json_data['is_group'],
        user_ticket_expected=json_data['user_ticket_expected'],
        sona_url=json_data['sona_url'],
        session_reporting_script=json_data['session_reporting_script'],
        post_session_callback=json_data['post_session_callback'])
    
    # Clobber existing ExperimentXForm instances
    if not created:
        experiment.experimentxform_set.all().delete()

    # Iterate over the ExperimentXForm instances
    for exf_data in json_data['exf_instances']:
        # Get the form data
        form_data = exf_data['form']

        form = import_json_form(form_data)

        # Create a new ExperimentXForm instance
        ExperimentXForm.objects.create(
            experiment=experiment,
            form=form,
            form_order=exf_data['form_order'],
            form_handler=exf_data['form_handler'],
            goto=exf_data['goto'],
            repeat=exf_data['repeat'],
            condition=exf_data['condition'],
            condition_script=exf_data['condition_script'],
            stimulus_script=exf_data['stimulus_script'],
            record_response_script=exf_data['record_response_script'],
            break_loop_button=exf_data['break_loop_button'],
            break_loop_button_text=exf_data['break_loop_button_text'],
            continue_button_text=exf_data['continue_button_text'],
            use_clientside_validation=exf_data['use_clientside_validation'],
            )
        
    return experiment


def import_json_form(json_data):
    # Create a new Form instance
    form, created = Form.objects.get_or_create(
        name=json_data['name'],
        category=json_data['category'],
        header=json_data['header'],
        footer=json_data['footer'],
        header_audio_path=json_data['header_audio_path'],
        footer_audio_path=json_data['footer_audio_path'],
        version=json_data['version'],
        locked=json_data['locked'],
        visit_once=json_data['visit_once']
    )

    # We're forcing an overwrite of the existing FormXQuestion instances
    # Delete the existing FormXQuestion instances
    form.formxquestion_set.all().delete()

    # Iterate over the FormXQuestion instances
    for fxq_data in json_data['fxq_instances']:
        # Get the question data
        question_data = fxq_data['question']

        question = import_json_question(question_data)

        # Create a new Form X Question instance
        FormXQuestion.objects.create(
            form=form,
            question=question,
            form_question_num=fxq_data['form_question_num'],
            question_iteration=fxq_data['question_iteration'],
            required=fxq_data['required']
        )

    return form


def import_json_question(json_data):
    # Check whether the data format already exists
    # We have to do this with get_or_create on only the fields that are unique
    data_format, created = DataFormat.objects.get_or_create(
        df_type=json_data['data_format']['df_type'],
        enum_values=json_data['data_format']['enum_values'])
    
    # If we created it, set the remaining fields
    if created:
        data_format.update(
            _range_hash=json_data['data_format']['_range_hash'],
            range_data=json_data['data_format']['range_data'],
        )

    # Create a new Question instance
    question, created = Question.objects.get_or_create(
        _unique_hash=json_data['_unique_hash'],
        text=json_data['text'],
        category=json_data['category'],
        locked=json_data['locked'],
        value_range=json_data['value_range'],
        value_default=json_data['value_default'],
        html_field_type=json_data['html_field_type'],
        audio_path=json_data['audio_path'],
        data_format=data_format
    )

    return question