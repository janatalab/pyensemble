# jingle_study.py

import os, csv, io, re
import random
import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
import django.forms as forms
from django.utils import timezone
from django.db.models import Q, Count, Min

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from pyensemble.models import Attribute, Stimulus, StimulusXAttribute, AttributeXAttribute, Experiment, Form, ExperimentXForm, Question, FormXQuestion, DataFormat

from pyensemble.forms import ImportForm

import pdb

# Specify the stimulus directory relative to the stimulus root
rootdir = 'jinglestims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

study_params = {
    'jingle_project_study1': {
        'age_ranges':[(6,16),(17,30),(31,64),(65,float('inf'))],
        'logo_duration_ms': 5000,
        'slogan_duration_ms': 5000,
    }
}

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Imports stimuli for Angela Nazarian's jingle study
def import_stims(stimdir=stimdir):
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimdir) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)

    for media_type in mediadirs:
        # Get an attribute corresponding to this media type
        attribute, _ = Attribute.objects.get_or_create(name='Media Type', attribute_class='stimulus')

        print(f'Working on {media_type}s ...')

        # Loop over files in the directory
        with os.scandir(os.path.join(stimdir,media_type)) as stimlist:
            for stim in stimlist:
                if not stim.name.startswith('.') and stim.is_file():
                    print(f'\tImporting {stim.name}')

                    # Strip off the extension
                    fstub,fext = os.path.splitext(stim.name)

                    # Create the stimulus object
                    stimulus, _ = Stimulus.objects.get_or_create(
                        name=fstub,
                        playlist='Jingle Study',
                        file_format=fext,
                        location=os.path.join(rootdir,media_type,stim.name)
                        )

                    # Create a stimulusXattribute entry
                    stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=media_type)

def import_experiment_structure(request):
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
                    experiment, created = Experiment.objects.get_or_create(
                        title=row['experiment_title'],
                        description=clean_string(row['experiment_description']),
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        irb_id=clean_string(row['irb_id']),
                        language=clean_string(row['language']),
                        params=clean_string(row['params']),
                        locked=clean_boolean(row['experiment_locked']),
                        )

                    # Get or create our Form instance
                    form, created = Form.objects.get_or_create(
                        name=row['form_name'],
                        category=clean_string(row['form_category']),
                        header=clean_string(row['header']),
                        footer=clean_string(row['footer']),
                        header_audio_path=clean_string(row['header_audio_path']),
                        footer_audio_path=clean_string(row['footer_audio_path']),
                        version=row['version'],
                        locked=clean_boolean(row['form_locked']),
                        visit_once=clean_boolean(row['visit_once']),
                        )

                    # Create the Experiment X Form entry
                    exf, created = ExperimentXForm.objects.get_or_create(
                        experiment=experiment,
                        form=form,
                        form_order=row['form_order'],
                        form_handler=row['form_handler'],
                        goto=row['goto'],
                        repeat=row['repeat'],
                        condition=clean_string(row['condition']),
                        condition_script=clean_string(row['condition_matlab']),
                        stimulus_script=clean_string(row['stimulus_matlab']),
                        )

                    # Make sure we actually have a question in order to try to create entries
                    if not row['question_text']:
                        continue

                    # Create our DataFormat entry since we need to insert this into our question
                    data_format, created = DataFormat.objects.get_or_create(
                        df_type=row['type'],
                        enum_values=clean_string(row['enum_values']),
                        )

                    # Create the Question entry
                    question, created = Question.objects.get_or_create(
                        text=row['question_text'],
                        category=clean_string(row['question_category']),
                        locked=clean_boolean(row['question_locked']),
                        value_range=clean_string(row['range']),
                        value_default=clean_string(row['default']),
                        html_field_type=clean_string(row['html_field_type']),
                        audio_path=clean_string(row['audio_path']),
                        data_format=data_format,
                        )

                    # Create the FormxQuestion entry
                    fxq, created = FormXQuestion.objects.get_or_create(
                        form=form,
                        question=question,
                        form_question_num=row['form_question_num'],
                        question_iteration=row['question_iteration'],
                        required=clean_boolean(row['required']),
                        )

            else:
                raise ValueError('Bad file type')

            return render(request,'pyensemble/message.html',{'msg':'Successfully imported the file contents'})

    else:
        form = ImportForm()

    context = {'form': form}

    return render(request, template, context)

def import_attributes(request):
    template = 'pyensemble/importers/import_generic.html'

    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)

        if form.is_valid():
            # Get our in-memory file
            csv_file = io.TextIOWrapper(request.FILES['file'].file)

            # Get a reader for our file
            reader = csv.reader(csv_file)

            # Get the column headers
            columns = next(reader)

            # Get a dictionary of column indexes
            cid = {col:idx for idx, col in enumerate(columns)}

            # Specify our column to attribute mapping
            colattmap = {
                'Company': 'Company',
                'Item': 'Product',
                'Product_Category': 'Product Category',
                'First_Played': 'First Played',
                'Last_Played': 'Last Played',
                'Region_Played': 'Region',
                'Modality': 'Modality',
            }
            numeric = ['First_Played','Last_Played']

            for row in reader:
                # Get a stimulus object based on the name
                stimname = row[cid['Stimulus_ID']]
                try:
                    stimulus = Stimulus.objects.get(name=stimname)
                except:
                    print(f'Unable to locate stimulus with name {stimname}')
                    continue

                # Iterate over our attributes
                for col in colattmap.keys():
                    # Fetch our attribute
                    attribute, created = Attribute.objects.get_or_create(name=colattmap[col])

                    # Get the value we're going to write
                    value = row[cid[col]]
                    if col in numeric:
                        value_text = ''
                        value_float = float(value) if value and value != '?' else None
                    else:
                        value_text = value
                        value_float = None

                    # Create our stimulusxattribute entry
                    sxa = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=value_text, attribute_value_double=value_float)

            return render(request,'pyensemble/message.html',{'msg':'Successfully imported the attribute file'})

    else:
        form = ImportForm()

    context = {'form': form}

    return render(request, template, context)

