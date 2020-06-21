# musmemfmri_loop.py
from . import loop_params as lp #for some reason this needs "from . " in the _bio??from . 

import pdb
import os, csv, re
import random
import json

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

def import_practice_stims(stimin):
    #imports the loops for practicing tasks that i forgot to include...
    #stimin='/var/www/html/ensemble/stimuli/musmemfmristims/practice_loops/' 
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimin) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)
    print(mediadirs)
    for media_type in mediadirs:
        if media_type == 'practice_loops':
            # Get an attribute corresponding to this media type
            attribute, ehn = Attribute.objects.get_or_create(name='Media Type', attribute_class='stimulus')
            attribute2, ehn = Attribute.objects.get_or_create(name='practice_loop', attribute_class='stimulus')

            #import pdb; pdb.set_trace()
            print(f'Working on {media_type}s ...')

            # Loop over files in the directory
            with os.scandir(os.path.join(stimin,media_type)) as stimlist:
                for stim in stimlist:
                    if not stim.name.startswith('.') and stim.is_file():
                        print(f'\tImporting {stim.name}')

                        # Strip off the extension
                        fstub,fext = os.path.splitext(stim.name)
                        pdb.set_trace()
                        # Create the stimulus object
                        stimulus, _ = Stimulus.objects.get_or_create(
                            name=fstub,
                            playlist='Musmem practice',
                            file_format=fext,
                            location=os.path.join(rootdir,media_type,stim.name)
                            )

                        # Create a stimulusXattribute entry
                        #pdb.set_trace()
                        stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=media_type)
                        stimXattrib2, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute2, attribute_value_text=media_type)

                       

    return print('pyensemble/message.html',{'msg':'Successfully imported the stimuli'})

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

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

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
    The stim to trial mapping for run 1 is CB’d across subjects. The stim to trial mapping for 
    subsequent runs are CB’d within a subject such that 1) same loop isn’t presented on the same 
    trial position in a run (e.g., not the 1st stim in two runs) and 2) loops never follow the 
    same loops more than once. 

    The problem is, in the later runs there is a small chance that we run out of face options by 
    the last trial attribute wtihin a run (e.g., the 20th trial in a run). The way to get around 
    this would be to start the CBing for the run over until it works out correctly. 

    However, this means that I cannot write attr x attr entries trial by trial, and i instead need 
    a buffer of sorts to keep track of things. So, where we normally call ‘logThisLoop()’, we 
    instead need to store each trial - stim pair in a dictionary, then once everything checks out 
    (doesn’t error), we can log all the loops at once. 


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

    run_list = sorted(params['run_params'].keys()) #need to go through runs in order
    previous_runs = []
    for irun in run_list:
        #cache the assignments for a run in a dictionary, if it works out then submit,
        #otherwise start the run over. 
        currRunDict = {}
        runReady2go = False
        while not runReady2go: 
            FlagsOnRun = False #if this is true by end of run, buld run from begining again 
            if irun in 'run1_trials':
                curr_loop_stims = uloop_stim_names #need to remove faces once's we've assigned one

                #if this is an odd numbere participant, reverse the trial assignment order 
                if (len(prev_sess)%2 == 0):
                    useThisTrialRange = range(0,len(params['run_params'][irun])) #use regular order (not reversed)
                else:
                    useThisTrialRange = range(len(params['run_params'][irun])-1,-1,-1)
            else:
                useThisTrialRange = range(0,len(params['run_params'][irun])) #use regular order (not reversed)
                #grab all the stims present in the first run (limit subsequent run CB to this set)
                tmp_stims = AttributeXAttribute.objects.filter(parent__name__in=params['run_params']['run1_trials'],parent__attribute_class='loop_trials',mapping_name=str(session.id)).values_list('mapping_value_text',flat=True)
                r1_loop_stims = []
                for ist in tmp_stims:
                    #remove key info part of string
                    r1_loop_stims.append(re.sub('_.*', '', ist))
                curr_loop_stims = [*set(r1_loop_stims), ]

            previous_runs.append(irun)
            #pdb.set_trace()
            for itrial in useThisTrialRange:
                cantAdjust = False
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
                    """
                    Run1 is Cb'd across subject and run2+ CB'd off subs run1 (preventing position repeats and order repeats )
                    SO the CB counterbalancing question is if we random all 2+ runs across subjects, the 
                    added constraint of not repeating a trial in a location/position within sub may result 
                    in us running out of loops and error out...so why not just do it off of that sub run 1 
                    (we already make sure previous trial positions aren't repeated). 
                    """
                    if irun not in 'run1_trials':
                        #CB based on the run 1 assignments for this subject
                        thisTrialPrevLoops = AttributeXAttribute.objects.filter(parent=currentTrialPosition,mapping_name__in=[str(session.id)],mapping_value_text__iregex=r'^%s_'%(curr_loop_stims)).values_list('mapping_value_text',flat=True)

                    else:
                        #CB based on the run 1 assignments across subjects
                        thisTrialPrevLoops = AttributeXAttribute.objects.filter(parent=currentTrial,mapping_name__in=prev_sess,mapping_value_text__iregex=r'^%s_'%(curr_loop_stims)).values_list('mapping_value_text',flat=True)

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
                        tmptrials2check = [*range(itrial+1,20*(len(previous_runs)-1),20),]
                        trials2check = ['trial'+format(x, '02d') for x in tmptrials2check]

                        prevLoopsThisPosition = AttributeXAttribute.objects.filter(parent__name__in=trials2check,parent__attribute_class='loop_trials',mapping_name__in=[str(session.id)]).values_list('mapping_value_text',flat=True)
                        #strip of key info
                        strpdprevLoopsThisPosition = []
                        for ist in prevLoopsThisPosition:
                            #remove key info part of string
                            strpdprevLoopsThisPosition.append(re.sub('_.*', '', ist))
                        remove_loop_idxs = [i for i, x in enumerate(curr_loop_stims) if x in strpdprevLoopsThisPosition]
                        #remove the prev. loop idx from the possibilities 
                        for itp in remove_loop_idxs:
                            if itp in min_loop_idxs: min_loop_idxs.remove(itp)

                        final_loop_idxs = min_loop_idxs

                        if len(final_loop_idxs)==0:
                            print(f'WARNING: ran out of possible loops!!!')
                            #pdb.set_trace()
                            FlagsOnRun = True
                            break
                        elif len(final_loop_idxs)==1:
                            print(f'WARNING: only 1 option left, cannot adjust for prev stim!!!')
                            #pdb.set_trace()
                            cantAdjust = True

                        #pdb.set_trace()
                        good2go = False
                        if itrial>0:
                            while not good2go:
                                #randomly select the loop, 
                                choose_this_loop_idx = final_loop_idxs[random.randrange(0,len(final_loop_idxs))]
                                currStimName = curr_loop_stims[choose_this_loop_idx]

                                #for this stim, get the past trials for this subject
                                thisLoopPrevTrial = AttributeXAttribute.objects.filter(mapping_name__in=[str(session.id)],mapping_value_text__iregex=r'^%s_'%(currStimName)).values_list('parent__name',flat=True).distinct()

                                #List 1: for this subject, increment each trial -1 and get the stimid of the loop
                                #presented before the current stim on previous trials. 
                                trials2check = []
                                for itp in thisLoopPrevTrial:
                                    tmpTrialNum = int(itp[-2:]) # grab the lst two char (numbers) in the attr. name
                                    tmpTrialNum = tmpTrialNum - 1 # increment them by 1 and put back into the string
                                    trials2check.append('trial'+'%02d'%(tmpTrialNum))
                                prevPrecedingLoops = AttributeXAttribute.objects.filter(parent__name__in=trials2check,parent__attribute_class='loop_trials',mapping_name=str(session.id)).values_list('mapping_value_text',flat=True)

                                #List 2: for this subject, get the last trial and get the stimid. 
                                tmpTrialNum = int(re.sub('^[a-zA-Z]*','',currentTrial.name))#int(currentTrial.name[-2:]) re.sub('^[a-zA-Z]*','',currentTrial.name)
                                tmpTrialNum = tmpTrialNum - 1
                                trial2check = 'trial'+'%02d'%(tmpTrialNum)
                                #pdb.set_trace()
                                currPrecedingLoop = currRunDict[trial2check]
                                #currPrecedingLoop = AttributeXAttribute.objects.filter(parent__name=trial2check,parent__attribute_class='loop_trials',mapping_name=str(session.id)).values_list('mapping_value_text',flat=True)

                                #pdb.set_trace()
                                #if list 2 stimid (only 1) is in List 1, then choose another current stimulus
                                #so that we don't reproduce the order within subject. 
                                if currPrecedingLoop in prevPrecedingLoops:
                                    if cantAdjust:
                                        #break out but flag the run
                                        FlagsOnRun = True
                                        good2go = True
                                    else:
                                        final_loop_idxs.remove(choose_this_loop_idx)
                                        good2go = False
                                else:
                                    good2go = True


                        else:
                            #first trial so just pick from what we've got
                            #randomly select the loop, 
                            choose_this_loop_idx = final_loop_idxs[random.randrange(0,len(final_loop_idxs))]
                            currStimName = curr_loop_stims[choose_this_loop_idx]

                        #now make sure we present this stim in the same key it was heard in run 1
                        thisLoopRun1 = AttributeXAttribute.objects.filter(mapping_name__in=[str(session.id)],mapping_value_text__iregex=r'^%s_'%(currStimName)).values_list('mapping_value_text',flat=True).distinct()
                        #grab the key info
                        currentKey = re.sub('.*_', '', thisLoopRun1[0])
                        currStim = Stimulus.objects.get(name = currStimName+'_'+currentKey)

                    else:
                        #1st run (only run we need to worry about picking keys)
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
                        if currRunDict:
                            #if we have prev trials this run
                            for ikey in params['loop_keys']:
                                #get vals within this sub
                                tmpqThisSub = 0
                                for ipk in [*currRunDict.values(),]:#how many these value sin ikey
                                    if re.match('.*_'+ikey,ipk):
                                        tmpqThisSub = tmpqThisSub + 1
                                #tmpqThisSub = AttributeXAttribute.objects.filter(parent__attribute_class='loop_trials',mapping_name=str(session.id),child__name='Key of '+ikey).values_list('mapping_value_text',flat=True)
                                if tmpqThisSub>=round(params['nUniqueLoops']/3):
                                    ignore_keys.append(currStimName+'_'+ikey)
                            if len(ignore_keys)==3:
                                #if we removed the all above, then pick one randomly
                                #because one class needs to have 6, the others 7
                                ignore_keys = [] #

                        #filter out the keys we are ignoring based on this subject
                        currStims = currStims.exclude(name__in=ignore_keys)

                        tmp_key_count_acrossSubs = []
                        # now get the counts for this stim-key across subject
                        for iloop in currStims:
                            #get vals across subs
                            tmpq = AttributeXAttribute.objects.filter(parent__attribute_class='loop_trials',mapping_name__in=prev_sess,mapping_value_text=iloop.name).values_list('mapping_value_text',flat=True).distinct()
                            tmp_key_count_acrossSubs.append(tmpq.count())

                        #do a check to see how many keys we've assigned to each one. if we have assign 
                        #get the min count idx
                        min_key_idxs = [i for i, x in enumerate(tmp_key_count_acrossSubs) if x == min(tmp_key_count_acrossSubs)]
                        choose_this_loop_idx = min_key_idxs[random.randrange(0,len(min_key_idxs))]
                        currStim = currStims[choose_this_loop_idx]

                    #need to ensure it doesn't get picked in a subsequent step
                    if re.sub('_.*', '', currStim.name) in curr_loop_stims: curr_loop_stims.remove(re.sub('_.*', '', currStim.name))
                    #pdb.set_trace()
                    # Save the particular loop-trial config so we know what it was later on!
                    currRunDict[currentTrial.name] = currStim.name
                    #tmp = logThisLoop(session,currStim,currentTrial,params)
                else:
                    #remove the face incase we need to assign more trials 
                    #need to ensure it doesn't get picked in a subsequent step
                    if re.sub('_.*', '', currStim.name) in curr_loop_stims: curr_loop_stims.remove(re.sub('_.*', '', currStim.name))

                #print('currentTrial')
                #print(itrial)
                #print(currentTrial.name)
                #print(currStim.name)

            if not FlagsOnRun:
                runReady2go = True
            else:
                #need to try the run over...
                runReady2go = False
                del previous_runs[-1]
                #THIS is the end of the giant run while loop 

        # log all of the loop-trial configs
        if currRunDict:
            print(f'logging run: '+irun)
            tmp = logThisRun(session,currRunDict,params)
            #otherwise it's already been logged 
            

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
    lastTrialAttribute = expsessinfo['currTrialName']

    # grab the lst two char (numbers) in the attr. name
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
    lastTrialAttribute = expsessinfo['currTrialName']
    
    #clear misc_info etc. 
    expsessinfo['misc_info'] = ''
    request.session.modified = True 

    #import pdb; pdb.set_trace()
    # if it's practice_trial, go ahead and present trial01
    if lastTrialAttribute in params['breakAfterTheseTrials']:
        #take a break! 
        time2rest = True
    else:
        time2rest = False

    return time2rest

