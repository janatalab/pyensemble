# musmemfmri_bio.py
from . import bio_params as bp
import pdb
import os, csv
import random
import json
from fuzzywuzzy import fuzz

from django.conf import settings
from django.db.models import Q, Count, Min

from pyensemble.models import Subject, Response, Session, Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

study_params = bp.bio_params()

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

def import_stimXattributes(stimin):
    #stimin='/home/bmk/stims2upload/musmemfmri_stimXattribute_uploads.csv'

    with open(stimin,'rt', encoding='ISO-8859-1') as f:
        reader = csv.reader(f)
        nattrib = 0
        # Get the column headers
        columns = next(reader)

        # Get a dictionary of column indexes
        cid = {col:idx for idx, col in enumerate(columns)}

        for row in reader:
            # Get a stimulus object based on the id
            stimid = row[cid['stimulus_id']]
            try:
                thisstim = Stimulus.objects.get(id=stimid)
            except:
                print(f'Unable to locate stimulus with id {stimid}')
                continue
            print

            # Get a attribute object based on the id
            attrid = row[cid['attribute_id']]
            try:
                thisattr = Attribute.objects.get(id=attrid)
            except:
                print(f'Unable to locate attribute with id {attrid}')
                continue
            print

            print(f"Processing stimXattribute: {thisstim.name} X {thisattr.name}")

            value_text = thisattr.name
            value_float = None

            # Create our stimulusxattribute entry
            import pdb; pdb.set_trace()
            sxa, created = StimulusXAttribute.objects.get_or_create(stimulus=thisstim, attribute=thisattr, attribute_value_text=value_text, attribute_value_double=value_float)

    return print('pyensemble/message.html',{'msg':'Successfully imported the stim X attribute file'})

def import_attributesXattribute(stimin):
    #stimin='/home/bmk/stims2upload/musmemfmri_stat_attributes.csv'

    with open(stimin,'rt', encoding='ISO-8859-1') as f:
        reader = csv.reader(f)
        nattrib = 0
        # Get the column headers
        columns = next(reader)

        # Get a dictionary of column indexes
        cid = {col:idx for idx, col in enumerate(columns)}

        for row in reader:
            # Get a stimulus object based on the id
            attr1 = row[cid['child']]
            try:
                childattr = Attribute.objects.get(name=attr1)
            except:
                print(f'Unable to locate attribute with name {attr1}')
                continue
            print

            # Get a attribute object based on the id
            attr2 = row[cid['parent']]
            try:
                parentattr = Attribute.objects.get(name=attr2)
            except:
                print(f'Unable to locate attribute with name {attr2}')
                continue
            print

            print(f"Processing attributeXattribute: {childattr.name} X {parentattr.name}")

            # Create our attribute X attribute entry
            axa = AttributeXAttribute.objects.get_or_create(child=childattr, parent=parentattr, mapping_name='',)
            #import pdb; pdb.set_trace()

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
    #grab subs who have entry in attrXattr (subs have that before anything is logged into the response table)
    triallAttrIDs = [format(x, '02d') for x in params['encoding_trials_1-20']]
    triallAttrs = Attribute.objects.filter(id__in=triallAttrIDs,attribute_class='bio_trials').values_list('name',flat=True)
    OurSubAxAentries = AttributeXAttribute.objects.filter(parent_id__in=triallAttrIDs,parent__attribute_class='bio_trials').exclude(mapping_name__in=params['ignore_subs']).values_list('mapping_name',flat=True).distinct()

    all_prev_subs = Subject.objects.filter(subject_id__in=OurSubAxAentries)
    prev_subs = all_prev_subs.exclude(subject_id__in=params['ignore_subs'])
    
    curr_face_stims = face_stims #need to remove faces once's we've assigned one
    triallAttrIDsRun1 = params['encoding_trials_1-20']

    #need to start with trial 20 and go backwards sometimes for CB purposes...
    #frees up all face pic options for trial 20
    if (len(prev_subs) % 2) == 0:
        oddnum = False
        trials2loopover = range(0,len(triallAttrIDsRun1))
    else:
        oddnum = True
        trials2loopover = range(len(triallAttrIDsRun1)-1,-1,-1)

    #for itrial in range(0,len(triallAttrIDsRun1)):
    for itrial in trials2loopover:

        currentTrial = Attribute.objects.get(id=str(triallAttrIDsRun1[itrial]))

        # Check to see if we already assigned a bio for this trial 

        currBioDic, currBio = doesThisBioExist(subject,currentTrial,params)
        
        if not currBioDic:
            curr_stims_x_pres = [] #tally number of times face was assigned to this trial
            print(f'Creating and loggin a new bio')
            #for each trial, find the face least often assigned across previous subs and
            #choose that one
            #grab all names of all stims presented on this trial (includes)
            #pdb.set_trace()
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentTrial,parent__attribute_class='bio_trials',mapping_name__in=prev_subs,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
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
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentOldTrial,parent__attribute_class='bio_trials',mapping_name__in=prev_subs,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
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
    print(f'last trial: '+lastTrialAttribute)
    # if it's practice_trial, go ahead and present trial01
    if lastTrialAttribute == 'trial_practice':
        currTrialAttribute = Attribute.objects.get(name='trial01',attribute_class='bio_trials')

    else:
        # grab the lst two char (numbers) in the attr. name
        tmpTrialNum = int(lastTrialAttribute[-2:])
        # increment them by 1 and put back into the string
        tmpTrialNum = tmpTrialNum + 1
        # grab the attribute for the new trial 
        currTrialAttribute = Attribute.objects.get(name='trial%02d'%tmpTrialNum,attribute_class='bio_trials')

    print(f'this trial: '+currTrialAttribute.name)

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

