# jingle_study.py
#
# Run a couple of importers to establish this experiment in the database:
# /experiments/jingles/import_experiment_structure/
# import_stims()
# import_attributes()


import os, csv, io, re
import random

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
import django.forms as forms
from django.utils import timezone
from django.db.models import Q, Count, Min

from django.contrib.auth.decorators import login_required

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from pyensemble.models import Session, Attribute, Stimulus, StimulusXAttribute, AttributeXAttribute, Experiment, Form, ExperimentXForm, Question, FormXQuestion, DataFormat, Response

from pyensemble.importers.forms import ImportForm

import pdb

# Specify the stimulus directory relative to the stimulus root
rootdir = 'jinglestims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

study_params = {
    'jingle_project_study1': {
        'age_ranges':[(6,16),(17,30),(31,64),(65,120)],
        'logo_duration_ms': 15000,
        'slogan_duration_ms': 15000,
    }
}

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Imports stimuli for Angela Nazarian's jingle study
@login_required
def import_stims(request,stimdir=stimdir):
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

    return render(request,'pyensemble/message.html',{'msg':'Successfully imported the stimuli'})

@login_required
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
                    sxa, created = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=value_text, attribute_value_double=value_float)

            return render(request,'pyensemble/message.html',{'msg':'Successfully imported the attribute file'})

    else:
        form = ImportForm()

    context = {'form': form}

    return render(request, template, context)

@login_required
def delete_exf(request,title):
    ExperimentXForm.objects.filter(experiment__title=title).delete()
    return render(request,'pyensemble/message.html',{'msg':f'Deleted experimentxform for {title}'})

def age_meets_criterion_and_lived_in_USA(request,*args,**kwargs):
    #
    # Get the subject's dob from the session
    dob = Session.objects.get(id=kwargs['session_id']).subject.dob

    # Display this form if they're under 18 years of age
    return (timezone.now().date()-dob).days < int(kwargs['min'])*365

    # Get the form we want
    form_name='jingle_project_demographics'
    
    # Get the response corresponding to Question 2 from this form
    USA_response = Response.objects.filter(session=kwargs['session_id'],form__name=form_name, question__text__contains='born').last()
    print(USA_response)
    # Display this form if they moved to the USA at 6 years of age or older
    return USA_response.response_enum < 4
    #return ("6" in USA_response.enum_values or "10" in USA_response.enum_values)
    

def age_meets_criterion(request,*args,**kwargs):
    #
    # Need to expand this to account for various min,max,eq possibilities
    #
    # Also, this is a generic function that should be moved to a generic location. Perhaps conditions.py, though this then causes a problem with the assumption that modules exist in experiments.
    #

    # Get the subject from the session
    dob = Session.objects.get(id=kwargs['session_id']).subject.dob

    return (timezone.now().date()-dob).days >= int(kwargs['min'])*365

def stim_was_familiar_and_jingle(request,*args,**kwargs):
    # Get the current stimulus ID
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=kwargs['session_id']).experiment.id))

    stimulus_id = expsessinfo['stimulus_id']

    if not stimulus_id:
        raise ValueError('Condition evaluator expected a stimulus_id but got None')

    # Make sure this stimulus was also a jingle
    attribute = Attribute.objects.get(name='Media Type')
    is_jingle = StimulusXAttribute.objects.get(stimulus_id=stimulus_id, attribute_id=attribute).attribute_value_text == 'jingle'

    if is_jingle:
        return False

    # Get the form we want
    form_name='Jingle Project Familiarity'

    # Get the response corresponding to this stimulus
    last_response = Response.objects.filter(session=kwargs['session_id'],form__name=form_name, question__text__contains='familiar', stimulus=stimulus_id).last()

    # Check whether our enum matches
    # pdb.set_trace()
    return last_response.response_enum > 0

