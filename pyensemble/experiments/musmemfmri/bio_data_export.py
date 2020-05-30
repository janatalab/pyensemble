# bio_data_export.py.py
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

whichExperiment = 'musmemfmri_bio_pilot'
startDate = '' #grab subjects after this date
endDate = '' #grab subjects before this date

# Get our parameters
study_params = bio_params() 
params = study_params[whichExperiment]


halfWayForm = study_params['halfWayForm']

endForm = study_params['endForm']



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



