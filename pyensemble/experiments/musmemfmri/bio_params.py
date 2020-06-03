# bio_params.py
# global parameters for all of the musmemfmri bio pilot experiments 
#### make sure the name of each dictionary matches the name of the experiment in pyensemble! 
#that's how it pics the right ones...

def bio_params():
    study_params = {
        #params for the first bio pilot study
        'musmemfmri_bio_pilot': {
            'experiment_id': 1,
            'ignore_subs': ['01mtt01011','01mtt89011','01ttf67012','04ttt89211','04ktb89211','01mtt89012','01ttt89011',
                            '01ttt89011','02weh90191','01mtt90011','01mtt91011','01ttt69011'],#'
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
                    'I enjoy [insert_hobby] in my spare time with my [insert_relation] [insert_relation_name].'],
            'form_names': ['post_bio_q2_face_name','post_bio_q2_location','post_bio_q2_job',
                    'post_bio_q2_hobby','post_bio_q2_relation','post_bio_q2_relation_name'],
            'data_dump_path': '/home/bmk/musmemfmri/bio_pilot_data',
            'alt_feature_answers': {'grandmother':'grandma','mom':'mother','dad':'father','grandfather':'grandpa'}
        },
        #this exp same as above, except feedback is given after each face-bio exposure trial 
        'musmemfmri_bio_pilotV2': {
            'experiment_id': '???',
            'ignore_subs': ['',''],
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
                    'I enjoy [insert_hobby] in my spare time with my [insert_relation] [insert_relation_name].'],
            'form_names': ['post_bio_q2_face_name','post_bio_q2_location','post_bio_q2_job',
                    'post_bio_q2_hobby','post_bio_q2_relation','post_bio_q2_relation_name'],
            'data_dump_path': '/home/bmk/musmemfmri/bio_pilotV2_data',
            'alt_feature_answers': {'grandmother':'grandma','mom':'mother','dad':'father','grandfather':'grandpa'}
        }
    }

    return study_params




