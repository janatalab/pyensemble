# musmemfmri_face_pilot.py

from pyensemble.models import Experiment, AttributeXAttribute

def select():
    # Get uptodate distribution of stimulus properties
    pass


def already_presented():
    # # Look up the response table
    # expt = Experiment.objects.get(experiment_id=experiment_id)

    # resptable_name = expt.response_table

    # Look up the already presented trials
    AttributeXAttribute.filter()
