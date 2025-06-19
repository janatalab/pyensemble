# Quality control functions for PyEnsemble

def default_session_qc_check(session, *args, **kwargs):
    # Run any quality control checks
    passed_qc = True

    # Add checks here, e.g. make sure that the participant made it through the entire experiment, 
    # as opposed to exiting early or abandoning the experiment.
    if not session.last_form_responded():
        passed_qc = False
    
    return passed_qc