def select_ftap_stim(request,*args,**kwargs):
    # script selects previoulsy assembled stim trials from attr x attr and presents
    # jspsych trial that records tapping responses (fixation cross)

    # Init jsPsych timeline
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
    trial = {
            'type':  'audio-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,thisStim.location.url),
            'choices': 'none',
            'click_to_start': True,
            'trial_ends_after_audio': True,
            'trial_duration': params['expo_trial_duration_ms']
        }
    if trial['click_to_start']:
        trial['prompt'] = '<a id="start_button" class="btn btn-primary" role="button"  href="#">Start sound</a>'
    
    #import pdb; pdb.set_trace()
    # Push the trial to the timeline
    timeline.append(trial)

    # NOTE THAT THIS DOESN"T RECORD A STIMULUS IN THE RESPONSE TABLE
    #but if we have the trial attributes assigned we can use those.
    addParams2Session(currBioDic,currTrialAttribute,request,session_id,params)

    #import pdb; pdb.set_trace()

    return(timeline, thisStim.id) 


"""
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
"""

"""
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
"""

def setUpLoopRecog(request,*args,**kwargs):
    #we want to create a list of stims to present (in order) and save it to the session var for this task
    #take all the loops they heard in run 1 and add 20 loops they didn't hear (the foils) (make sure order is randomized)

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # Grab stim - trial mappings for this subject
    triallAttrs = Attribute.objects.filter(name__in=params['run_params']['run1_trials'],attribute_class='loop_trials').values_list('name',flat=True)
    OurSubAxAentries = AttributeXAttribute.objects.filter(parent__name__in=triallAttrs,parent__attribute_class='loop_trials',mapping_name=str(session_id))
    target_names = OurSubAxAentries.values_list('mapping_value_text',flat=True)

    # get the unique names (minus key info at end), loop through each of these
    uTargStims = []
    sloop_stim_names = []
    for iloop in target_names:
        #remove key info part of string
        sloop_stim_names.append(re.sub('_.*', '', iloop))
    uTargStims = sorted([*set(sloop_stim_names), ])

    # Get stims this subject hasn't seen
    all_loops = Stimulus.objects.filter(stimulusxattribute__attribute_id__name=params['loop_attribute']).values_list('name',flat=True)
    
    # get the unique names (minus key info at end), loop through each of these
    uFoilStims = []
    sloop_stim_names = []
    for iloop in all_loops.values_list('name',flat=True):
        if re.sub('_.*', '', iloop) not in uTargStims:
            #add this foil
            sloop_stim_names.append(re.sub('_.*', '', iloop))
    uFoilStims = sorted([*set(sloop_stim_names), ])
    uFoilStims = random.sample(uFoilStims,20) #choose random subset of 20 foils (21 options total)


    # now assign keys for the foils (making sure an equal amount from each key are presented)
    #little diff then above approach. sort existing into 3rds and then append keys to each set.
    keyoptions = [item for sublist in [params['loop_keys']]*round(params['nUniqueLoops']/3) for item in sublist]
    random.shuffle(keyoptions)
    foil_names = []
    for ifoil in range(0,len(uFoilStims)):
        foil_names.append(uFoilStims[ifoil]+'_'+keyoptions[ifoil])
        #litt

    all_loop_names = [*target_names,]+foil_names

    trialDict = {}
    #{'trial01': { 
    #    'type': 'target',
    #    'loop':'Misc51_e'}
    #}    
    # While loop: make sure loop isn't preceded by a loop it followed during exposure
    #make sure we present no more than 3 targets in a row. 
    trialNames = params['run_params']['run1_trials']+params['run_params']['run2_trials']
    ready2go = False
    while not ready2go:
        targetCount = 0
        foilCount = 0
        random.shuffle(all_loop_names) # rand. order of all loops, 

        for itrial in range(0,len(all_loop_names)):
            trialReady = False
            while not trialReady:
                currStimName = all_loop_names[itrial]
                currTrial = trialNames[itrial]

                if currStimName in target_names:
                    targetCount = targetCount + 1
                    foilCount = 0
                else:
                    foilCount = foilCount + 1
                    targetCount = 0

                if not itrial==0:
                    #need to start checking for preceding stims in expo
                    #for this stim, get the past trials for this subject
                    thisLoopPrevTrial = AttributeXAttribute.objects.filter(mapping_name__in=[str(session.id)],mapping_value_text=currStimName).values_list('parent__name',flat=True).distinct()

                    if thisLoopPrevTrial:
                        #not a foil, there are prev trials
                        #List 1: for this subject, increment each trial -1 and get the stimid of the loop
                        #presented before the current stim on previous trials. 
                        trials2check = []
                        for itp in thisLoopPrevTrial:
                            tmpTrialNum = int(itp[-2:]) # grab the lst two char (numbers) in the attr. name
                            tmpTrialNum = tmpTrialNum - 1 # increment them by 1 and put back into the string
                            trials2check.append('trial'+'%02d'%(tmpTrialNum))
                        prevPrecedingLoops = AttributeXAttribute.objects.filter(parent__name__in=trials2check,parent__attribute_class='loop_trials',mapping_name=str(session.id)).values_list('mapping_value_text',flat=True)
                        
                        #List 2: for this subject, get the last trial and get the stimid. 
                        tmpTrialNum = int(re.sub('^[a-zA-Z]*','',currTrial))#int(currentTrial.name[-2:]) re.sub('^[a-zA-Z]*','',currentTrial.name)
                        tmpTrialNum = tmpTrialNum - 1
                        trial2check = 'trial'+'%02d'%(tmpTrialNum)
                        currPrecedingLoop = trialDict[trial2check]['loop']

                        #if list 2 stimid (only 1) is in List 1, then choose another current stimulus
                        #so that we don't reproduce the order within subject. 
                        noDup = False
                        if currPrecedingLoop in prevPrecedingLoops:
                            if itrial==len(trialNames)-1:
                                #last trial, have to start run over and try again
                                ready2go = False
                                noDup = False
                                print(f'Have to restart the run, preceding loop at end')
                            else:
                                noDup = False
                                print(f'Have to restart the trial, preceding loop duplicate')
                                tmpitem = all_loop_names.pop(itrial)
                                try:
                                    #if this fails, most likely last trial and no other loop to pick here
                                    #e.g., empty range for randrange() (39,39, 0)
                                    all_loop_names.insert(random.randrange(itrial+1,len(all_loop_names)),tmpitem)
                                except:
                                    pdb.set_trace()
                                    ready2go = False


                        else:
                            noDup = True
                    else:
                        noDup = True
                    if targetCount>3:
                        if itrial==len(trialNames)-1:
                            #last trial, have to start run over and try again
                            ready2go = False
                            print(f'Have to restart the run, too many targets at end')
                        else:
                            #too many targets in a row, change this assignment 
                            trialReady = False
                            print(f'Have to restart the trial, too many targets')
                            tmpitem = all_loop_names.pop(itrial)
                            all_loop_names.insert(random.randrange(itrial+1,len(all_loop_names)),tmpitem)
                    elif itrial==len(trialNames)-1:
                        trialReady = True
                        ready2go = True

                    elif noDup:
                        trialReady = True
                        
                else:
                    trialReady = True
                    
            if currStimName in foil_names:
                trialDict[currTrial] = {'type': 'foil','loop': currStimName}
            elif currStimName in target_names:
                trialDict[currTrial] = {'type': 'targ','loop': currStimName}
            
    #pdb.set_trace()
    # now log this trial dict in the session info to access later. 
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    expsessinfo['currTrialName'] = 'trial00'
    expsessinfo['recogTrialDic'] = json.dumps(trialDict)

    request.session.modified = True
    

    timeline = [{'nothing':'nothing'}] #pass dummy along

    return(timeline,'')

