# select.py

from django.conf import settings
from pyensemble.models import Stimulus

import os, random
import pdb

def select_audio(request,*args,**kwargs):
    name = kwargs.get('name',None)
    playlist = kwargs.get('playlist',None)
    use_jspsych = kwargs.get('use_jspsych', True)

    stimulus = None
    timeline = []

    # Fetch the stimulus object if we are giving a name
    if name:
        stimulus = Stimulus.objects.get(name=name)

    # Select a stimulus at random from a playlist if specified
    if not stimulus and playlist:
        stimuli = Stimulus.objects.filter(playlist=playlist, file_format='.mp3')

        # Select one at random
        if stimuli.count():
            stimidx = random.randrange(0,stimuli.count())
            stimulus = stimuli[stimidx]


    if stimulus and use_jspsych:
        if settings.USE_AWS_STORAGE:
            stimulus_url = stimulus.location.url
        else:
            stimulus_url = os.path.join(settings.MEDIA_URL, stimulus.location.url)

        trial = {
            'type': 'audio-keyboard-response',
            'stimulus': stimulus_url,
            'choices': 'none',
            'click_to_start': True,
            'trial_ends_after_audio': True,
            'trial_duration': 3000,
        }

        if trial['click_to_start']:
            trial['prompt'] = '<a id="start_button" class="btn btn-primary" role="button"  href="#">Start sound</a>'

        timeline.append(trial)

    stimulus_id = None
    if stimulus:
        stimulus_id = stimulus.id

    return timeline, stimulus_id