def stim_feedback(request,*args,**kwargs):
    # did they get the  trial correct? (for main encoding task)
    # if so return False, otherwise return True so that we see form telling them 
    # to try again. 
    timeline = []

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    form_names = params['form_names']

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=kwargs['session_id']).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialAttribute']

    #grab the last response to the practice stim 
    last_response = Response.objects.filter(session=kwargs['session_id'],form__name__in=form_names, stimulus_id=expsessinfo['stimulus_id']).last()

    #gsort to get most resent incase there are multiple 

    currentPartAnswerString = last_response.response_text

    #figure out which feature we asked about 
    currentFeature = expsessinfo['currPostBioQ']

    #now grab the correct answers
    ThisBioDic = json.loads(expsessinfo['misc_info'])
    currentCorrectAnswerString = ThisBioDic[currentFeature]

    #now do some fuzzy matching to see if it's correct
    matchScore = fuzz.ratio(currentPartAnswerString.lower(), currentCorrectAnswerString.lower())

    if matchScore >= 85:
        needMorePractice = 'your answer is correct!'
        results = 'correct'
    elif matchScore >= 70:
        needMorePractice = 'close, but watch your spelling!'
        results = 'verify'
    else:
        needMorePractice = 'your answer is incorrect!'
        results = 'incorrect'

    #import pdb; pdb.set_trace()
    # Grab the face and bio again to present with feedback
    currBioDic, currBio = doesThisBioExist(subject,Attribute.objects.get(name=lastTrialAttribute),params)
    if not currBioDic:
        print(f'SOMETHING IS WRONG. CANNOT FIND TRIAL')
        import pdb; pdb.set_trace()
        # Something went wrong, bio should already exist 

    thisStim = currBioDic['picture']
    #
    # Now, set up the jsPsych trial
    #
    currBio_html = '<div style="margin-top:00%; margin-left:30%; margin-right:30%; display:inline-block; vertical-align:top;"><p><b>'+needMorePractice+'</b></p><p>'+currBio+'</p></div>'
    trial = {
            'type': 'image-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,thisStim.location.url),
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': params['encoding_bio_feedback_duration_ms'],
            'trial_duration': params['encoding_bio_feedback_duration_ms'],
            'prompt': currBio_html
        }
    #import pdb; pdb.set_trace()
    # Push the trial to the timeline
    timeline.append(trial)

    currBioDic['feedback'] = results #doesn't actually add anything because the form_stimulus_s doesn't add anything 2 DB 
    addParams2Session(currBioDic,Attribute.objects.get(name=lastTrialAttribute),request,session_id,params)
    # do want to update misc_info though! 

    #import pdb; pdb.set_trace()

    return(timeline, thisStim.id) 