def imagined_jingle(request,*args,**kwargs):
    # Get our stimulusID 
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=kwargs['session_id']).experiment.id))
    stimulus_id = expsessinfo['stimulus_id']

    # Get the form we want
    form = Form.objects.get(name='heard_jingle')
    last_response = Response.objects.filter(session=kwargs['session_id'], stimulus=stimulus_id, form=form, form_question_num=0).last()

    if not last_response:
        return False

    return last_response.response_enum>0

def select_study1(request,*args,**kwargs):
    # Construct a jsPsych timeline
    # https://www.jspsych.org/overview/timeline/
    #
    # Still need to:
    # prevent repeats of product category
    # select based on product categories
    # incorporate desired percentage of Canadian stims
    # incorporate maximum selected number per-category
    # make

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
    media_year_ranges = [((dob+timezone.timedelta(days=r[0]*365)).year,(dob+timezone.timedelta(days=r[1]*365)).year) for r in age_ranges]

    # Get our list of stimuli that this subject has already encountered
    presented_stim_ids = Response.objects.filter(experiment=session.experiment, subject_id=subject, stimulus__isnull=False).values_list('stimulus',flat=True).distinct()
    presented_stims = Stimulus.objects.filter(id__in=presented_stim_ids)

    # Get the last presented stimulus to this subject in this experiment
    if presented_stims:
        previous_stim = presented_stims.get(id=presented_stim_ids.last())
    else:
        previous_stim = None

    #
    # Get our list of possible stimuli
    #

    # Exclude previously presented stimuli
    possible_stims = Stimulus.objects.filter(playlist='Jingle Study').exclude(id__in=(presented_stims))

    # Exclude stimuli that are in the same advertisement grouping as any of the presented stimui
    for stim in presented_stims:
        use_prefix = False
        if use_prefix:
            # Get the grouping identifier
            match = re.match('^(?P<group_str>\d+)_',stim.name)

            if not match:
                # If we don't have a grouping identifier, just continue
                continue

            group_str = match.groupdict()['group_str']
            possible_stims = possible_stims.exclude(name__iregex=r'^%s'%(group_str))

        else:
            try:
                # Find the item that this stimulus advertised
                sxa_instance = StimulusXAttribute.objects.get(stimulus=stim,attribute__name='Product')

                product_name = sxa_instance.attribute_value_text

                possible_stims = possible_stims.exclude(
                    stimulusxattribute__attribute__id=sxa_instance.attribute.id,
                    stimulusxattribute__attribute_value_text=product_name)
            except:
                if settings.DEBUG:
                    pdb.set_trace()

    # Exclude stimuli that have the same company as the previously presented stimulus
    if previous_stim:
        company = StimulusXAttribute.objects.get(stimulus=previous_stim,attribute__name='Company').attribute_value_text
        possible_stims = possible_stims.exclude(stimulusxattribute__attribute_value_text=company)

    # Determine the number of times that each stimulus has been presented
    experiment_responses = Count('response', filter=Q(response__experiment=session.experiment))
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

    # Randomly pick a media type
    media_idx = random.randrange(0,media_types.count())

    # Randomly pick an age range from those that actually have stimuli
    num_available_in_range = [r.count() for r in stims_x_agerange]
    available_ranges = [idx for idx,n in enumerate(num_available_in_range) if n]
    age_idx = available_ranges[random.randrange(0,len(available_ranges))]

    # Select from among the least played stimuli in the target category
    select_from_stims = stims_x_agerange[age_idx].filter(
        stimulusxattribute__attribute__name='Media Type',
        stimulusxattribute__attribute_value_text=media_types[media_idx])
    num_min = select_from_stims.aggregate(Min('num_responses'))['num_responses__min']
    select_from_stims = select_from_stims.filter(num_responses=num_min)

    # We've arrived at our stimulus
    if not select_from_stims.count():
        if settings.DEBUG:
            pdb.set_trace()

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
        contents = stimulus.location.open().read().decode('utf-8')
        trial = {
            'type': 'html-keyboard-response',
            'stimulus': contents,
            #'stimulus': '<p style="color: black; font-size: 48px; font-weight: bold;">contents</p>',
            #'stimulus':'<div style="font-size:32px;">contents</div>',
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