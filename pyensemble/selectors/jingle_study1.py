# jingle_study1.py

import os, random

from django.conf import settings
from pyensemble.models import Stimulus, StimulusXAttribute, AttributeXAttribute

import pdb

def select(request,*args,**kwargs):
    # Construct a jsPsych timeline
    # https://www.jspsych.org/overview/timeline/
    timeline = []

    # Select the stimulus
    jingles = Stimulus.objects.filter(attributes__name='jingle')

    randidx = random.randrange(jingles.count())
    stimulus = jingles[randidx]

    # Specify the trial based on the jsPsych definition
    trial = {
        'type': 'audio-keyboard-response',
        'stimulus': os.path.join(settings.MEDIA_URL,stimulus.location.url),
        'choices': 'none',
        'trial_ends_after_audio': True,
    }

    # Push the trial to the timeline
    timeline.append(trial)

    # pdb.set_trace()

    return timeline, stimulus.stimulus_id
