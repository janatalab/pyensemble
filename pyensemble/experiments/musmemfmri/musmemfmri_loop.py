# musmemfmri_loop.py
import pdb
import os, csv
import random
#import json

from django.conf import settings
from django.db.models import Q, Count, Min

from pyensemble.models import Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

study_params = {
    'musmemfmri_loop_pilot': {
        'ignore_subs': ['04ktb89211','01mtt89012'],
        'breakAfterTheseTrials': ['trial10','trial20','trial30'],
        'practice_face_stim_ids': [840, 841],
        'face_stim_ids': [range(820,820+20)],
        'encoding_bio_duration_ms': 16000,#16000
        'encoding_bio_feedback_duration_ms': 8000,
        'encoding_1back_question_duration_ms': 8000,
        'encoding_rest_duration_ms': 10000,
        'encoding_trials_1-20': range(146,146+20),
        'encoding_trials_21-40': range(166,166+20),
        'bioFeature_names': ['face_name','location','job','hobby','relation','relation_name'],
        'bio_template': ['Hi, my name is [insert_face_name]. ' +
                'I live in [insert_location] and work as a [insert_job]. ' +
                'I enjoy [insert_hobby] in my spare time with my [insert_relation] [insert_relation_name].']
    }
}

# Imports stimuli for Angela Nazarian's jingle study
#@login_required
def import_stims(stimin):#removed request arg. stimdir=stimdir
    #stimin='/home/bmk/stims2upload/' 
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimin) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)
    print(mediadirs)
    for media_type in mediadirs:
        # Get an attribute corresponding to this media type
        attribute, ehn = Attribute.objects.get_or_create(name='Media Type', attribute_class='stimulus')
        
        #import pdb; pdb.set_trace()
        print(f'Working on {media_type}s ...')

        # Loop over files in the directory
        with os.scandir(os.path.join(stimin,media_type)) as stimlist:
            for stim in stimlist:
                if not stim.name.startswith('.') and stim.is_file():
                    print(f'\tImporting {stim.name}')

                    # Strip off the extension
                    fstub,fext = os.path.splitext(stim.name)

                    # Create the stimulus object
                    stimulus, _ = Stimulus.objects.get_or_create(
                        name=fstub,
                        playlist='Musmem fMRI',
                        file_format=fext,
                        location=os.path.join(rootdir,media_type,stim.name)
                        )

                    # Create a stimulusXattribute entry
                    #import pdb; pdb.set_trace()
                    stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=media_type)

    return print('pyensemble/message.html',{'msg':'Successfully imported the stimuli'})
    #return render(request,'pyensemble/message.html',{'msg':'Successfully imported the stimuli'})

def import_attributes(stimin):
    #stimin='/home/bmk/stims2upload/musmemfmri_attribute_uploadsV2.csv'
    #load up the csv file
    #with open(stimdir,'rt', encoding='ISO-8859-1') as f:
    with open(stimin,'rt', encoding='ISO-8859-1') as f:
        reader = csv.reader(f)
        nattrib = 0
        # Get the column headers
        columns = next(reader)

        # Get a dictionary of column indexes
        cid = {col:idx for idx, col in enumerate(columns)}
        # Iterate over the rows
        for row in reader:
            nattrib +=1
            name = row[cid['name']]
            nclass = row[cid['class']]
            print(f"Processing attribute {nattrib}: {name}")
            attribute, _ = Attribute.objects.get_or_create(name=name, attribute_class=nclass)

    return print('pyensemble/message.html',{'msg':'Successfully imported the attributes'})

