# musmemfmri_loop.py
from . import loop_params as lp #for some reason this needs "from . " in the _bio??

import pdb
import os, csv, re
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

study_params = lp.loop_params()


def import_stims(stimin):
    # Imports loop stimuli for musmemfmri study (creates attributes too)
    #stimin='/var/www/html/ensemble/stimuli/musmemfmristims/loops/' 
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimin) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)
    print(mediadirs)
    for media_type in mediadirs:
        if media_type == 'loops':
            # Get an attribute corresponding to this media type
            attribute, ehn = Attribute.objects.get_or_create(name='Media Type', attribute_class='stimulus')
            attribute2, ehn = Attribute.objects.get_or_create(name='loopsV1', attribute_class='stimulus')

            # Create the key attributes if they don't exist
            attributeC, ehn = Attribute.objects.get_or_create(name='Key of C', attribute_class='stimulus')
            attributeE, ehn = Attribute.objects.get_or_create(name='Key of E', attribute_class='stimulus')
            attributeAb, ehn = Attribute.objects.get_or_create(name='Key of Ab', attribute_class='stimulus')

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
                        #pdb.set_trace()
                        stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=media_type)
                        stimXattrib2, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute2, attribute_value_text=media_type)

                        # Add and attribute for key

                        if '_C' in fstub:
                            stimXattrib3, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attributeC, attribute_value_text=media_type)
                        elif '_E' in fstub:
                            stimXattrib3, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attributeE, attribute_value_text=media_type)
                        elif '_Ab' in fstub:
                            stimXattrib3, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attributeAb, attribute_value_text=media_type)



    return print('pyensemble/message.html',{'msg':'Successfully imported the stimuli'})
    #return render(request,'pyensemble/message.html',{'msg':'Successfully imported the stimuli'})

def import_attributes(stimin):
    #stimin='/home/bmk/stims2upload/musmemfmri_looptrial_attrs.csv'
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

