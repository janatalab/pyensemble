# musmemfmri.py
import pdb
import os, csv

from django.conf import settings

from pyensemble.models import Stimulus, Experiment, Attribute, AttributeXAttribute, StimulusXAttribute

# Ultimately, this should inherit a base ExperimentDefinition class that implements basic import and select methods
# class JingleStudy(object):

# Specify the stimulus directory relative to the stimulus root
rootdir = 'musmemfmristims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

# Imports stimuli for Angela Nazarian's jingle study
#@login_required
def import_stims(stimin):#removed request arg. stimdir=stimdir
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimin) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)
    print(mediadirs)
    for media_type in mediadirs:
        # Get an attribute corresponding to this media type
        attribute, _ = Attribute.objects.get_or_create(name='Media Type', attribute_class='stimulus')
        
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
                    stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus=stimulus, attribute=attribute, attribute_value_text=media_type)

    return print('pyensemble/message.html',{'msg':'Successfully imported the stimuli'})
    #return render(request,'pyensemble/message.html',{'msg':'Successfully imported the stimuli'})

def import_attributes(stimin):
    #'/home/bmk/stims2upload/musmemfmri_attribute_uploadsV2..csv'
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
    #'/home/bmk/stims2upload/musmemfmri_stimXattribute_uploads.csv'

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
            sxa, created = StimulusXAttribute.objects.get_or_create(stimulus=thisstim, attribute=thisattr, attribute_value_text=value_text, attribute_value_double=value_float)

    return print('pyensemble/message.html',{'msg':'Successfully imported the stim X attribute file'})

def import_attributesXattribute(stimin):
    #'/home/bmk/stims2upload/musmemfmri_stat_attributes.csv'

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
            import pdb; pdb.set_trace()

def select():
    # Get uptodate distribution of stimulus properties
    pass


def already_presented():
    # # Look up the response table
    # expt = Experiment.objects.get(experiment_id=experiment_id)

    # resptable_name = expt.response_table

    # Look up the already presented trials
    AttributeXAttribute.filter()
