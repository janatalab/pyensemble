# study.py

from django.conf import settings

from pyensemble.models import Attribute, Study, Experiment, ExperimentXAttribute, StudyXExperiment

import logging

'''
Group experiments into studies.

The studies parameter expects a dictionary in which each key corresponds 
to a study title. The key's value is a list of experiment titles for the study.
'''
def create_experiment_groupings(studies={}):

    for study, experiments in studies.items():
        msg = f"\nCreating experiment groupings for study titled: {study}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        # Get an attribute for the study
        grouping_attribute, created = Attribute.objects.get_or_create(name=study, attribute_class='study')

        # Create an entry in the Study table
        study_obj, created = Study.objects.get_or_create(title=study)

        if created:
            status = "Created"
        else:
            status = "Fetched"
        msg = f"{status} study: {study}"
        if settings.DEBUG:
            print(msg)
        else:
            logging.info(msg)

        # Loop over the experiments
        for idx, title in enumerate(experiments, start=1):
            # Get the experiment object
            experiment, created = Experiment.objects.get_or_create(title=title)

            if created:
                status = "Created"
            else:
                status = "Fetched"

            msg = f"{status} experiment: {title}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.info(msg)

            # Create the annotation
            exa, created = ExperimentXAttribute.objects.get_or_create(
                experiment = experiment,
                attribute = grouping_attribute
                )

            if created:
                status = "Created"
            else:
                status = "Found"
            msg = f"{status} link between {experiment.title} and attribute: {grouping_attribute.name}"
            if settings.DEBUG:
                print(msg)
            else:
                logging.info(msg)

            # Create and entry in the StudyXExperiment table
            sxe, created = StudyXExperiment.objects.get_or_create(study=study_obj, experiment=experiment, experiment_order=idx)