def select_practice_stim(request,*args,**kwargs):
    #i don't think there is really a big issue with using a relation_name and the reg. features 
    #(even though they'll get remapped onto a real bio during the task)

    # Construct a jsPsych timeline
    # https://www.jspsych.org/overview/timeline/
    #
    timeline = []

    NotAPracticeTrial = False #set this flag

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

    # Grab the practice stim
    try:
        #practice_stims = Stimulus.objects.get(id=params['practice_face_stim_ids'])
        practice_stims = Stimulus.objects.filter(id__in=params['practice_face_stim_ids'])
    except:
        print(f'Unable to locate practice faces with id ')

    try:
        sexAttributes = Attribute.objects.get(name='male')
    except:
        print(f'Unable to locate attribute with name: male')

    thisStim = practice_stims.filter(stimulusxattribute__attribute__id=sexAttributes.id)

    # Get the appropraite Trial attribute
    TrialAttribute = Attribute.objects.get(name='trial_practice')

    # Check to see if we already assigned a bio for this trial 
    currBioDic, practice_bio = doesThisBioExist(subject,TrialAttribute,params)
    if not currBioDic:
        #import pdb; pdb.set_trace()
        # Grab and assemble a random bio (for a male); use the name Jim; 
        currBioDic, practice_bio = assembleThisBio(subject,thisStim[0],NotAPracticeTrial,params,[])
        # Save the particular bio config so we know what it was later on!
        tmp = logThisBio(subject,currBioDic,TrialAttribute,params)

    #
    # Now, set up the jsPsych trial
    #
    currBio_html = '<div style="margin-top:00%; margin-left:30%; margin-right:30%; display:inline-block; vertical-align:top;">'+practice_bio+'</div>'
    trial = {
            'type': 'image-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,thisStim[0].location.url),
            'stimulus_height': None,
            'stimulus_width': None,
            'choices': 'none',
            'stimulus_duration': params['encoding_bio_duration_ms'],
            'trial_duration': params['encoding_bio_duration_ms'],
            'prompt': currBio_html
        }

    # Push the trial to the timeline
    timeline.append(trial)

    # NOTE THAT THIS DOESN"T RECORD A STIMULUS IN THE RESPONSE TABLE
    #but if we have the trial attributes assigned we can use those.
    addParams2Session(currBioDic,TrialAttribute,request,session_id,params)

    return(timeline, thisStim[0].id)

def practice_stim_feedback(request,*args,**kwargs):
    # did they get the practice trial correct? 
    # if so return False, otherwise return True so that we see form telling them 
    # to try again. 
    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=kwargs['session_id']).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialAttribute']

    #grab the last response to the practice stim 
    last_response = Response.objects.filter(session=kwargs['session_id'],form__name__in=params['form_names'], stimulus_id=expsessinfo['stimulus_id']).last()

    #gsort to get most resent incase there are multiple 

    currentPartAnswerString = last_response.response_text

    #figure out which feature we asked about 
    currentFeature = expsessinfo['currPostBioQ']

    #now grab the correct answers
    ThisBioDic = json.loads(expsessinfo['misc_info'])
    currentCorrectAnswerString = ThisBioDic[currentFeature]

    #now do some fuzzy matching to see if it's correct
    matchScore = fuzz.ratio(currentPartAnswerString.lower(), currentCorrectAnswerString.lower())

    if matchScore >= 85:
        #count it as correct. and advance
        needMorePractice = False
    else:
        needMorePractice = True

    return(needMorePractice)

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

