# bio_data_export.py.py

from bio_params import bio_params as bp

import pdb
import os, csv
import random
#import json

from django.conf import settings
from django.utils import timezone
import datetime

from pyensemble.models import Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)


def bio_participantStatus(expName,startMonthDay,endMonthDay):
    # Grab data from this experiment from subjects who participated between specified dates
    # if dates are specified, grab all reponses from the experiment 
    # filters out subjects that are also not being included in the counterbalancing (see params)
    #return: 
    #subjects name (so we can assign credit)
    #subjects date of doing practice trial 
    #time to complete expo task, otherwise empty
    #time to complete surveys 
    #time to complete expo
    #answer for free-text any comments response. 

    # Get our parameters
    study_params = bp() 
    params = study_params[expName] #'musmemfmri_bio_pilot'

    study_year = 2020

    startMonthDay = [5,1]
    endMonthDay = [6,30]

    #grab all previous subs who have been entered in attr X attr 
    triallAttrIDs = [format(x, '02d') for x in params['encoding_trials_1-20']]+[format(x, '02d') for x in params['encoding_trials_21-40']]
    all_prev_subids = AttributeXAttribute.objects.filter(parent_id__in=triallAttrIDs).values_list('mapping_name',flat=True).distinct()
    all_prev_subs = Subject.objects.filter(subject_id__in=all_prev_subids)
    prev_subs_initd = all_prev_subs.exclude(subject_id__in=params['ignore_subs']) #filter out subs we aren't including (in counterbalancing)

    #grab all the subs with responses between the start/end poitns 
    all_time_subids = Response.objects.filter(experiment_id=params['experiment_id'],date_time__gte=datetime.date(study_year, startMonthDay[0], startMonthDay[1]),date_time__lte=datetime.date(study_year, endMonthDay[0],endMonthDay[1])).values_list('subject_id',flat=True).distinct()
    #all_time_subids = Response.objects.filter(experiment_id=params['experiment_id'],date_time__range=['2020-05-01','2020-06-30'])
    prev_subs_start = prev_subs_initd.filter(subject_id__in=all_time_subids) #now filter so only have these stims
    #put subjects in order of time. (first to most recent) date_entered
    prev_subs_start = prev_subs_start.filter().order_by('date_entered')

    outFile = open(os.path.join(params['data_dump_path'],expName+"_status_"+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+".txt"),"a") 
    outFile.write('Last Name, First Name\tDate Reg\tExpo Time\tSurvey Time\tRecall Time\tComments\n')
    print(f'Last Name, First Name\tDate Reg\tExpo Time\tSurvey Time\tRecall Time\tComments\n')
    
    #loop through each subject and calculate the things we are interested in 
    for isub in prev_subs_start:
        #pdb.set_trace() 
        # look at responses for the exposure task (form 7 as attractiveness question, should be at least 40; culd be more dep on practice trials)
        expoResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form__id='7')
        nExpoResps = len(expoResponses)
        #get the first and last presented form (either form_order or date_time)
        #calculate time spent on the task. 
        try:
            sortExpoResponses = expoResponses.filter().order_by('date_time') #- for descending order
            expoTime = sortExpoResponses[len(sortExpoResponses)-1].date_time - sortExpoResponses[0].date_time
            mexpoTime = str((expoTime.total_seconds() % 3600) // 60)
        except:
            mexpoTime = '-'

        #did this sub make it through the survey task? (start time at form 14; ending 23)
        survey_start_resp = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='14',question='3')
        survey_end_resp = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='23',question='127')
        try:
            surveyTime = survey_end_resp[0].date_time - survey_start_resp[0].date_time
            msurveyTime = str((surveyTime.total_seconds() % 3600) // 60)
        except:
            msurveyTime = '-'
        
        #did this sub make it through the recall task (form 27 is the image recall questions, should be 20)
        recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='27',question='128')
        nRecallResps = len(recallResponses)
        #get the first and last presented form (either form_order or date_time)
        #calculate time spent on the task. 
        try:
            sortrecallResponses = recallResponses.filter().order_by('date_time') #- for descending order
            recalltime = sortrecallResponses[len(sortrecallResponses)-1].date_time - sortrecallResponses[0].date_time
            mrecalltime = str((recalltime.total_seconds() % 3600) // 60)
        except:
            mrecalltime = '-'
        
        #did this sub leave a comment (form 60 question ? )
        recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='60',question='317')
        try:
            textResp = recallResponses[0].response_text
        except:
            textResp = '-'
        #pdb.set_trace() 

        outFile.write(isub.name_last+', '+isub.name_first+'\t'+str(isub.date_entered)+'\t'+mexpoTime+'\t'+msurveyTime+'\t'+mrecalltime+'\t'+textResp+'\n')
        print(isub.name_last+', '+isub.name_first+'\t'+str(isub.date_entered)+'\t'+mexpoTime+'\t'+msurveyTime+'\t'+mrecalltime+'\t'+textResp+'\n')
            #'Has Trials\tExpo Time\tSurvey Time\tRecallT Time\tComments\n')
    outFile.close()


def bio_dumpData(expName,startMonthDay,endMonthDay):
    # Grab data from this experiment from subjects who participated between specified dates
    # if dates are specified, grab all reponses from the experiment 
    # filters out subjects that are also not being included in the counterbalancing (see params)
    #return: 
    # Exposure task data .csv
    # -
    # Survey task data .csv
    # -
    # Recall task data .csv
    # -
    # Feedback data .csv
    # - 
    # Get our parameters
    study_params = bp() 
    params = study_params[expName] #'musmemfmri_bio_pilot'

    study_year = 2020

    startMonthDay = [5,1]
    endMonthDay = [6,30]

    #grab all previous subs who have been entered in attr X attr 
    triallAttrIDs = [format(x, '02d') for x in params['encoding_trials_1-20']]+[format(x, '02d') for x in params['encoding_trials_21-40']]
    all_prev_subids = AttributeXAttribute.objects.filter(parent_id__in=triallAttrIDs).values_list('mapping_name',flat=True).distinct()
    all_prev_subs = Subject.objects.filter(subject_id__in=all_prev_subids)
    prev_subs_initd = all_prev_subs.exclude(subject_id__in=params['ignore_subs']) #filter out subs we aren't including (in counterbalancing)

    #grab all the subs with responses between the start/end poitns 
    all_time_subids = Response.objects.filter(experiment_id=params['experiment_id'],date_time__gte=datetime.date(study_year, startMonthDay[0], startMonthDay[1]),date_time__lte=datetime.date(study_year, endMonthDay[0],endMonthDay[1])).values_list('subject_id',flat=True).distinct()
    #now filter so only have these stims
    prev_subs_start = prev_subs_initd.filter(subject_id__in=all_time_subids) 
    prev_subs_start = prev_subs_start.filter().order_by('date_entered') #put subjects in order of time. (first to most recent) date_entered
    
    











