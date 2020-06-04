# loop_params.py
# global parameters for all of the musmemfmri loop pilot experiments 
#### make sure the name of each dictionary matches the name of the experiment in pyensemble! 
#that's how it pics the right ones...

def loop_params():
    study_params = {
        #params for the first bio pilot study
        'musmemfmri_loop_pilot': {
            'experiment_id': 0,
            'ignore_subs': [''],#
            'breakAfterTheseTrials': ['trial10','trial20','trial30'],
            'loop_stim_ids': [range(820,820+20)],
            'encoding_bio_duration_ms': 16000,#16000
            'encoding_bio_feedback_duration_ms': 8000,
            'encoding_1back_question_duration_ms': 8000,
            'encoding_rest_duration_ms': 10000,
            'encoding_trials_1-20': range(146,146+20),
            'encoding_trials_21-40': range(166,166+20),
            'form_names': ['post_bio_q2_face_name','post_bio_q2_location','post_bio_q2_job',
                    'post_bio_q2_hobby','post_bio_q2_relation','post_bio_q2_relation_name'],
            'data_dump_path': '/home/bmk/musmemfmri/loop_pilot_data',
        },
        #this exp same as above, except feedback is given after each face-bio exposure trial 
        'musmemfmri_loop_pilotV2': {
            'experiment_id': '???',
            'ignore_subs': ['',''],
            'breakAfterTheseTrials': ['trial10','trial20','trial30'],
            
        }
    }

    return study_params