def assign_face_stim(request,*args,**kwargs):
    #This function assembles the bios and assigns them to trials
    #in the attr X attr table

    NotAPracticeTrial = True #set this flag

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our experiment session info
    #expsessinfo = request.session['experiment_%d'%(session.experiment.id)]

    # Get our subject
    subject = session.subject

    #get the session var
    #expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))

    # Grab the face stims
    try:
        #practice_stims = Stimulus.objects.get(id=params['practice_face_stim_ids'])
        face_stims = Stimulus.objects.filter(id__in=params['face_stim_ids'][0])
    except:
        print(f'Cannot find face stims')


    #grab all previous subs who have participated
    all_prev_subids = Response.objects.filter(experiment_id=session.experiment.id,).values_list('subject_id',flat=True).distinct()
    all_prev_subs = Subject.objects.filter(subject_id__in=all_prev_subids)
    prev_subs = all_prev_subs.exclude(subject_id__in=params['ignore_subs'])
        

    #OK, so let's just try and just get em assigned once, so it's easier to test the db
    curr_face_stims = face_stims #need to remove faces once's we've assigned one
    triallAttrIDsRun1 = params['encoding_trials_1-20']
    for itrial in range(0,len(triallAttrIDsRun1)):

        currentTrial = Attribute.objects.get(id=str(triallAttrIDsRun1[itrial]))

        # Check to see if we already assigned a bio for this trial 

        currBioDic, currBio = doesThisBioExist(subject,currentTrial,params)
        
        if not currBioDic:
            curr_stims_x_pres = [] #tally number of times face was assigned to this trial
            print(f'Creating and loggin a new bio')
            #for each trial, find the face least often assigned across previous subs and
            #choose that one
            #grab all names of all stims presented on this trial (includes)
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentTrial,mapping_name__in=prev_subs,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
            for iface in range(0,len(curr_face_stims)):
                if curr_face_stims[iface].name in thisTrialPrevFaces:
                    #if the current face is in this Q, count the number of times
                    curr_stims_x_pres.append([*thisTrialPrevFaces].count(curr_face_stims[iface].name))
                else:
                    #it hasn't been presented on this trial yet, so add 0
                    curr_stims_x_pres.append(0)

            #this is idx from curr_stims_x_pres of the stims presented least often
            final_face_idxs = [i for i, x in enumerate(curr_stims_x_pres) if x == min(curr_stims_x_pres)]

            #randomly select the face, 
            choose_this_face_idx = final_face_idxs[random.randrange(0,len(final_face_idxs))]
            currFaceStim = curr_face_stims[choose_this_face_idx]
            #import pdb; pdb.set_trace() 
            #need to ensure it doesn't get picked in a subsequent step
            curr_face_stims = curr_face_stims.exclude(name=curr_face_stims[choose_this_face_idx].name)

            # Grab and assemble a random bio (for a male); 
            currBioDic, currBio = assembleThisBio(subject,currFaceStim,currentTrial,params,prev_subs)
            #import pdb; pdb.set_trace() 
            # Save the particular bio config so we know what it was later on!
            tmp = logThisBio(subject,currBioDic,currentTrial,params)
        else:
            #remove the face incase we need to assign more trials 
            #need to ensure it doesn't get picked in a subsequent step
            curr_face_stims = curr_face_stims.exclude(name=currBioDic['picture'].name)

        #print('currBio')
        #print(currBio)
        #print(itrial)
        #print(str(triallAttrIDsRun1[itrial]))
        #import pdb; pdb.set_trace() 
        
    #import pdb; pdb.set_trace()    
    curr_face_stims = face_stims #need to remove faces once's we've assigned one
    triallAttrIDsRun2 = params['encoding_trials_21-40']
    for itrial in range(0,len(triallAttrIDsRun2)):
        currentTrial = Attribute.objects.get(id=triallAttrIDsRun2[itrial])

        # Check to see if we already assigned a bio for this trial 
        currBioDic, currBio = doesThisBioExist(subject,currentTrial,params)
        if not currBioDic:
            curr_stims_x_pres = [] #tally number of times face was assigned to this trial
            print(f'Creating and loggin a new bio')
            currentOldTrial = Attribute.objects.get(id=str(triallAttrIDsRun1[itrial]))
            #grab all names of all stims presented on this trial (includes)
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentOldTrial,mapping_name__in=prev_subs,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
            for iface in range(0,len(curr_face_stims)):
                if curr_face_stims[iface].name in thisTrialPrevFaces:
                    #if the current face is in this Q, count the number of times
                    curr_stims_x_pres.append([*thisTrialPrevFaces].count(curr_face_stims[iface].name))
                else:
                    #it hasn't been presented on this trial yet, so add 0
                    curr_stims_x_pres.append(0)

            #this is idx from curr_stims_x_pres of the stims presented least often
            min_n_pres_idxs = [i for i, x in enumerate(curr_stims_x_pres) if x == min(curr_stims_x_pres)]

            #grab the orig bio trial (bio doesn't get modified) so we can exclude this face from this trial
            tmpBioDic, currBio = doesThisBioExist(subject,currentOldTrial,params)

            remove_face_idxs = [i for i, x in enumerate(curr_face_stims.values_list('name',flat=True)) if x == tmpBioDic['picture'].name]
            
            #import pdb; pdb.set_trace()
            #remove the prev. face idx from the possibilities 
            try:
                final_face_idxs = min_n_pres_idxs.remove(remove_face_idxs)
            except:
                final_face_idxs = min_n_pres_idxs

            #randomly select the face, 
            choose_this_face_idx = final_face_idxs[random.randrange(0,len(final_face_idxs))]
            curr_face = curr_face_stims[choose_this_face_idx]

            #need to ensure it doesn't get picked in a subsequent step
            curr_face_stims = curr_face_stims.exclude(name=curr_face_stims[choose_this_face_idx].name)

            #now grab the bio already created for this face and assign it to the current trial
            oldTrialThisFace = AttributeXAttribute.objects.filter(mapping_name=subject.subject_id,mapping_value_text=curr_face.name,child__attribute_class='relation_name')
            currBioDic, currBio = doesThisBioExist(subject,oldTrialThisFace[0].parent,params)

            #import pdb; pdb.set_trace()
            # Save the particular bio config so we know what it was later on!
            tmp = logThisBio(subject,currBioDic,currentTrial,params)
        else:
            #remove the face incase we need to assign more trials 
            #need to ensure it doesn't get picked in a subsequent step
            curr_face_stims = curr_face_stims.exclude(name=currBioDic['picture'].name)

        #print('currBioDic2')
        #print(currBio)
        #print(itrial)
        #print(str(triallAttrIDsRun2[itrial]))
        #import pdb; pdb.set_trace()  

    timeline = [{'nothing':'nothing'}] #pass dummy along

    return(timeline,'')

