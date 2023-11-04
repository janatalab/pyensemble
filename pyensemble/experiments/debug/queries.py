# queries.py

# Import models that we want to examine
from pyensemble.models import Experiment, Response, Session

import pandas as pd

def example_queries():
	# Generate a QuerySet containing all of the experiments
	experiments = Experiment.objects.all()

	# Search for all of the experiments whose titles contain a specific string
	search_str = 'Test'

	experiments.filter(title__contains=search_str) # case-sensitive
	experiments.filter(title__icontains=search_str) # case-insensitive

	# To exclude experiments containing a particular string
	experiments.exclude(title__contains=search_str)

	'''
	To get the sessions associated with a particular experiment, 
	we can fetch them in a couple of different ways.
	'''

	# Via the Session model
	sessions = Session.objects.filter(experiment__title__contains=search_str) 

	# Via the Experiment object
	experiment = Experiment.objects.get(title='Debug Group Experiment')
	sessions_via_experiment = experiment.session_set.all()

	# Set up exporting of response data from a specific experiment, 
	# using sessions that have not been excluded. Do this via the Response table.
	responses = Response.objects.filter(experiment__title='Debug Group Experiment').exclude(session__exclude=True)

	# Extract the values
	response_values = responses.values()

	# Convert it to a Pandas dataframe
	df = pd.DataFrame(response_values)

	# Write the dataframe to a csv file
	df.to_csv('test.csv')

	# Extract a more informative list of values
	better_values = responses.values(
		'subject_id',
		'session__start_datetime',
		'form__name',
		'question__text',
		'response_text',
		'response_enum',
		'jspsych_data',
		)

	return {'experiment': experiments, 'sessions': sessions, 'responses': responses}
