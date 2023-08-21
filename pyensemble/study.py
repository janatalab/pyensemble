# study.py


from pyensemble.models import Attribute, Study, Experiment, ExperimentXAttribute, StudyXExperiment

'''
Group experiments into studies.

The studies parameter expects a dictionary in which each key corresponds 
to a study title. The key's value is a list of experiment titles for the study.
'''
def create_experiment_groupings(studies={}):
    for study, experiments in studies.items():
        # Get an attribute for the study
        grouping_attribute, created = Attribute.objects.get_or_create(name=study, attribute_class='study')

        # Create an entry in the Study table
        study_obj, created = Study.objects.get_or_create(title=study)

        # Loop over the experiments
        for idx, title in enumerate(experiments, start=1):
            # Get the experiment object
            print(f"Fetching experiment: {title}")
            experiment = Experiment.objects.get(title=title)

            # Create the annotation
            exa, created = ExperimentXAttribute.objects.get_or_create(
                experiment = experiment,
                attribute = grouping_attribute
                )

            print(f"Linked {experiment.title} with attribute: {grouping_attribute.name}")

            # Create and entry in the StudyXExperiment table
            sxe, created = StudyXExperiment.objects.get_or_create(study=study_obj, experiment=experiment, experiment_order=idx)