def present_rest_message(request,*args,**kwargs):
    #DOESN"T WORK !
    # present a string describing progress through task 
    timeline = []

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialAttribute']

    # grab the lst two char (numbers) in the attr. name
    if lastTrialAttribute=='NULL':
        tmpTrialNum = 10 #means we are in recall task.
        # how many trials total? (40)
        currprog = (tmpTrialNum/20)*100
    else:
        tmpTrialNum = int(lastTrialAttribute[-2:])
        # how many trials total? (40)
        currprog = (tmpTrialNum/40)*100

    # increment them by 1 and put back into the string
    currpromt = 'Great work so far! You have completed %02d%% of the task.'%(currprog)

    trial = {
            'type': 'image-keyboard-response',
            'stimulus': '',
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': params['encoding_rest_duration_ms'],
            'trial_duration': params['encoding_rest_duration_ms'],
            'prompt': currpromt
        }

    # Push the trial to the timeline
    timeline.append(trial)
    #import pdb; pdb.set_trace() #test if it ges here if time4rest is false (doesn't)

    return(timeline, '')

def time4rest(request,*args,**kwargs):
    #return True when it's time for a rest form to be presented
    #should be based on the trial param in the session info
    #also clears the misc info after each trial 
    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialAttribute']

    #get trial counter for final recall task (trial IDs randomized)
    try:
        breaknum = expsessinfo['curr_recall_trial']
    except:
        breaknum = 999
    
    #clear misc_info etc. 
    expsessinfo['misc_info'] = ''
    expsessinfo['currPostBioQ'] = 'NULL' #mark it as used for sanity 
    request.session.modified = True 


    #import pdb; pdb.set_trace()
    # if it's practice_trial, go ahead and present trial01
    if lastTrialAttribute in params['breakAfterTheseTrials']:
        #take a break! 
        time2rest = True
    elif breaknum in ['10']:
        time2rest = True
    else:
        time2rest = False

    return time2rest

def select_stim(request,*args,**kwargs):
    # script selects previoulsy assembled face bios from the attr x attr table 

    # Construct a jsPsych timeline
    # https://www.jspsych.org/overview/timeline/
    #
    timeline = []

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialAttribute']

    expsessinfo['misc_info'] = 'NULL' #reset it for sanity 

    
    # if it's practice_trial, go ahead and present trial01
    if lastTrialAttribute == 'trial_practice':
        currTrialAttribute = Attribute.objects.get(name='trial01')

    else:
        # grab the lst two char (numbers) in the attr. name
        tmpTrialNum = int(lastTrialAttribute[-2:])
        # increment them by 1 and put back into the string
        tmpTrialNum = tmpTrialNum + 1
        # grab the attribute for the new trial 
        currTrialAttribute = Attribute.objects.get(name='trial%02d'%tmpTrialNum)


    # Check to see if we already assigned a bio for this trial 
    currBioDic, currBio = doesThisBioExist(subject,currTrialAttribute,params)
    if not currBioDic:
        print(f'SOMETHING IS WRONG. CANNOT FIND TRIAL')
        import pdb; pdb.set_trace()
        # Something went wrong, bio should already exist 


    thisStim = currBioDic['picture']
    #
    # Now, set up the jsPsych trial
    #
    #import pdb; pdb.set_trace()
    #try to add some html markup to get the bio to not spread so far
    currBio_html = '<div style="margin-top:00%; margin-left:30%; margin-right:30%; display:inline-block; vertical-align:top;">'+currBio+'</div>'
    trial = {
            'type': 'image-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,thisStim.location.url),
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': params['encoding_bio_duration_ms'],
            'trial_duration': params['encoding_bio_duration_ms'],
            'prompt': currBio_html
        }
    #import pdb; pdb.set_trace()
    # Push the trial to the timeline
    timeline.append(trial)

    # NOTE THAT THIS DOESN"T RECORD A STIMULUS IN THE RESPONSE TABLE
    #but if we have the trial attributes assigned we can use those.
    addParams2Session(currBioDic,currTrialAttribute,request,session_id,params)

    #import pdb; pdb.set_trace()

    return(timeline, thisStim.id) 