def select_recog_loop(request,*args,**kwargs):
    #we want to create a list of stims to present (in order) and save it to the session var for this task
    #take all the loops they heard in run 1 and add 20 loops they didn't hear (the foils) (make sure order is randomized)

    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    timeline = []

    pdb.set_trace()

    # Get the appropraite Trial attribute from the current session
    expsessinfo = request.session.get('experiment_%d'%(Session.objects.get(id=session_id).experiment.id))
    lastTrialAttribute = expsessinfo['currTrialName']

    expsessinfo['misc_info'] = 'NULL' #reset it for sanity 
    print(f'last trial: '+lastTrialAttribute)

    # grab the lst two char (numbers) in the attr. name
    tmpTrialNum = int(lastTrialAttribute[-2:])
    # increment them by 1 and put back into the string
    tmpTrialNum = tmpTrialNum + 1
    # grab the trial from the dict
    recogTrialDic = json.loads(expsessinfo['recogTrialDic'])

    currTrialInfo = recogTrialDic['trial%02d'%tmpTrialNum]

    print(f'this trial: '+currTrialInfo['type']+'; '+currTrialInfo['loop'])



    thisStim = Stimulus.objects.get(name=currTrialInfo['loop'])
    #
    # Now, set up the jsPsych trial (THIS INS"T WORKING)
    #
    #import pdb; pdb.set_trace()
    trial = {
            'type':  'audio-keyboard-response',
            'stimulus': os.path.join(settings.MEDIA_URL,thisStim.location.url),
            'choices': 'none',
            'click_to_start': True,
            'trial_ends_after_audio': True,
            'trial_duration': params['recog_trial_duration_ms']
        }
    if trial['click_to_start']:
        trial['prompt'] = '<a id="start_button" class="btn btn-primary" role="button"  href="#">Start sound</a>'
    #import pdb; pdb.set_trace()
    # Push the trial to the timeline
    timeline.append(trial)
    currTrialInfo['currTrial'] = 'trial%02d'%tmpTrialNum #add this info to misc_info
    #save out info to write to response table and add the new trial nuber 
    expsessinfo['misc_info'] = json.dumps(currTrialInfo)
    expsessinfo['currTrialName'] = 'trial%02d'%tmpTrialNum
    request.session.modified = True

    #import pdb; pdb.set_trace()

    return(timeline, thisStim.id) 