def assign_loop_trials(request,*args,**kwargs):#request,*args,**kwargs
    #This function figures out which key version to use and assigns loops to trials
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

    #grab all previous subs who have participated
    all_prev_subids = Response.objects.filter(experiment_id=session.experiment.id).values_list('subject_id',flat=True).distinct()
    all_prev_subs = Subject.objects.filter(subject_id__in=all_prev_subids)
    prev_subs = all_prev_subs.exclude(subject_id__in=params['ignore_subs'])
    #subject session id is what's written to attr X attr, use this to get previous subs...
    prev_sess = Session.objects.filter(subject_id__in=prev_subs,experiment_id=session.experiment.id).values_list('id',flat=True).distinct()

    # Grab the loop stims
    try:
        #this includes 3 versions of each loop (keys) 
        loop_stims_long = Stimulus.objects.filter(stimulusxattribute__attribute_id__name=params['loop_attribute'])
    except:
        print(f'Cannot find loop stims')

    # get the unique names (minus key info at end), loop through each of these
    uloop_stim_names = []
    sloop_stim_names = []
    for iloop in loop_stims_long.values_list('name',flat=True):
        #remove key info part of string
        sloop_stim_names.append(re.sub('_.*', '', iloop))
    uloop_stim_names = [*set(sloop_stim_names), ]
    
    """ 
    ACTUALLY, if we want to make sure 1/3 of the trials are from each key, then we need to 
    pick the keys after we select the final 20 stims. 
    
    # Now pick the key of each loop we are going to use 
    # tally how many times each version of the stim has been presented across subs
    loop_stims = []#hold list of stim set to choose from. 
    for iloop in uloop_stim_names:
        tmp_loop_count = []
        for ikey in params['loop_keys']:
            #grab all previous instances for this loop
            thisLoop = iloop+'_'+ikey
            tmpq = AttributeXAttribute.objects.filter(parent__attribute_class='loop_trials',mapping_name__in=prev_sess,child__name='Key of '+ikey).values_list('mapping_value_text',flat=True)
            tmp_loop_count.append(tmpq.count())
        #get the min count idx
        min_key_idxs = [i for i, x in enumerate(tmp_loop_count) if x == min(tmp_loop_count)]
        choose_this_loop_idx = min_key_idxs[random.randrange(0,len(min_key_idxs))]
        loop_stims.append(iloop+'_'+params['loop_keys'][choose_this_loop_idx])

    pdb.set_trace()


    # random least frequent 
    """

    """
    On a given trial, 
    -get all the loopXtrialN instances (all subs)
    Filter out:
        -don’t want to pick these: get all the loopXtrialN*20 instances (loops previously heard in this run 
        position) (this sub), rem, run = 20 stims/trials
        -don’t want to pick these: get all the loops previously presented in this run (this sub) 
    -grab the stimulus that was presented on the last trial
    While theSame:
        -randomly choose 1 from the remaining possibilities 
        -grab the loops that have been presented before this loop previously (this sub) 
            -e.g., search for this loop in attrXattr (subject specific), get the previous trial numbers of this 
            loop (not current run), go back 1 trial from each and get the stimulus presented before
        -check to see if the last trial is in the above list (set to 1 if so, and start from top)
        -remove that stimulus from the list of remaining possibilities 
    *question here is whether or not it will ever run out of stims this way? 
    """

    pdb.set_trace() 
    run_list = sorted(params['run_params'].keys()) #need to go through runs in order
    previous_runs = []
    #OK, so let's just try and just get em assigned once, so it's easier to test the db
    for irun in run_list:
        pdb.set_trace()
        if irun in 'run1_trials':
            curr_loop_stims = uloop_stim_names #need to remove faces once's we've assigned one
        else:
            #grab all the stims present in the first run
            tmp_stims = AttributeXAttribute.objects.filter(parent__name__in=params['run_params']['run1_trials'],parent__attribute_class='loop_trials',mapping_name=str(session.id)).values_list('mapping_value_text',flat=True)
            r1_loop_stims = []
            for ist in tmp_stims:
                #remove key info part of string
                r1_loop_stims.append(re.sub('_.*', '', ist))
            curr_loop_stims = [*set(r1_loop_stims), ]
            pdb.set_trace()

        previous_runs.append(irun)
        for itrial in range(0,len(params['run_params'][irun])):

            currentTrial = Attribute.objects.get(name=params['run_params'][irun][itrial],attribute_class='loop_trials')
            currentTrialPosition = Attribute.objects.get(name=params['run_params']['run1_trials'][itrial],attribute_class='loop_trials')
            # Check to see if we already assigned a loop for this trial 
            currStim = doesThisTrialExist(session,currentTrial)
            
            if not currStim:
                curr_stims_x_pres = [] #tally number of times loop was assigned to this trial (across subs)
                print(f'Creating and loggin a new loop-trial')
                #for each trial, find the loop least often assigned across previous subs 
                #grab all names of all stims presented on this trial 
                #NOTE, second time through this limits the search to the 20 stims selected out of the 
                #total 41 during run1
                ###NEED TO FIX SESSION ID HERE SO IT GRABS ALL PREVIOUS SUBS INCLUDING THE CURRENT
                thisTrialPrevLoops = AttributeXAttribute.objects.filter(parent=currentTrialPosition,mapping_name__in=[str(session.id)],mapping_value_text__iregex=r'^%s'%(curr_loop_stims)).values_list('mapping_value_text',flat=True)

                #trip the thisTrialPrevLoops of key ending
                thisTrialStrpdPrevLoops = []
                for iloop in thisTrialPrevLoops:
                    #remove key info part of string
                    thisTrialStrpdPrevLoops.append(re.sub('_.*', '', iloop))

                #now go through and count the occurances 
                for iloop in range(0,len(curr_loop_stims)):
                    if curr_loop_stims[iloop] in thisTrialStrpdPrevLoops:
                        #if the current face is in this Q, count the number of times
                        curr_stims_x_pres.append([*thisTrialStrpdPrevLoops].count(curr_loop_stims[iloop]))
                    else:
                        #it hasn't been presented on this trial yet, so add 0
                        curr_stims_x_pres.append(0)
                
                #this is idx from curr_stims_x_pres of the stims presented least often
                min_loop_idxs = [i for i, x in enumerate(curr_stims_x_pres) if x == min(curr_stims_x_pres)]

                #pdb.set_trace() 
                if irun not in 'run1_trials':
                    #need to make sure stim isn't present in the same location as in a previous run
                    trials2check = [*range(itrial+1,20*(len(previous_runs)-1),20),]
                    pdb.set_trace()
                    prevLoopsThisPosition = AttributeXAttribute.objects.filter(parent__in=trials2check,parent__attribute_class='loop_trials',mapping_name__in=[str(session.id)]).values_list('mapping_value_text',flat=True)
                    remove_loop_idxs = [i for i, x in enumerate(curr_loop_stims) if x in prevLoopsThisPosition]
                    #remove the prev. face idx from the possibilities 
                    try:
                        final_loop_idxs = min_loop_idxs.remove(remove_loop_idxs)
                    except:
                        final_loop_idxs = min_loop_idxs
                    if len(final_loop_idxs)==0:
                        print(f'WARNING: ran out of possible loops!!!')
                        pdb.set_trace()

                    #while loop, 
                    #for this stim, get the ids of the stims that came before it
                    pdb.set_trace()
                    trials2check = [*range(itrial-1,20*len(previous_runs),20),]

                    #get the stim on the previous cuurrent trial
                    #if the latter is in the former list, pic another current stim

                    #randomly select the loop, 
                    choose_this_loop_idx = final_loop_idxs[random.randrange(0,len(final_loop_idxs))]
                    currStimName = curr_loop_stims[choose_this_loop_idx]
                    pdb.set_trace()
                    #grab the key the loop was presented in during run 1

                else:
                    #1st run
                    final_loop_idxs = min_loop_idxs

                    #randomly select the loop, 
                    choose_this_loop_idx = final_loop_idxs[random.randrange(0,len(final_loop_idxs))]
                    currStimName = curr_loop_stims[choose_this_loop_idx]

                    currStimNames = []
                    # add the key info back to names
                    for ikey in params['loop_keys']:
                        currStimNames.append(currStimName+'_'+ikey)
                    #now grab instance of this stim in every key
                    currStims = Stimulus.objects.filter(name__in = currStimNames)

                    # Now we select the key class
                    #first we need to mkae sure this sub hasn't already had too many of 1 class
                    ignore_keys = [] #key options for loop to filter out
                    for ikey in params['loop_keys']:
                        #get vals within this sub
                        tmpqThisSub = AttributeXAttribute.objects.filter(parent__attribute_class='loop_trials',mapping_name=str(session.id),child__name='Key of '+ikey).values_list('mapping_value_text',flat=True)
                        if len(tmpqThisSub)>=round(params['nUniqueLoops']/3):
                            ignore_keys.append(currStimName+'_'+ikey)
                    if len(ignore_keys)==3:
                        #if we removed the all above, then pick one randomly
                        #because one class needs to have 6, the others 7
                        ignore_keys = [] #

                    pdb.set_trace() 

                    #filter out the keys we are ignoring based on this subject
                    currStims = currStims.exclude(name__in=ignore_keys)

                    tmp_key_count_acrossSubs = []
                    # now get the counts for this stim-key across subject
                    for iloop in currStims:
                        #get vals across subs
                        tmpq = AttributeXAttribute.objects.filter(parent__attribute_class='loop_trials',mapping_name__in=prev_sess,mapping_value_text=iloop.name).values_list('mapping_value_text',flat=True)
                        tmp_key_count_acrossSubs.append(tmpq.count())

                    #do a check to see how many keys we've assigned to each one. if we have assign 
                    #get the min count idx
                    min_key_idxs = [i for i, x in enumerate(tmp_key_count_acrossSubs) if x == min(tmp_key_count_acrossSubs)]
                    choose_this_loop_idx = min_key_idxs[random.randrange(0,len(min_key_idxs))]
                    currStim = currStims[choose_this_loop_idx]

                    


                

                #import pdb; pdb.set_trace() 
                #need to ensure it doesn't get picked in a subsequent step
                if re.sub('_.*', '', currStim.name) in curr_loop_stims: curr_loop_stims.remove(re.sub('_.*', '', currStim.name))

                pdb.set_trace() 
                # Save the particular loop-trial config so we know what it was later on!
                tmp = logThisLoop(session,currStim,currentTrial,params)
            else:
                #remove the face incase we need to assign more trials 
                #need to ensure it doesn't get picked in a subsequent step
                if re.sub('_.*', '', currStim.name) in curr_loop_stims: curr_loop_stims.remove(re.sub('_.*', '', currStim.name))

            print('currentTrial')
            print(itrial)
            print(currentTrial.name)
            print(currStim.name)
        
    pdb.set_trace()    
    curr_loop_stims = uloop_stim_names #need to remove faces once's we've assigned one
    triallAttrIDsRun2 = params['encoding_trials_21-40']
    for itrial in range(0,len(triallAttrIDsRun2)):
        currentTrial = Attribute.objects.get(id=triallAttrIDsRun2[itrial])

        # Check to see if we already assigned a bio for this trial 
        currStim = doesThisTrialExist(subject,currentTrial)
        if not currStim:
            curr_stims_x_pres = [] #tally number of times face was assigned to this trial
            print(f'Creating and loggin a new bio')
            currentOldTrial = Attribute.objects.get(id=str(triallAttrIDsRun1[itrial]))
            #grab all names of all stims presented on this trial (includes)
            thisTrialPrevFaces = AttributeXAttribute.objects.filter(parent=currentOldTrial,mapping_name__in=prev_sess,child__attribute_class='relation_name').values_list('mapping_value_text',flat=True)
            for iface in range(0,len(curr_loop_stims)):
                if curr_loop_stims[iface].name in thisTrialPrevFaces:
                    #if the current face is in this Q, count the number of times
                    curr_stims_x_pres.append([*thisTrialPrevFaces].count(curr_loop_stims[iface].name))
                else:
                    #it hasn't been presented on this trial yet, so add 0
                    curr_stims_x_pres.append(0)

            #this is idx from curr_stims_x_pres of the stims presented least often
            min_n_pres_idxs = [i for i, x in enumerate(curr_stims_x_pres) if x == min(curr_stims_x_pres)]

            #grab the orig bio trial (bio doesn't get modified) so we can exclude this face from this trial
            tmpBioDic, currBio = doesThisBioExist(subject,currentOldTrial,params)

            remove_face_idxs = [i for i, x in enumerate(curr_loop_stims.values_list('name',flat=True)) if x == tmpBioDic['picture'].name]
            
            #import pdb; pdb.set_trace()
            #remove the prev. face idx from the possibilities 
            try:
                final_face_idxs = min_n_pres_idxs.remove(remove_face_idxs)
            except:
                final_face_idxs = min_n_pres_idxs

            #randomly select the face, 
            choose_this_face_idx = final_face_idxs[random.randrange(0,len(final_face_idxs))]
            curr_face = curr_loop_stims[choose_this_face_idx]

            #need to ensure it doesn't get picked in a subsequent step
            curr_loop_stims = curr_loop_stims.exclude(name=curr_loop_stims[choose_this_face_idx].name)

            #now grab the bio already created for this face and assign it to the current trial
            oldTrialThisFace = AttributeXAttribute.objects.filter(mapping_name=subject.subject_id,mapping_value_text=curr_face.name,child__attribute_class='relation_name')
            currBioDic, currBio = doesThisBioExist(subject,oldTrialThisFace[0].parent,params)

            #import pdb; pdb.set_trace()
            # Save the particular bio config so we know what it was later on!
            tmp = logThisBio(subject,currBioDic,currentTrial,params)
        else:
            #remove the face incase we need to assign more trials 
            #need to ensure it doesn't get picked in a subsequent step
            curr_loop_stims = curr_loop_stims.exclude(name=currBioDic['picture'].name)

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
def logThisLoop(session,currStim,currTrialAttribute,params):
    #enter each feature for a pic; parent attrb is the current trial type/number
    mappingName = str(session.id)
    mappingValText = currStim.name
    #grab the key attribute
    childattr =Attribute.objects.get(name='Key of '+re.sub('.*_', '', currStim.name))
    parentattr = currTrialAttribute
  
    print(f'creating entry for: ' +mappingName+' '+mappingValText+' '+childattr.name+' '+parentattr.name)     
    try:
        axa = AttributeXAttribute.objects.get_or_create(child=childattr, parent=parentattr,mapping_value_text = mappingValText, mapping_name=mappingName)
    except:
        print(f'failed to create attr X attr entry!')
        axa = ''

    return axa
    
# Return the loop_name if trial already exists in attr X attr table
def doesThisTrialExist(session,currTrialAttribute):
    currTrialEntry = AttributeXAttribute.objects.filter(parent=currTrialAttribute,mapping_name=str(session.id))
     
    try:
        currStim = Stimulus.objects.get(name = currTrialEntry[0].mapping_value_text)
    except:
        currStim = {}
    
    return currStim