def addParams2Session(currBioDic,TrialAttribute,request,session_id,params):
    #add the bio info to the session data to later write out in response table
    #add name of the form we want (which feature question are we answering)
    #we should also add the trial info stuff 

    #need to serialize this info, but first reduce it to the actual names
    saveThisBioDic = {}
    saveThisBioDic['trial_attribute_name'] = TrialAttribute.name
    for iftr in currBioDic:
        try:
            saveThisBioDic[iftr] = currBioDic[iftr].name
        except:
            saveThisBioDic[iftr] = currBioDic[iftr] #not a DB object


    import pdb; pdb.set_trace()
    # Get the current session and apend info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    expsessinfo['currTrialAttribute'] = TrialAttribute.name
    expsessinfo['misc_info'] = json.dumps(saveThisBioDic)
    expsessinfo['currPostBioQ'] = params['bioFeature_names'][random.randrange(0,len(params['bioFeature_names']))]
    #import pdb; pdb.set_trace()
    request.session.modified = True 

def clear_trial_sess_info(request,*args,**kwargs):
    # Extract our session ID
    session_id = kwargs['session_id']

    #clear misc_info etc. 
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    expsessinfo['currTrialAttribute'] = 'NULL'
    expsessinfo['misc_info'] = ''
    expsessinfo['currPostBioQ'] = ''
    #import pdb; pdb.set_trace()
    #import pdb; pdb.set_trace()
    request.session.modified = True 

    timeline = [{'nothing':'nothing'}] #pass dummy along

    return(timeline,'')

# Create our attribute X attribute entries for a specific bio
def logThisBio(subject,currBioDic,currTrialAttribute,params):
    #enter each feature for a pic; parent attrb is the current trial type/number
    for iftr in params['bioFeature_names']:
        mappingName = subject.subject_id
        mappingValText = currBioDic['picture'].name
        childattr = currBioDic[iftr]
        parentattr = currTrialAttribute

        #import pdb; pdb.set_trace()   
        print(f'creating entry for: ' +mappingName+' '+mappingValText+' '+childattr.name+' '+parentattr.name)     
        try:
            axa = AttributeXAttribute.objects.get_or_create(child=childattr, parent=parentattr,mapping_value_text = mappingValText, mapping_name=mappingName)
        except:
            print(f'failed to create attr X attr entry!')
            axa = ''

    return axa
    
# Return the bioDic and bio text if trial already exists in attr X attr table
def doesThisBioExist(subject,currTrialAttribute,params):
    currTrialEntry = AttributeXAttribute.objects.filter(parent=currTrialAttribute, 
                    mapping_name=subject.subject_id)
     
    #build up the dictionary with all features
    bio = params['bio_template'][0]

    try:
        #get the picture name
        picName = currTrialEntry.values_list('mapping_value_text',flat=True)[0]

        #get the picture stimulu
        currBioDic = {'picture': Stimulus.objects.get(name=picName)}

        for iftr in params['bioFeature_names']: 
            currAttr = Attribute.objects.get(name=iftr)
            thisTrialEntry = AttributeXAttribute.objects.filter(parent=currTrialAttribute,mapping_name=subject.subject_id,child__attribute_class=currAttr.name)
            # now grab the attribute for that specific feature instance 
            currBioDic[iftr] = Attribute.objects.get(id=thisTrialEntry.values_list('child',flat=True)[0])
            # fill in the bio
            if iftr == 'job' and currBioDic[iftr].name[0] in ['a','e','i','o','u']:
                #need to adjust 'a' or 'an'
                bio = bio.replace('a [insert_'+iftr+']','an '+currBioDic[iftr].name)
            else:
                bio = bio.replace('[insert_'+iftr+']',currBioDic[iftr].name)
    except:
        #doesn't exist
        currBioDic = {}
    
    return currBioDic, bio



