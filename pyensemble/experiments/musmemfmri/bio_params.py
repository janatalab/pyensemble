# bio_params.py
# global parameters for all of the musmemfmri bio pilot experiments 
#### make sure the name of each dictionary matches the name of the experiment in pyensemble! 
#that's how it pics the right ones...

def bio_params():
    study_params = {
        #params for the first bio pilot study
        'musmemfmri_bio_pilot': {
            'experiment_id': 1,
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
        },
        'musmemfmri_bio_pilotV2': {
            'experiment_id': '???',
            'ignore_subs': ['',''],
            'breakAfterTheseTrials': ['','',''],
            'practice_face_stim_ids': [840, 841]
        }
    }

    return study_params