def IRMIsong1FollowUp(request,*args,**kwargs):
    #if they recognized the loop, as them about INMI
    #still want to ask even if it's a foil. nice to get the INMI FA rates
    #
    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # grab the last response
    hearBeforeResp = Response.objects.filter(session_id=session_id,question__text__contains='Have you heard this music excerpt before?').order_by('date_time') #- most recent is last?

    if hearBeforeResp.reverse()[0].response_enum==0:
        presentThisForm = True
    else:
        presentThisForm = False 

    return presentThisForm

def IRMIsong2FollowUp(request,*args,**kwargs):
    #if they reported INMI, follow up some more
    #
    # Extract our session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our parameters
    params = study_params[session.experiment.title]

    # Get our subject
    subject = session.subject

    # grab the last response
    hadINMIResp = Response.objects.filter(session_id=session_id,question__text__contains='Have you experienced this musical loop as involuntary repetitive musical imagery while participating in the study today?').order_by('date_time') #- most recent is last?

    # grab the last response
    hearBeforeResp = Response.objects.filter(session_id=session_id,question__text__contains='Have you heard this music excerpt before?').order_by('date_time') #- most recent is last?


    if hadINMIResp.reverse()[0].response_enum>0 and hearBeforeResp.reverse()[0].response_enum==0:
        presentThisForm = True
    else:
        presentThisForm = False 

    return presentThisForm


def logThisRun(session,currRunDict,params):
    # Create our attribute X attribute entries for a specific bio
    #enter each trial-stim into attr x attr
    for itrial in currRunDict:
        mappingName = str(session.id)
        mappingValText = currRunDict[itrial]
        #grab the key attribute
        childattr =Attribute.objects.get(name='Key of '+re.sub('.*_', '', currRunDict[itrial]))
        parentattr = Attribute.objects.get(name=itrial,attribute_class='loop_trials')
      
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