def assign_recall_order(request,*args,**kwargs):
    #i guess we may as well counterbalance based on the order this sub got 
    #on run 1 and 2 (choosing least frequent location)
    #in the end we want a list with the trial.name in order [trial09 trial02 trial20 ...]
    #keep this in session, and we will iterate through in select_recall_stim()
    
    NotAPracticeTrial = True #set this flag

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # Grab the face stims
    try:
        #practice_stims = Stimulus.objects.get(id=params['practice_face_stim_ids'])
        face_stims = Stimulus.objects.filter(id__in=params['face_stim_ids'][0])
    except:
        print(f'Cannot find face stims')
        
    recall_trial_order = [] #init this list to store in exp sess info later on
    #OK, so let's just try and just get em assigned once, so it's easier to test the db
    curr_face_stims = face_stims #need to remove faces once's we've assigned one
    triallAttrIDsRun1 = params['encoding_trials_1-20']
    triallAttrIDsRun2 = params['encoding_trials_21-40']
    for itrial in range(0,len(triallAttrIDsRun1)):

        currentTrial = Attribute.objects.get(id=str(triallAttrIDsRun1[itrial]))
        currentTrial_r2 = Attribute.objects.get(id=str(triallAttrIDsRun2[itrial]))

        # grab the bio for this trial 
        currBioDic, currBio = doesThisBioExist(subject,currentTrial,params)
        
        if currBioDic:
            curr_stims_x_pres = [] #tally number of times face was assigned to this trial
            print(f'Loading old bio')
            #for each trial, find the face least often assigned across previous subs and
            #choose that one
            #grab all names of all stims presented on this trial (includes)
            #going to treat r2 as instaces of 1-20
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentTrial,mapping_name=subject.subject_id,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
            thisTrialPrevFaces_r2 = AttributeXAttribute.objects.filter(parent=currentTrial_r2,mapping_name=subject.subject_id,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
            
            thisTrialPrevFaces = [*thisTrialPrevFaces]+[*thisTrialPrevFaces_r2]
            for iface in range(0,len(curr_face_stims)):
                if curr_face_stims[iface].name in thisTrialPrevFaces:
                    #if the current face is in this Q, count the number of times
                    curr_stims_x_pres.append([*thisTrialPrevFaces].count(curr_face_stims[iface].name))
                else:
                    #it hasn't been presented on this trial yet, so add 0
                    curr_stims_x_pres.append(0)

            #this is idx from curr_stims_x_pres of the stims presented least often
            final_face_idxs = [i for i, x in enumerate(curr_stims_x_pres) if x == min(curr_stims_x_pres)]
            #import pdb; pdb.set_trace() #make sure below code works!
            #randomly select the face, 
            choose_this_face_idx = final_face_idxs[random.randrange(0,len(final_face_idxs))]
            currFaceStim = curr_face_stims[choose_this_face_idx]
            #
            #need to ensure it doesn't get picked in a subsequent step
            curr_face_stims = curr_face_stims.exclude(name=curr_face_stims[choose_this_face_idx].name)

            #grab the trial number for this face and append to list 
            thisFacesPrevTrial = AttributeXAttribute.objects.filter(mapping_value_text=currFaceStim.name,mapping_name=subject.subject_id,child__attribute_class='relation_name')
            #import pdb; pdb.set_trace() 
            recall_trial_order.append(thisFacesPrevTrial[0].parent.name) #should return 2, first 1 should be earlier trial attribute we want 
            
        else:
            #can't find it?!
            print(f'WANRING: cannot find biodic')

    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    expsessinfo['recall_trial_order'] = recall_trial_order
    expsessinfo['curr_recall_trial'] = '0'
    #import pdb; pdb.set_trace()
    request.session.modified = True 

    timeline = [{'nothing':'nothing'}] #pass dummy along

    return(timeline,'')

def select_recall_stim(request,*args,**kwargs):
    # randomly select face to probe
    timeline = [{'nothing':'nothing'}] #pass dummy along
     # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    #import pdb; pdb.set_trace()
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    recall_trial_order = expsessinfo['recall_trial_order'] 
    curr_recall_trial = Attribute.objects.get(attribute_class='bio_trials',name=recall_trial_order[int(expsessinfo['curr_recall_trial'])])

    #get the face stim.id and the bio for this trial 
    thisFaceName = AttributeXAttribute.objects.filter(parent=curr_recall_trial,mapping_name=subject.subject_id,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
    thisFace = Stimulus.objects.get(name=thisFaceName[0])
    #update misc_info with bio and increase the curr_recall_trial var
    tmpTrialNum = int(expsessinfo['curr_recall_trial'])
    # increment them by 1 and put back into the string
    tmpTrialNum = tmpTrialNum + 1
    # grab the attribute for the new trial 
    expsessinfo['curr_recall_trial'] = '%d'%tmpTrialNum

    currBioDic, currBio = doesThisBioExist(subject,curr_recall_trial,params)
    if currBioDic:
        #need to serialize this info, but first reduce it to the actual names
        saveThisBioDic = {}
        saveThisBioDic['trial_attribute_name'] = curr_recall_trial.name
        for iftr in currBioDic:
            saveThisBioDic[iftr] = currBioDic[iftr].name
        expsessinfo['misc_info'] = json.dumps(saveThisBioDic)
    else:
        print(f'WARNING: could not find trial')

    #import pdb; pdb.set_trace() as
    request.session.modified = True 


    #stim should be the picture (face) we want 
    return(timeline,thisFace.id)

def assembleThisBio(subject,thisStim,NotAPracticeTrial,params,prev_subs):
    #function takes in face stim and assembles a bio
    bio = params['bio_template'][0]

    currBioDic = {'picture': thisStim} #use this dict later to log in db
    for iftr in params['bioFeature_names']:
        # get all the possible attributes 
        possibleAttributes = Attribute.objects.filter(attribute_class=iftr)

        #figure out gender of the chosen relation and limit names based on that
        if iftr in ['relation_name']:
            #the gender attribute id (parent) is linked to this in attr attr 
            #do we need to limit it to the current subect? Actually, I don't think so!
            #import pdb; pdb.set_trace()
            relationAxA = AttributeXAttribute.objects.filter(mapping_name='',child=currBioDic['relation'])#mapping_name=subject.subject_id
            #relationAxA = Attribute.objects.get(name=currBioDic['relation'].name)
            #relationAxA.parent #this is the gender

            #get all names with this gender
            namesAxA = AttributeXAttribute.objects.filter(parent=relationAxA[0].parent,child__attribute_class='relation_name')
            #namesAxA = AttributeXAttribute.objects.filter(parent=relationAxA.id,child__attribute_class='relation_name')
            
            if relationAxA[0].parent.name in ['male','female']:
                #don't need to add additional filtering for neutral case
                #filter names for gender
                possibleAttributes = possibleAttributes.filter(id__in=namesAxA.values_list('child',flat=True))
            elif relationAxA[0].parent.name in ['neutral']:
                #make sure no more than 3 of a sex get assigned to neutral relation names, otherwise
                #it will run out of, e.g., female names for female relations
                # grab neutral relation ids
                neutralRelationsAxA = AttributeXAttribute.objects.filter(parent=Attribute.objects.get(id=12),child__attribute_class='relation').values_list('child',flat=True)
                # get the trial ids for previous neutral trials for this particpant
                prevNeutralTrials = AttributeXAttribute.objects.filter(mapping_name=subject.subject_id,child__in=neutralRelationsAxA).exclude(parent='145').values_list('parent',flat=True)
                # get the relation_name assigned to those trials 
                prevNames = AttributeXAttribute.objects.filter(mapping_name=subject.subject_id,parent__in=prevNeutralTrials,child__attribute_class='relation_name').values_list('child',flat=True)

                prevFemaleNames = AttributeXAttribute.objects.filter(parent=Attribute.objects.get(id=11),child__in=prevNames).values_list('child',flat=True)
                prevMaleNames = AttributeXAttribute.objects.filter(parent=Attribute.objects.get(id=10),child__in=prevNames).values_list('child',flat=True)
                #OK< SO DON"T WANT TO JUST FILTER OUT PREVIOUS ASSIGNED NAMES< ALL NAMES OF THAT GENDER!!!
                if len(prevFemaleNames) > 2:
                    #get all the femal names
                    allFemaleNames = AttributeXAttribute.objects.filter(parent=Attribute.objects.get(id=11),child__attribute_class='relation_name').values_list('child',flat=True)
                    #filter out the female names
                    possibleAttributes = possibleAttributes.exclude(id__in=allFemaleNames)
                elif len(prevMaleNames) > 2:
                    #get all the male names
                    allMaleNames = AttributeXAttribute.objects.filter(parent=Attribute.objects.get(id=10),child__attribute_class='relation_name').values_list('child',flat=True)
                    #filter out the male names (don't assign anymore to neutral relation)
                    possibleAttributes = possibleAttributes.exclude(id__in=allMaleNames)
                #no need to modify if it hasn't hit the limit on neurtral name assignment 

        #figure out gender AND ethnicity of the chosen face and limit names based on that
        if iftr in ['face_name']:
            #the gender attribute id (parent) is linked to this in attr attr 
            sexAttrXstim = StimulusXAttribute.objects.get(stimulus = thisStim, attribute__attribute_class = 'sex')
            ethAttrXstim = StimulusXAttribute.objects.get(stimulus = thisStim, attribute__attribute_class = 'ethnicity')
            #thisAttrXstim.attribute_id #gender attribute

            #get all names with this gender and ethnicity
            names1 = AttributeXAttribute.objects.filter(parent__in=[sexAttrXstim.attribute],child__attribute_class='face_name').values_list('child',flat=True)
            names2 = AttributeXAttribute.objects.filter(parent__in=[ethAttrXstim.attribute],child__attribute_class='face_name').values_list('child',flat=True)
            possibleNames = set(names1) & set(names2)
            possiblenames = [*possibleNames, ]
            #import pdb; pdb.set_trace()
            
            #filter names for gender
            possibleAttributes = Attribute.objects.filter(id__in=possiblenames)
            #import pdb; pdb.set_trace()

        if NotAPracticeTrial:
            #going to randomize based on previous subjects assignments AND other trials. 
            #need a function here !!!!!!
            print(f'filtering bio assignments based on previous trials.')
            
            #search for all other attr x attr entries that have a child if with attribute_class=iftr (exclude the practie trialce)
            otherEntriesAxA = AttributeXAttribute.objects.filter(mapping_name=subject.subject_id,child__attribute_class=iftr).exclude(parent='145').values_list('child',flat=True)
            #import pdb; pdb.set_trace()
            if otherEntriesAxA:
                #filter out explemars that have already been assigned to a face (for this person)
                possibleAttributes = possibleAttributes.exclude(id__in = otherEntriesAxA)
            
            #now figure out which feature exemplar (of the one's left) has been assigned  the least across participants
            thisFacesPrevFeat = AttributeXAttribute.objects.filter(mapping_value_text=thisStim.name,mapping_name__in=prev_subs,child__attribute_class=iftr).exclude(parent='145').values_list('child',flat=True)
            if thisFacesPrevFeat:
                curr_feature_x_pres = []
                #the results really lists each assignment twice (logged for Run 1 and 2 (seperate trial attr ids))
                #filter out all except those that have been chosen the least amount of time
                for ipftr in range(0,len(possibleAttributes)):
                    if possibleAttributes[ipftr].id in thisFacesPrevFeat:
                        #if the current face is in this Q, count the number of times
                        curr_feature_x_pres.append([*thisFacesPrevFeat].count(possibleAttributes[ipftr].id))
                    else:
                        #it hasn't been presented on this trial yet, so add 0
                        curr_feature_x_pres.append(0)

                #import pdb; pdb.set_trace()
                #this is idx from curr_feature_x_pres of the stims presented least often
                final_feat_idxs = [i for i, x in enumerate(curr_feature_x_pres) if x == min(curr_feature_x_pres)]

                #randomly select the face, 
                
                #got ane rror here, may be a case where the fitlering removes all stims?
                #e.g., or if there is only 1 feature, does that lead the range call 0? 
                #don't think so, probably because relation_gender neutral thing. 
                try:
                    choose_this_feat_idx = final_feat_idxs[random.randrange(0,len(final_feat_idxs))]
                except:
                    pdb.set_trace() 

                currAttribte = possibleAttributes[choose_this_feat_idx]
            else:
                #no previous pairrings
                #import pdb; pdb.set_trace() 
                currAttribte = possibleAttributes[random.randrange(0,len(possibleAttributes))]

        else:
            print(f'Practice trial: previous bio assignments being ignored.')
            currAttribte = possibleAttributes[random.randrange(0,len(possibleAttributes))]

        currBioDic[iftr] = currAttribte #assign it for later entry in attrXattr

        # fill in the bio
        if iftr == 'job' and currBioDic[iftr].name[0] in ['a','e','i','o','u']:
            #need to adjust 'a' or 'an'
            bio = bio.replace('a [insert_'+iftr+']','an '+currBioDic[iftr].name)
        else:
            bio = bio.replace('[insert_'+iftr+']',currAttribte.name)

    return currBioDic, bio

def logThisBio(subject,currBioDic,currTrialAttribute,params):
    # Create our attribute X attribute entries for a specific bio
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
    
def doesThisBioExist(subject,currTrialAttribute,params):
    # Return the bioDic and bio text if trial already exists in attr X attr table
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

def post_bio_q2_face_name(request,*args,**kwargs):
    #should we present a question about the 'face_name'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'face_name':
        doit = True
    else:
        doit = False

    return(doit)

def post_bio_q2_location(request,*args,**kwargs):
    #should we present a question about the 'location'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'location':
        doit = True
    else:
        doit = False

    return(doit)

def post_bio_q2_job(request,*args,**kwargs):
    #should we present a question about the 'job'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'job':
        doit = True
    else:
        doit = False

    return(doit)

def post_bio_q2_hobby(request,*args,**kwargs):
    #should we present a question about the 'hobby'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'hobby':
        doit = True
    else:
        doit = False

    return(doit)

def post_bio_q2_relation(request,*args,**kwargs):
    #should we present a question about the 'relation'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'relation':
        doit = True
    else:
        doit = False

    return(doit)

def post_bio_q2_relation_name(request,*args,**kwargs):
    #should we present a question about the 'relation_name'? 
    #return True if we want it

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get the current trial info
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    #import pdb; pdb.set_trace()

    if expsessinfo['currPostBioQ'] == 'relation_name':
        doit = True
    else:
        doit = False

    return(doit)





