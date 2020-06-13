# bio_data_export.py.py

from bio_params import bio_params as bp

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

from fuzzywuzzy import fuzz

from pyensemble.models import Question, Form, Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

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

def bio_dumpData(expName,startMonthDay,endMonthDay):
    # Grab data from this experiment from subjects who participated between specified dates
    # if dates are specified, grab all reponses from the experiment 
    # filters out subjects that are also not being included in the counterbalancing (see params)
    #return: 
    # Exposure task data .csv (want to have 1 response per bio. so on same row: attractive, textresp)
    # -subject_id, experiment_id, date_time, trial_name, resposne_order, face_id, hit, (resps), correct_feature, verify? 
    # Survey task data .csv
    # -subject_id, experiment_id, date_time, trial_name, resposne_order, face_id, (name_resp, name_CA), perc_recall, verify?
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
    
    #add one more filter to remove subs who haven't made it all the way through the study 
    finished_subids = Response.objects.filter(experiment_id=params['experiment_id'],form='60',question='317').values_list('subject_id',flat=True).distinct()
    prev_subs_finished = prev_subs_start.filter(subject_id__in=finished_subids)
    #pdb.set_trace()

    all_attributes = Attribute.objects.filter(id__in=triallAttrIDs)

    #################
    ## grab the exposure data (attractiveness + feature recall)
    with open(os.path.join(params['data_dump_path'],expName+"_expo_"+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+".csv"), mode='w') as outDatCSV:
        fieldnames = ['subject_id','experiment_id','resptime','response_order','trial',
                        'stimulus_id','attractivness','response_text','correct_answer','hit','verify']
        writer = csv.writer(outDatCSV, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)

        #loop through each subject and calculate the things we are interested in 
        for isub in prev_subs_finished:
            attracResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form__id='7')
            recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form__name__in=params['form_names'])

            #append all the relevant info to each entry (stored in misc_info)
            #[json.loads(x.trial_name)['trial_attribute_name'] for x in attracResponses]
            if len(attracResponses)==len(recallResponses):
                for iresp in range(0,len(attracResponses)):
                    attracResponses[iresp].trial_name = json.loads(attracResponses[iresp].misc_info)['trial_attribute_name']
                    recallResponses[iresp].trial_name = json.loads(recallResponses[iresp].misc_info)['trial_attribute_name']
                    
                    #['currPostBioQ']not saved out, but the form answered is the feature
                    whichQuestion = Form.objects.get(id=recallResponses[iresp].form_id).name
                    #this sucks but just loop
                    for ipname in params['bioFeature_names']:
                        if ipname in whichQuestion:
                            if ipname in ['relation']:
                                #pdb.set_trace()
                                if json.loads(recallResponses[iresp].misc_info)[ipname] in params['alt_feature_answers'].keys():
                                    recallResponses[iresp].correct_answer = [json.loads(recallResponses[iresp].misc_info)[ipname],params['alt_feature_answers'][json.loads(recallResponses[iresp].misc_info)[ipname]]]
                                else:
                                    recallResponses[iresp].correct_answer = json.loads(recallResponses[iresp].misc_info)[ipname]
                            else:
                                recallResponses[iresp].correct_answer = json.loads(recallResponses[iresp].misc_info)[ipname]
                     
            else:
                print(f'WARNING: mismatched number of expo trials for sub:'+isub.subject_if)

            #we want a row for every trial, so let's loop through the trials
            # be better to match the trials to verify
            for itrial in range(0,len(attracResponses)):
                resptime = str(attracResponses[itrial].date_time.month)+'/'+str(attracResponses[itrial].date_time.day)+'/'+str(attracResponses[itrial].date_time.year)+'_'+str(attracResponses[itrial].date_time.hour)+':'+str(attracResponses[itrial].date_time.minute)
                #NEED TO ADD SOMETHING HERE THAT GETS SYNONYMS AND ANTONYMS (e.g., father/dad; mom/son?)
                #now do some fuzzy matching to see if it's correct
                if len(recallResponses[itrial].correct_answer)==2: 
                    matchScore1 = fuzz.ratio(recallResponses[itrial].response_text.lower(), recallResponses[itrial].correct_answer[0].lower())
                    matchScore2 = fuzz.ratio(recallResponses[itrial].response_text.lower(), recallResponses[itrial].correct_answer[1].lower())
                    if matchScore1 >= matchScore2:
                        matchScore = matchScore1
                    else:
                        matchScore = matchScore2
                else:
                    #pdb.set_trace()
                    matchScore = fuzz.ratio(recallResponses[itrial].response_text.lower(), recallResponses[itrial].correct_answer.lower())
                if matchScore >= 90:
                    hit = '1'
                    verify = '-'
                elif matchScore >= 70:
                    hit = '1'
                    verify = 'verify'
                else:
                    hit = '0'
                    verify = '-'
                #pdb.set_trace()
                writer.writerow([attracResponses[itrial].subject_id, str(attracResponses[itrial].experiment_id),resptime,
                    str(attracResponses[itrial].response_order), attracResponses[itrial].trial_name, str(attracResponses[itrial].stimulus_id),
                    str(attracResponses[itrial].response_enum), recallResponses[itrial].response_text, recallResponses[itrial].correct_answer,
                    hit, verify])

    outDatCSV.close()

    #################
    ## grab the survey data ()


    #################
    ## grab the recall data () 
    #subject_id, experiment_id, date_time, resposne_order, face_id, (name_resp, name_CA), perc_recall, verify?
    with open(os.path.join(params['data_dump_path'],expName+"_recall_"+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+".csv"), mode='w') as outDatCSV:
        fieldnames = ['subject_id','experiment_id','resptime','response_order','trial','stimulus_id',
                        'face_name_resp','face_name_resp_CA','face_name_hit','location_resp','location_resp_CA','location_hit','job_resp','job_resp_CA','job_hit',
                        'hobby_resp','hobby_resp_CA','hobby_hit','relation_resp','relation_resp_CA','relation_hit','relation_name_resp','relation_name_resp_CA','relation_name_hit',
                        'perc_recall','verify']
        writer = csv.writer(outDatCSV, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)

        #loop through each subject and calculate the things we are interested in 
        for isub in prev_subs_finished:
            recallResponses = Response.objects.filter(experiment_id=params['experiment_id'],subject_id=isub,form__id='27')

            #append all the relevant info to each entry (stored in misc_info)
            #[json.loads(x.trial_name)['trial_attribute_name'] for x in attracResponses]
            
            if len(recallResponses)>0:
                #we want a row for every trial, so let's loop through the trials
                triallAttrIDs = [format(x, '02d') for x in params['encoding_trials_1-20']]
                for itrial in triallAttrIDs:
                    currRecallScore = 0
                    verify = 0
                    #need to combine each set into 1 row
                    #pdb.set_trace()
                    #filter based on thihe stim associated with this trial 
                    currTrialName = Attribute.objects.get(id=itrial)
                    currFaceName = AttributeXAttribute.objects.filter(parent_id=itrial,mapping_name=isub.subject_id).values_list('mapping_value_text',flat=True).distinct()
                    currResps = recallResponses.filter(stimulus_id__name=currFaceName[0])
                    resptime = str(currResps[0].date_time.month)+'/'+str(currResps[0].date_time.day)+'/'+str(currResps[0].date_time.year)+'_'+str(currResps[0].date_time.hour)+':'+str(currResps[0].date_time.minute)
                    for iresp in currResps:
                        #['currPostBioQ']not saved out, but the form answered is the feature
                        whichQuestion = Question.objects.get(id=iresp.question_id).id

                        if whichQuestion==132:
                            matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['face_name'].lower())
                            curr_face_name_resp = iresp.response_text
                            curr_face_name_resp_CA = json.loads(iresp.misc_info)['face_name']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                face_name_hit = '1'
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                face_name_hit = '1'
                            else:
                                face_name_hit = '0'
                        elif whichQuestion==133:
                            matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['location'].lower())
                            curr_location_resp = iresp.response_text
                            curr_location_resp_CA = json.loads(iresp.misc_info)['location']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                location_hit = '1'
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                location_hit = '1'
                            else:
                                location_hit = '0'
                        elif whichQuestion==128:
                            matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['job'].lower())
                            curr_job_resp = iresp.response_text
                            curr_job_resp_CA = json.loads(iresp.misc_info)['job']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                job_hit = '1'
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                job_hit = '1'
                            else:
                                job_hit = '0'
                        elif whichQuestion==129:
                            matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['hobby'].lower())
                            curr_hobby_resp = iresp.response_text
                            curr_hobby_resp_CA = json.loads(iresp.misc_info)['hobby']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                hobby_hit = '1'
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                hobby_hit = '1'
                            else:
                                hobby_hit = '0'
                        elif whichQuestion==130:#130 now 
                            #NEED TO ADD SOMETHING HERE THAT GETS SYNONYMS AND ANTONYMS (e.g., father/dad; mom/son?)
                            try: 
                                params['alt_feature_answers'][json.loads(iresp.misc_info)['relation']]
                                #pdb.set_trace()
                                #run match on the other options and use the higher match
                                matchScore1 = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['relation'].lower())
                                matchScore2 = fuzz.ratio(iresp.response_text.lower(), params['alt_feature_answers'][json.loads(iresp.misc_info)['relation']].lower())
                                if matchScore1 >= matchScore2:
                                    matchScore = matchScore1
                                else:
                                    matchScore = matchScore2
                            except:
                                matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['relation'].lower())

                            curr_relation_resp = iresp.response_text
                            curr_relation_resp_CA = json.loads(iresp.misc_info)['relation']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                relation_hit = 1
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                relation_hit = '1'
                            else:
                                relation_hit = '0'
                        elif whichQuestion==131:
                            matchScore = fuzz.ratio(iresp.response_text.lower(), json.loads(iresp.misc_info)['relation_name'].lower())
                            curr_relation_name_resp = iresp.response_text
                            curr_relation_name_resp_CA = json.loads(iresp.misc_info)['relation_name']
                            if matchScore >= 90:
                                currRecallScore = currRecallScore + 1
                                relation_name_hit = '1'
                            elif matchScore >= 70:
                                currRecallScore = currRecallScore + 1
                                verify = verify + 1
                                relation_name_hit = '1'
                            else:
                                relation_name_hit = '0'
                    recallPercent = currRecallScore/len(currResps)
                    if len(currResps)!=6:
                        pdb.set_trace()
                        print(f'WARNING: missing some responses for sub: '+isub.subject_id)
                    #pdb.set_trace()

                    writer.writerow([currResps[0].subject_id, str(currResps[0].experiment_id),resptime,
                        str(currResps[0].response_order), currTrialName.name, str(currResps[0].stimulus_id),curr_face_name_resp,curr_face_name_resp_CA,face_name_hit,
                        curr_location_resp,curr_location_resp_CA,location_hit,curr_job_resp,curr_job_resp_CA,job_hit,
                        curr_hobby_resp,curr_hobby_resp_CA,hobby_hit,curr_relation_resp,curr_relation_resp_CA,relation_hit,
                        curr_relation_name_resp,curr_relation_name_resp_CA,relation_name_hit,str(recallPercent),str(verify)])
                    
            else:
                print(f'WARNING: wrong number of recall trials for sub:'+isub.subject_if)

    outDatCSV.close()

    #################
    ## grab the feedback data ()
    with open(os.path.join(params['data_dump_path'],expName+"_feedback_"+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+".csv"), mode='w') as outDatCSV:
        fieldnames = ['subject_id','experiment_id','resptime','studyContext','paidAttention',
        'performedMyBest','performedIntegrity','personImagery','personSpont','personExp','feedback']
        writer = csv.writer(outDatCSV, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)

        #loop through each subject and calculate the things we are interested in 
        for isub in prev_subs_finished:
            timeInfo = paidAttention = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='I paid attention throughout the experiment')
            studyContext = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='Please describe the environment in which you participated in the study').values_list('response_text',flat=True)[0]
            paidAttention = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='I paid attention throughout the experiment').values_list('response_enum',flat=True)[0]
            performedMyBest = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='I performed the experiment to the best of my ability and believe').values_list('response_enum',flat=True)[0]
            performedIntegrity = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='I performed the experiment with integrity').values_list('response_enum',flat=True)[0]
            personImagery = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='While you were filling out the surveys, about how much of the time were you thinking about the people you just met').values_list('response_enum',flat=True)[0]
            personSpont = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='During the survey period, how spontaneous were your thoughts about the people you just met').values_list('response_enum',flat=True)[0]
            personExp = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='Can you describe your experience in a few sentences').values_list('response_text',flat=True)[0]
            feedback = Response.objects.filter(subject_id=isub, form__name='bio_pilot_participant_feedback', question__text__contains='like us to know about the experiment?').values_list('response_text',flat=True)[0]

            resptime = str(timeInfo[0].date_time.month)+'/'+str(timeInfo[0].date_time.day)+'/'+str(timeInfo[0].date_time.year)+'_'+str(timeInfo[0].date_time.hour)+':'+str(timeInfo[0].date_time.minute)

            writer.writerow([isub.subject_id,str(currResps[0].experiment_id),resptime,studyContext,paidAttention,
                         performedMyBest,performedIntegrity,personImagery,personSpont,personExp,feedback])
    outDatCSV.close()

