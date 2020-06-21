# loop_params.py
# global parameters for all of the musmemfmri loop pilot experiments 
#### make sure the name of each dictionary matches the name of the experiment in pyensemble! 
#that's how it pics the right ones...

def loop_params():
    nuLoops = 20 #number of unique loops to include in the study. present each loop 1 time(line) per run. 
    study_params = {
        #params for the first bio pilot study
        'musmemfmri_loop_pilot': {
            'experiment_id': 6,
            'ignore_subs': ['01mtt90011'],#
            'breakAfterTheseTrials': ['trial10','trial20','trial30'],
            'prac_loop_stim_id': 99999,
            'loop_attribute': 'loopsV1',
            'nUniqueLoops': nuLoops,
            'loop_keys': ['C','E','Ab'],
            'run_params': {'run1_trials': [str('trial%02d'%i) for i in range(1,1+nuLoops)],
                            'run2_trials': [str('trial%02d'%i) for i in range((nuLoops*1)+1,21+nuLoops)],#_21-40
                            'run3_trials': [str('trial%02d'%i) for i in range((nuLoops*2)+1,41+nuLoops)],#_41-60
                            'run4_trials': [str('trial%02d'%i) for i in range((nuLoops*3)+1,61+nuLoops)],#_61-80
                            'run5_trials': [str('trial%02d'%i) for i in range((nuLoops*4)+1,81+nuLoops)],#_81-100
                            'run6_trials': [str('trial%02d'%i) for i in range((nuLoops*5)+1,101+nuLoops)]#_101-120
                            },
            'loop_trial_duration_ms': 16000,#3200=4 loop reps
            'encoding_rest_duration_ms': 10000,
            
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




