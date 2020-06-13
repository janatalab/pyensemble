# loop_data_export.py.py

from loop_params import loop_params as lp

import pandas as pd
import seaborn as sb
from matplotlib.backends.backend_pdf import PdfPages

import matplotlib.pyplot as plt
import pdb
import os, csv, glob
import random
import json

from django.conf import settings
from django.utils import timezone
import datetime

from pyensemble.models import Question, Form, Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

def bio_cbPlots(expName,startMonthDay,endMonthDay):
    #######################################################
    # counterbalance plots 
    # builds plots from DB for easy access
    #
    # loop X trial (run1, across subjects); 
    # loop X key (run1, across subjects); 

    # loop X trial (runs2-6, within subject: ensure no same run position or preceding loop across runs)
    # Get our parameters
    study_params = lp() 
    params = study_params[expName] #'musmemfmri_bio_pilot'

    study_year = 2020

    startMonthDay = [5,1]
    endMonthDay = [6,30]

    #
    #grab all previous subs who have been entered in attr X attr 
    triallAttrIDs = [format(x, '02d') for x in params['encoding_trials_1-20']]
    triallAttrs = Attribute.objects.filter(id__in=triallAttrIDs,attribute_class='bio_trials').values_list('name',flat=True)
    OurSubAxAentries = AttributeXAttribute.objects.filter(parent_id__in=triallAttrIDs,parent__attribute_class='bio_trials').exclude(mapping_name__in=params['ignore_subs'])
    OurSubAxAentries_name = OurSubAxAentries.filter(child__attribute_class='face_name')
    OurSubAxAentries_location = OurSubAxAentries.filter(child__attribute_class='location')

    uLocations = sorted(OurSubAxAentries_location.values_list('child__name',flat=True).distinct())
    uFaces = sorted(OurSubAxAentries.filter(child__attribute_class='face_name').values_list('mapping_value_text',flat=True).distinct())
    uNames = sorted(OurSubAxAentries_name.values_list('child__name',flat=True).distinct())
    nSubs =  len(OurSubAxAentries.values_list('mapping_name',flat=True).distinct())

    #pdb.set_trace()

    # init DF to hold the stimXtrial counts 
    StimXTrial = pd.DataFrame(0,index=uFaces,columns = triallAttrs)
    for iface in uFaces:
        for itrial in triallAttrs:
            #loop through each stim entry in attrxattr and add count to df
            tmp_entries = OurSubAxAentries_name.filter(parent__name=itrial,mapping_value_text=iface)
            StimXTrial.at[iface,itrial] = len(tmp_entries)

    # init DF to hold the stimXnames counts 
    StimXName = pd.DataFrame(0,index=uFaces,columns = uNames)
    for iface in uFaces:
        for uname in uNames:
            #loop through each stim entry in attrxattr and add count to df
            tmp_entries = OurSubAxAentries_name.filter(child__name=uname,mapping_value_text=iface)
            StimXName.at[iface,uname] = len(tmp_entries)

    # init DF to hold the stimXlocation counts 
    StimXLocation = pd.DataFrame(0,index=uFaces,columns = uLocations)
    for iface in uFaces:
        for uloc in uLocations:
            #loop through each stim entry in attrxattr and add count to df
            tmp_entries = OurSubAxAentries_location.filter(child__name=uloc,mapping_value_text=iface)
            StimXLocation.at[iface,uloc] = len(tmp_entries)



    with PdfPages(os.path.join(params['data_dump_path'],('CB_plots_'+'nSubs%02d'%nSubs)+'_'+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+'.pdf')) as pdf_pages:

        plot1 = sb.heatmap(StimXTrial)
        pdf_pages.savefig(plot1.figure)
        plt.close()

        plot2 = sb.heatmap(StimXName)
        pdf_pages.savefig(plot2.figure)
        plt.close()

        plot3 = sb.heatmap(StimXLocation)
        pdf_pages.savefig(plot3.figure)
        plt.close()

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
    study_params = lp() 
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
    #pdb.set_trace()
    #add subid, age, sex, ethnicity, gender !!!
    print(f'Last Name, First Name\tDate Reg\tsubject_id\tExpo nTrials\tRecall nTrials\tTotal Time\tComments\n')
    fieldnames = ['Last_Name', 'First_Name', 'Date_Reg', 'subject_id', 'Expo_nTrials','Expo_Time','Survey_Time','Recall_nTrials','Recall_Time','Total_Time','Comments']
    with open(os.path.join(params['data_dump_path'],expName+"_status_"+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+".csv"),mode='w') as outDatCSV:
        writer = csv.writer(outDatCSV, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)
    
        #loop through each subject and calculate the things we are interested in 
        for isub in prev_subs_start:
            #pdb.set_trace() 
            # look at responses for the exposure task (form 7 as attractiveness question, should be at least 40; culd be more dep on practice trials)
            expoResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form__id='7')
            #get the first and last presented form (either form_order or date_time)
            #calculate time spent on the task. 
            nexpoTrials = str(len(expoResponses))
            try:
                sortExpoResponses = expoResponses.filter().order_by('date_time') #- for descending order
                expoTime = sortExpoResponses[len(sortExpoResponses)-1].date_time - sortExpoResponses[0].date_time
                mexpoTime = (expoTime.total_seconds() % 3600) // 60
                hexpoTime = expoTime.total_seconds() // 3600
                mexpoTime = str(mexpoTime + hexpoTime*60)
            except:
                mexpoTime = '-'

            #did this sub make it through the survey task? (start time at form 14; ending 23)
            survey_start_resp = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='14',question='3')
            survey_end_resp = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='23',question='127')
            try:
                surveyTime = survey_end_resp[0].date_time - survey_start_resp[0].date_time
                msurveyTime = (surveyTime.total_seconds() % 3600) // 60
                hsurveyTime = surveyTime.total_seconds() // 3600
                msurveyTime = str(msurveyTime + hsurveyTime*60)

            except:
                msurveyTime = '-'
            
            #did this sub make it through the recall task (form 27 is the image recall questions, should be 20)
            recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='27',question='128')
            #get the first and last presented form (either form_order or date_time)
            #calculate time spent on the task. 
            nrecallTrials = str(len(recallResponses))
            if len(recallResponses)>0:
                sortrecallResponses = recallResponses.filter().order_by('date_time') #- for descending order
                recalltime = sortrecallResponses[len(sortrecallResponses)-1].date_time - sortrecallResponses[0].date_time
                mrecalltime = (recalltime.total_seconds() % 3600) // 60
                hrecalltime = recalltime.total_seconds() // 3600
                mrecalltime = str(mrecalltime + hrecalltime*60)

                totalTime = sortrecallResponses[len(sortrecallResponses)-1].date_time - sortExpoResponses[0].date_time
                mtotalTime = (totalTime.total_seconds() % 3600) // 60
                htotalTime = totalTime.total_seconds() // 3600
                mtotalTime = str(mtotalTime + htotalTime*60)

            else:
                mrecalltime = '-'
                mtotalTime = '-'
                #ADD DELAY TIME (last expo trial - first recall trial?)
            
            #did this sub leave a comment (form 60 question ? )
            recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form='60',question='317')
            try:
                textResp = recallResponses[0].response_text
            except:
                textResp = '-'
            #pdb.set_trace() 

            writer.writerow([isub.name_last,isub.name_first,str(isub.date_entered),isub.subject_id,nexpoTrials,mexpoTime,msurveyTime,nrecallTrials,mrecalltime,mtotalTime,textResp])
            print(isub.name_last+', '+isub.name_first+'\t'+str(isub.date_entered)+'\t'+isub.subject_id+'\t'+nexpoTrials+'\t'+nrecallTrials+'\t'+mtotalTime+'\t'+textResp+'\n')
                #'Has Trials\tExpo Time\tSurvey Time\tRecallT Time\tComments\n')
    outDatCSV.close()









