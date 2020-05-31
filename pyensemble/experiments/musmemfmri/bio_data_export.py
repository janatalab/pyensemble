# bio_data_export.py.py

from .bio_params import bio_params as bp

import pdb
import os, csv
import random
#import json

from django.conf import settings

from pyensemble.models import Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)


def bio_participantStatus(expName,starDate,endDate):
    # Grab data from this experiment from subjects who participated between specified dates
    # if dates are specified, grab all reponses from the experiment 
    # filters out subjects that are also not being included in the counterbalancing (see params)

    try:
        expName
        # Get our parameters
        study_params = bio_params() 
        params = study_params[whichExperiment] #'musmemfmri_bio_pilot'
    except:
        print(f'WANRING: you must specify an experiment name!')
    try:
        starDate
    except:
        starDate = ''#get all 
    try:
        endDate
    except:
        endDate = ''#get all 

    pdb.set_trace() 
    #grab all previous subs who have been entered in attr X attr 
    triallAttrIDs = params['encoding_trials_1-20']+params['encoding_trials_21-40']
    triallAttrIDs = list(map(str, triallAttrIDs))
    all_prev_subids = AttributeXAttribute.objects.filter(parent_id_in=triallAttrIDs).values_list('mapping_value_text',flat=True)
    all_prev_subs = Subject.objects.filter(subject_id__in=all_prev_subids)
    prev_subs_initd = all_prev_subs.exclude(subject_id__in=params['ignore_subs']) #filter out subs we aren't including (in counterbalancing)

    #grab all the subs with responses between the start/end poitns ##NOT GOING TO WORK
    all_time_subids = Response.objects.filter(experiment_id=session.experiment.id,date_time=startTime).values_list('subject_id',flat=True).distinct()
    prev_subs_start = prev_subs_initd.filter(subject_id__in=all_time_subids) #now filter so only have these stims
    #put subjects in order of time. (first to most recent)

    print(f'Subject Name\\tHas Trials\\tExpo Time\\tSurvey Time\\tRecallT Time\\tComments\n')
    #loop through each subject and calculate the things we are interested in 
    for isub in prev_subs_start:
        #currSub = prev_subs_start[]

        # look at responses for the exposure task (form 7 as attractiveness question, should be 40)
        expoResponses = Response.objects.filter(experiment_id=session.experiment.id,subject_id=isub,form__id='7')
        nExpoResps = len(expoResponses)
        #get the first and last presented form (either form_order or date_time)
        #calculate time spent on the task. 
        expoTime = ''

        #did this sub make it through the survey task? (start time at form 14; ending 23)
        survey_start_resp = Response.objects.filter(experiment_id=session.experiment.id,subject_id=isub,form='14')
        survey_end_resp = Response.objects.filter(experiment_id=session.experiment.id,subject_id=isub,form='23')
        surveyTie = ''

        #did this sub make it through the recall task (form 27 is the image recall questions, should be 20)
        recallResponses = Response.objects.filter(experiment_id=session.experiment.id,subject_id=isub,form__id='27')
        nRecallResps = len(recallResponses)
        #get the first and last presented form (either form_order or date_time)
        #calculate time spent on the task. 
        recalltime = ''

        #did this sub leave a comment (form 60 question ? )
        recallResponses = Response.objects.filter(experiment_id=session.experiment.id,subject_id=isub,form__id='60')
        textResp = recallResponses

        print(f'')

    #return: 
    #subjects name (so we can assign credit)
    #subjects date of doing practice trial 
    #time to complete expo task, otherwise empty
    #time to complete surveys 
    #time to complete expo
    #answer for free-text any comments response. 