def bio_cbPlots(expName,startMonthDay,endMonthDay):
    #######################################################
    # counterbalance plots 
    # builds plots from DB for easy access
    #
    # face X trial (recog); face X name, face X location, 

    # face X trial (response_order, recall); 
    #
    # Get our parameters
    study_params = bp() 
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

def bio_performancePlots(expName):
    #musmemfmri_bio_pilot
    #use csvs created in bio_dumpData, make some plots to help us assess performance
    # PLOTS:
    # overall exposure score (include subject-data points)
    # overall recall score (include subject-data points)
    #
    # attractiveness X face (recog)
    # recall score X face 
    # recall score X trial 
    # recall score X feature 
    #
    # counterbalance plots
    # face X trial (recog); face X trial (response_order, recall); 
    # face X name (recog); face X location; face X job; face X hobby; face X relation; face X relation_name
    #
    # ADD THESE: Time X Task (boxplat)

    study_params = bp() 
    params = study_params[expName] #'musmemfmri_bio_pilot'

    #load in the latest status data
    list_of_files = glob.glob(os.path.join(params['data_dump_path'],expName+'_status_'+'*.csv'))
    latest_file = max(list_of_files, key=os.path.getctime)
    statusDat = pd.read_csv(latest_file)

    #load in the latest recog data
    list_of_files = glob.glob(os.path.join(params['data_dump_path'],expName+'_expo_'+'*.csv'))
    latest_file = max(list_of_files, key=os.path.getctime)
    recogDat = pd.read_csv(latest_file)

    #load in the latest recall data
    list_of_files = glob.glob(os.path.join(params['data_dump_path'],expName+'_recall_'+'*.csv'))
    latest_file = max(list_of_files, key=os.path.getctime)
    recallDat = pd.read_csv(latest_file)

    #calculate total number of subjects 
    nsubs = len(recogDat.subject_id.unique())

    with PdfPages(os.path.join(params['data_dump_path'],('plotAll_'+'nSubs%02d'%nsubs)+'_'+str("%02d"%timezone.now().month)+"-"+str("%02d"%timezone.now().day)+'.pdf')) as pdf_pages:

        #######################################################
        # overall exposure times (include subject-data points)
        pdb.set_trace()
        tmp = statusDat.reset_index()
        statusDat_long = pd.melt(tmp, id_vars=['subject_id'], value_vars=['Expo_Time', 'Survey_Time', 'Recall_Time','Total_Time'])

        statusDat_scores = statusDat_long.rename(columns= {'variable': 'task','value':'total_minutes'})
        plot1 = sb.catplot(x="total_minutes",y="task",kind='box',data=statusDat_scores)
        plot1.set_xticklabels(rotation=45,horizontalalignment='right')
        #plot5.savefig(os.path.join(params['data_dump_path'],'plot5.png'))
        pdf_pages.savefig(plot1.fig)

        #######################################################
        # overall exposure score (include subject-data points)
        subRecogScores = recogDat.groupby('subject_id')['hit'].mean()  #get sub level score
        subRecogScores = subRecogScores.to_frame().reset_index()
        subRecogScores = subRecogScores.rename(columns= {'hit': 'score'})
        subRecogScores['task'] = 'recog'#add col for value type

        # overall recall score (include subject-data points)
        subRecallScores = recallDat.groupby('subject_id')['perc_recall'].mean()  #get sub level score
        subRecallScores = subRecallScores.to_frame().reset_index()
        subRecallScores = subRecallScores.rename(columns= {'perc_recall': 'score'})
        subRecallScores['task'] = 'recall'#add col for value type

        # combine into one plot
        subScores = subRecogScores.append(subRecallScores)

        #pdb.set_trace()
        plot2 = sb.catplot(x="score",y="task",kind='box',data=subScores)
        #plot1.savefig(os.path.join(params['data_dump_path'],'plot1.png'))
        pdf_pages.savefig(plot2.fig)

        #######################################################
        # attractiveness X face (recog)
        plot3 = sb.catplot(x="stimulus_id",y="attractivness",kind='box',data=recogDat)
        plot3.set_xticklabels(rotation=45,horizontalalignment='right')
        #plot2.savefig(os.path.join(params['data_dump_path'],'plot2.png'))
        pdf_pages.savefig(plot3.fig)

        #######################################################
        # recall score X face 
        plot4 = sb.catplot(x="stimulus_id",y="perc_recall",kind='box',data=recallDat)
        plot4.set_xticklabels(rotation=45,horizontalalignment='right')
        #plot3.savefig(os.path.join(params['data_dump_path'],'plot3.png'))
        pdf_pages.savefig(plot4.fig)

        #######################################################
        # recall score X trial
        plot5 = sb.catplot(x="trial",y="perc_recall",kind='box',data=recallDat)
        plot5.set_xticklabels(rotation=45,horizontalalignment='right')
        #plot4.savefig(os.path.join(params['data_dump_path'],'plot4.png'))
        pdf_pages.savefig(plot5.fig)

        #######################################################
        # recall score X feature type
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial'], value_vars=['face_name_hit', 'location_hit', 'job_hit','hobby_hit','relation_hit','relation_name_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','variable'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'variable': 'feature','value':'perc_recall'})
        plot6 = sb.catplot(x="feature",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot6.set_xticklabels(rotation=45,horizontalalignment='right')
        #plot5.savefig(os.path.join(params['data_dump_path'],'plot5.png'))
        pdf_pages.savefig(plot6.fig)

        #######################################################
        # recall score X feature exemplar: name
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','face_name_resp_CA'], value_vars=['face_name_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','face_name_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'face_name_resp_CA':'face_name','value':'perc_recall'})
        plot7 = sb.catplot(x="face_name",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot7.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot7.fig)

        #######################################################
        # recall score X feature exemplar: location
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','location_resp_CA'], value_vars=['location_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','location_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'location_resp_CA':'location','value':'perc_recall'})
        plot8 = sb.catplot(x="location",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot8.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot8.fig)

        #######################################################
        # recall score X feature exemplar: job
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','job_resp_CA'], value_vars=['job_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','job_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'job_resp_CA':'job','value':'perc_recall'})
        plot9 = sb.catplot(x="job",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot9.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot9.fig)

        #######################################################
        # recall score X feature exemplar: hobby
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','hobby_resp_CA'], value_vars=['hobby_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','hobby_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'hobby_resp_CA':'hobby','value':'perc_recall'})
        plot10 = sb.catplot(x="hobby",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot10.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot10.fig)

        #######################################################
        # recall score X feature exemplar: relation
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','relation_resp_CA'], value_vars=['relation_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','relation_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'relation_resp_CA':'relation','value':'perc_recall'})
        plot11 = sb.catplot(x="relation",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot11.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot11.fig)

        #######################################################
        # recall score X feature exemplar: relation_name
        #need to convert columns to rows. 
        tmp = recallDat.reset_index()
        recallDat_long = pd.melt(tmp, id_vars=['subject_id','trial','relation_name_resp_CA'], value_vars=['relation_name_hit'])
        featureSubRecallScores = recallDat_long.groupby(['subject_id','relation_name_resp_CA'])['value'].mean()  #get subXfeat level score
        featureSubRecallScores = featureSubRecallScores.to_frame().reset_index()
        featureSubRecallScores = featureSubRecallScores.rename(columns= {'relation_name_resp_CA':'relation_name','value':'perc_recall'})
        plot12 = sb.catplot(x="relation_name",y="perc_recall",kind='box',data=featureSubRecallScores)
        plot12.set_xticklabels(rotation=45,horizontalalignment='right')
        pdf_pages.savefig(plot12.fig)

        