def clean_string(item):
    return item if item else ''

def clean_boolean(item):
    if item=='T':
        value = True
    elif item=='F':
        value=False
    else:
        value=None
    return value

def delete_exf(request,title):
    ExperimentXForm.objects.filter(experiment__title=title).delete()
    return render(request,'pyensemble/message.html',{'msg':f'Deleted experimentxform for {title}'})

def select_study1(request,*args,**kwargs):
    # Construct a jsPsych timeline
    # https://www.jspsych.org/overview/timeline/
    timeline = []

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our experiment session info
    expsessinfo = request.session['experiment_%d'%(session.experiment.id)]

    # Get our subject
    subject = session.subject

    # Get the date of birth of our participant
    dob = subject.dob

    # Determine the media year ranges
    age_ranges = params['age_ranges']
    media_year_ranges = [(dob+timezone.timedelta(years=r[0]),dob+timezone.timedelta(years=r[1])) for r in age_ranges]

    # Get our list of stimuli that this subject has already encountered
    presented_stims = Response.objects.filter(experiment=session.experiment, subject_id=subject).values('stimulus')

    # Get the last presented stimulus to this subject in this experiment
    previous_stim = presented_stims.last()

    #
    # Get our list of possible stimuli
    #

    # Exclude previously presented stimuli
    possible_stims = Stimulus.objects.exclude(stimulus__in=(presented_stims))

    # Exclude stimuli that are in the same advertisement grouping as any of the presented stimui
    for stim in presented_stims:
        # Get the grouping identifier
        match = re.match('^(?P<group_str>\d+)_',stim.name)
        group_str = match.groupdict()['group_str']
        possible_stims = possible_stims.exclude(name__iregex=r'^%s'%(group_str))

    # Exclude stimuli that have the same company as the previously presented stimulus
    company = StimulusXAttribute.objects.get(stimulus=previous_stim,attribute__name='Company').attribute_value_text
    possible_stims = possible_stims.exclude(stimulusxattribute__attribute_value_text=company)

    # Determine the number of times that each stimulus has been presented
    experiment_responses = Count('response', filter=Q(response__experiment=experiment))
    possible_stims = possible_stims.annotate(num_responses=experiment_responses)

    # Determine the existing media types
    media_types = StimulusXAttribute.objects.filter(stimulus__in=possible_stims,attribute__name='Media Type').values_list('attribute_value_text',flat=True).distinct()

    # Get the first and last played attributes
    first_attrib = Attribute.objects.get(name='First Played')
    last_attrib = Attribute.objects.get(name='Last Played')

    # Get the possible stimuli within each year range
    stims_x_agerange = []
    for r in media_year_ranges:
        stims_x_agerange.append(possible_stims
            .filter(
                stimulusxattribute__attribute=first_attrib, 
                stimulusxattribute__attribute_value_double__gte=r[0])
            .filter(
                stimulusxattribute__attribute=first_attrib,
                stimulusxattribute__attribute_value_double__lt=r[1]) 
            | possible_stims
            .filter(
                stimulusxattribute__attribute=last_attrib,
                stimulusxattribute__attribute_value_double__gte=r[0])
            .filter(
                stimulusxattribute__attribute=last_attrib,
                stimulusxattribute__attribute_value_double__lt=r[1])                
            )

    # Randomly pick a media type and year range
    media_idx = random.randrange(0,media_types.count())
    age_idx = random.randrange(0,len(stims_x_agerange))

    # Select from among the least played stimuli in the target category
    select_from_stims = stims_x_agerange[age_idx].filter(stimulusxattribute__attribute_value_text=media_types[media_idx])
    select_from_stims = select_from_stims.filter(num_responses=select_from_stims.aggregate(Min('num_responses')))

    # We've arrived at our stimulus
    stimulus = select_from_stims[random.randrange(0,select_from_stims.count())]

    #
    # Now, set up the jsPsych trial
    #

    # Determine the stimulus type
    media_type = media_types[media_idx]

    # Specify the trial based on the jsPsych definition for the corresponding media type
    if media_type == 'jingle':
        trial = {
            'type': 'audio-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
            'choices': 'none',
            'trial_ends_after_audio': True,
        }
    elif media_type == 'logo':
        trial = {
            'type': 'image-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': params['logo_duration_ms'],
            'trial_duration': params['logo_duration_ms']
        }
    elif media_type == 'slogan':
        # Possibly need to fetch the text from the file and place it into the stimulus string
        trial = {
            'type': 'html-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
            'choices': 'none',
            'stimulus_duration': params['slogan_duration_ms'],
            'trial_duration': params['slogan_duration_ms']
        }
    else:
        raise ValueError(f'Cannot specify trial for {media_type}')

    # Push the trial to the timeline
    timeline.append(trial)

    # pdb.set_trace()

    return timeline, stimulus.id


