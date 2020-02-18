# jingle_study_stims.py
#
# Imports stimuli for Angela Nazarian's jingle study
import os

from django.conf import settings

from pyensemble.models import Attribute, Stimulus, StimulusXAttribute

# Specify the stimulus directory relative to the stimulus root
rootdir = 'jinglestims'
stimdir = os.path.join(settings.MEDIA_ROOT, rootdir)

def import_stims(stimdir=stimdir):
    # Determine the number of subdirectories, corresponding to media types
    mediadirs = []

    with os.scandir(stimdir) as dirlist:
        for entry in dirlist:
            if not entry.name.startswith('.') and entry.is_dir():
                mediadirs.append(entry.name)

    for media_type in mediadirs:
        # Get an attribute corresponding to this media type
        attribute, _ = Attribute.objects.get_or_create(name=media_type,class_field='stimulus')

        print(f'Working on {media_type}s ...')

        # Loop over files in the directory
        with os.scandir(os.path.join(stimdir,media_type)) as stimlist:
            for stim in stimlist:
                if not stim.name.startswith('.') and stim.is_file():
                    print(f'\tImporting {stim.name}')

                    # Strip off the extension
                    fstub,fext = os.path.splitext(stim.name)

                    # Create the stimulus object
                    stimulus, _ = Stimulus.objects.get_or_create(
                        name=fstub,
                        playlist='Jingle Study',
                        file_format=fext,
                        location=os.path.join(rootdir,media_type,stim.name)
                        )

                    # Create a stimulusXattribute entry
                    stimXattrib, _ = StimulusXAttribute.objects.get_or_create(stimulus_id=stimulus, attribute_id=attribute)
