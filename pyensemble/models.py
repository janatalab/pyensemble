# models.py
#
# Specifies the core Ensemble models
#

from django.db import models
from django.urls import reverse

from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField, EncryptedDateField

from django.utils import timezone
from pyensemble.utils.parsers import parse_function_spec

import pdb

#
# Base class tables
#
class Attribute(models.Model):
    attribute_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    attribute_class = models.CharField(db_column='class', max_length=15)  # Field renamed because it was a Python reserved word.

class DataFormat(models.Model):
    data_format_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=15)
    enum_values = models.TextField(blank=True)

class Question(models.Model):
    question_id = models.IntegerField(primary_key=True)
    question_text = models.TextField(blank=True)
    question_category = models.CharField(max_length=19, blank=True)
    heading_format = models.CharField(max_length=14)
    locked = models.CharField(max_length=1)

    forms = models.ManyToManyField('Form', through='FormXQuestion')

    values = models.ManyToManyField('DataFormat', through='QuestionXDataFormat')

    def __unicode__(self):
        return self.question_text

    def choices(self):
        return [(val,lbl) for val,lbl in enumerate(self.values().replace('"','').split(','))]

class Form(models.Model):
    form_id = models.IntegerField(primary_key=True)
    form_name = models.CharField(unique=True, max_length=50)
    form_category = models.CharField(max_length=19, blank=True)
    header = models.TextField(blank=True)
    footer = models.TextField(blank=True)
    header_audio_path = models.CharField(max_length=50, blank=True)
    footer_audio_path = models.CharField(max_length=50, blank=True)
    version = models.FloatField(blank=True, null=True)
    locked = models.CharField(max_length=1)
    visit_once = models.CharField(max_length=1)

    questions = models.ManyToManyField('Question', through='FormXQuestion')
    experiments = models.ManyToManyField('Experiment', through='ExperimentXForm')

class Experiment(models.Model):
    experiment_id = models.IntegerField(primary_key=True)
    start_date = models.DateField(blank=True, null=True)
    experiment_title = models.CharField(unique=True, max_length=50)
    experiment_description = models.TextField(blank=True)
    response_table = models.CharField(max_length=50)
    irb_id = models.CharField(max_length=30, blank=True)
    end_date = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=30)
    play_question_audio = models.CharField(max_length=1)
    encrypted_response_table = models.CharField(max_length=1)
    params = models.TextField()
    locked = models.CharField(max_length=1)

    forms = models.ManyToManyField('Form', through='ExperimentXForm')

class Response(models.Model):
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE)
    session = models.ForeignKey('Session', db_column='session_id', db_constraint=True, on_delete=models.CASCADE)
    form = models.ForeignKey('Form', db_column='form_id', db_constraint=True, on_delete=models.CASCADE)
    form_order = models.PositiveSmallIntegerField(null=False,default=0)

    stimulus = models.ForeignKey('Stimulus', db_column='stimulus_id', db_constraint=True, on_delete=models.CASCADE)

    # Question X DataFormat
    qdf = models.ForeignKey('QuestionXDataFormat', db_constraint=True, on_delete=models.CASCADE)
    form_question_num = models.PositiveSmallIntegerField(null=False,default=0)
    question_iteration = models.PositiveSmallIntegerField(null=False,default=0)

    date_time = models.DateTimeField(auto_now_add=True)
    response_order = models.PositiveSmallIntegerField(null=False,default=0)
    response_text = models.TextField(blank=True)
    response_enum = models.PositiveIntegerField(blank=True, null=True)
    decline = models.BooleanField(default=False)
    misc_info = models.TextField(blank=True)
    

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    date_time = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    ticket = models.ForeignKey('Ticket', db_column='ticket_id', db_constraint=True, on_delete=models.CASCADE, related_name='+')
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE,null=True)
    php_session_id = models.CharField(max_length=70, blank=True)

class Stimulus(models.Model):
    stimulus_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=30)
    playlist = models.CharField(max_length=50, blank=True)
    artist = models.CharField(max_length=200, blank=True)
    album = models.TextField(blank=True)
    genre = models.TextField(blank=True)
    file_format = models.CharField(max_length=6, blank=True)
    size = models.IntegerField(blank=True, null=True)
    duration = models.TimeField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)  
    compression_bit_rate = models.IntegerField(blank=True, null=True)
    sample_rate = models.IntegerField(blank=True, null=True)
    sample_size = models.IntegerField(blank=True, null=True)
    channels = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    location = models.FileField()

    attributes = models.ManyToManyField('Attribute', through='StimulusXAttribute')

    class Meta:
        unique_together = (("name", "location"),)

class Subject(models.Model):
    SEX_OPTIONS = [
        ('F','Female'),
        ('M','Male'),
        ('UN','Undeclared')
    ]

    ETHNICITY_OPTIONS = [
        ('HL','Hispanic or Latino'),
        ('NHL','Not Hispanic or Latino'),
        ('UN','Undeclared')
    ]

    RACE_OPTIONS = [
        ('AIAN','American Indian or Alaska Native'),
        ('A','Asian'),
        ('B','Black or African American'),
        ('NHPI','Native Hawaiian or Other Pacific Islander'),
        ('W','White'),
        ('UN','Undeclared')
    ]

    subject_id = models.CharField(primary_key=True, max_length=10)
    date_entered = models.DateField(auto_now_add=True)
    name_last = EncryptedCharField(max_length=24)
    name_first = EncryptedCharField(max_length=24)
    name_middle = EncryptedCharField(max_length=24)
    name_suffix = EncryptedCharField(max_length=24)
    passphrase = EncryptedCharField(max_length=64)
    security_questions = models.TextField()
    security_responses = EncryptedTextField(max_length=128)
    email = EncryptedEmailField(max_length=24)
    phone1 = EncryptedCharField(max_length=16)
    phone2 = EncryptedCharField(max_length=16)
    address1 = EncryptedCharField(max_length=24)
    address2 = EncryptedCharField(max_length=24)
    address3 = EncryptedCharField(max_length=24)
    city = EncryptedCharField(max_length=24)
    county = EncryptedCharField(max_length=24)
    state = EncryptedCharField(max_length=24)
    postal_code = EncryptedCharField(max_length=10)
    sex = models.CharField(max_length=2,
        choices=SEX_OPTIONS,
        default='UN',
        )
    ethnicity = models.CharField(
        max_length=4,
        choices=ETHNICITY_OPTIONS,
        default='UN',
        )
    race = models.CharField(
        max_length=2,
        choices=RACE_OPTIONS,
        default='UN',
        )
    dob = EncryptedDateField()
    notes = models.TextField()


class Ticket(models.Model):
    TICKET_TYPE_CHOICES=[
        ('master','Master'),
        ('user','User'),
    ]

    ticket_id = models.AutoField(primary_key=True)
    ticket_code = models.CharField(max_length=32)
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=6,
        choices=TICKET_TYPE_CHOICES,
        default='master',
        )
    used = models.BooleanField(default=False)
    expiration_datetime = models.DateTimeField(blank=True, null=True)
    # session = models.ForeignKey('Session',db_column='session_id',on_delete=models.CASCADE,null=True)
    assigned = models.BooleanField(default=False)

    @property
    def expired(self):
        if (self.used and self.type == 'user') or (self.expiration_datetime and self.expiration_datetime < timezone.now()):
            self._expired=True
        else:
            self._expired=False

        return self._expired
    


#
# Linking tables
#

class AttributeXAttribute(models.Model):
    attribute_id_child = models.IntegerField()
    attribute_id_parent = models.IntegerField()
    mapping_name = models.CharField(max_length=128)
    mapping_value_double = models.FloatField(blank=True, null=True)

    class Meta:
        unique_together = (("attribute_id_child", "attribute_id_parent", "mapping_name", "mapping_value_double"),)


class StimulusXAttribute(models.Model):
    # id = models.IntegerField(primary_key=True) # Not present in original ensemble db
    stimulus_id = models.ForeignKey('Stimulus', db_column='stimulus_id', db_constraint=True, on_delete=models.CASCADE)
    attribute_id = models.ForeignKey('Attribute', db_column='attribute_id', db_constraint=True, on_delete=models.CASCADE)
    attribute_value_double = models.FloatField(blank=True, null=True)
    attribute_value_text = models.TextField(blank=True)

    class Meta:
        unique_together = (("stimulus_id", "attribute_id"),)

class ExperimentXStimulus(models.Model):
    # id = models.IntegerField(primary_key=True) # Not present in original ensemble db
    experiment_id = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    stimulus_id = models.ForeignKey('Stimulus', db_column='stimulus_id', db_constraint=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("experiment_id", "stimulus_id"),)

class QuestionXDataFormat(models.Model):
    qdf_id = models.IntegerField(primary_key=True)
    question = models.ForeignKey('Question', db_column='question_id', db_constraint=True, on_delete=models.CASCADE)
    subquestion = models.IntegerField()
    answer_format = models.ForeignKey('DataFormat', db_column='answer_format_id', db_constraint=True, on_delete=models.CASCADE)

    heading = models.TextField(blank=True)
    range = models.CharField(max_length=30, blank=True)
    default = models.CharField(max_length=30, blank=True)
    html_field_type = models.CharField(max_length=10, blank=True)
    audio_path = models.CharField(max_length=50, blank=True)
    required = models.BooleanField(default=True)

    class Meta:
        unique_together = (("question", "subquestion", "answer_format"),)

class FormXQuestion(models.Model):
    #id = models.IntegerField(primary_key=True) # Not present in original ensemble db
    form = models.ForeignKey('Form', db_column='form_id', db_constraint=True, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', db_column='question_id', db_constraint=True, on_delete=models.CASCADE)
    question_iteration = models.IntegerField()
    form_question_num = models.IntegerField()

    class Meta:
        unique_together = (("form","question","form_question_num","question_iteration"),)


class ExperimentXForm(models.Model):
    #id = models.IntegerField(primary_key=True) # Not present in original ensemble db
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    form = models.ForeignKey('Form', db_column='form_id', db_constraint=True, on_delete=models.CASCADE)
    form_order = models.IntegerField()
    form_handler = models.CharField(max_length=50, blank=True)
    goto = models.IntegerField(blank=True, null=True)
    repeat = models.IntegerField(blank=True, null=True)
    condition = models.TextField(blank=True)
    condition_matlab = models.TextField(blank=True)
    stimulus_matlab = models.TextField(blank=True)
    break_loop_button = models.CharField(max_length=1)
    break_loop_button_text = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = (("experiment", "form", "form_order"),)

    #
    # Helper functions for taking form actions
    #

    def parse_condition_string(self, expsessinfo):
        # Returns a list of condition dictionaries
        item_order = ['form_occurrence','form_id','trial_form','question_id','form_question_num','question_iteration','subquestion','trial_order','stim','type','test_response']

        # Initialize the array of conditions
        conditions=[]

        # Split it up into a list of conditions
        if self.condition:
            condition_str_array = self.condition.split('\n')
        else:
            return conditions

        # Iterate over the array of condition strings and parse each one
        for cond_str in condition_str_array:
            cond_items = cond_str.split(',')

            curr_condition = dict()
            iresp=0
            for idx, val in enumerate(cond_items):
                if idx < 10:
                    # Get the name of our field
                    item = item_order[idx]

                    # Deal with any special handling
                    if item == 'trial_order':
                        if curr_condition['trial_form'] and expsessinfo:
                            val = expsessinfo['trial_order'] - val
                        else:
                            val = 0

                    # Update our dictionary
                    curr_condition.update({item:val})

                else:
                    # Handle the test responses
                    if 'test_response' not in curr_condition.keys():
                        curr_condition['test_response'] = []

                    curr_condition['test_response'].append(val)

            # Update our list
            conditions.append(curr_condition)

        return conditions

    def conditions_met(self, request):
        met_conditions = True

        expsess_key = 'experiment_%d'%(self.experiment.experiment_id,)
        expsessinfo = request.session[expsess_key]

        #
        # First check for conditions specified within the database
        #
        conditions = self.parse_condition_string(expsessinfo)

        # Iterate over all the conditions, breaking on the first failed condition
        for condition in conditions:
            #check the condref for the form that this condition depends on
            #if condref is false, the parent form was not visited the last time around
            reference = 'condref_%d'%(condition['form_id'])
            if not expsessinfo.get(reference, False):
                met_conditions = False
                break

            # See whether we will have a stimulus filtering constraint
            stimulus_id = expsessinfo.get('stimulus_id', None)
            check_same_stim = (condition['stim'] == 'same_stim') and stimulus_id
                
            # Find the requisite responses in the Response table
            responses = Response.objects.filter(
                session=expsessinfo['session_id'], 
                form=condition['form_id'],
                form_question_num=condition['form_question_num'],
                qdf__question=condition['question_id'],
                qdf__subquestion=condition['subquestion'],
                question_iteration=condition['question_iteration']
                )

            # Handle the same stimulus constraint if necessary
            if stimulus_id:
                responses = responses.filter(stimulus=stimulus_id)

            # Index into the set of responses
            if condition['form_occurrence'] < 0:
                response_idx = responses[responses.count()+condition['form_occurrence']]
            else:
                response_idx = condition['form_occurrence']

            # Pull out the response we'll be examining
            response = responses[response_idx]

            # Check whether the response matches any of the conditions
            if condition['type'] == 'response_enum':
                # Handle single response (radiogroup)
                if response.qdf.html_field_type == 'radiogroup':
                    if response.response_enum not in condition['test_response']:
                        met_conditions = False
                        break
                else:
                    # Handle checkbox
                    if not response.response_enum & sum([pow(2,tr-1) for tr in condition['test_response']]):
                        met_conditions = False
                        break
            elif condition['type'] == 'response_text':
                if response.response_text not in condition['test_response']:
                    met_conditions = False
                    break
            else:
                raise ValueError('Unknown response type: %s'%(condition['type']))

        #
        # Now check whether there is any condition-checking script that we need to run
        #
        if met_conditions and self.condition_matlab:
            # Parse the function call specification
            specdict = parse_function_spec(self.condition_matlab)

            # Call the requested function. Assume it is in the selectors package


        return met_conditions

    def next_form_idx(self, request):
        next_form_idx = None
        experiment_id = self.experiment.experiment_id

        expsess_key = f'experiment_{experiment_id}'
        expsessinfo = request.session[expsess_key]

        # Get our form stack - should be a better way to do this relative to self
        exf = ExperimentXForm.objects.filter(experiment=experiment_id).order_by('form_order')

        # Get our current form
        form_idx = expsessinfo['curr_form_idx']
        currform = exf[form_idx]

        check_conditional = True

        # Fetch our variables that control looping
        num_repeats = self.repeat
        goto_form_idx = self.goto

        # See whether a break loop flag was set
        if expsessinfo['break_loop']:
            # If the user chose to exit the loop
            expsessinfo['curr_form_idx'] += 1
            expsessinfo['break_loop']=False

        elif num_repeats and num_visits == num_repeats:
            # If the repeat value is set and we have visited it this number of times, then move on
            expsessinfo['curr_form_idx'] +=1

        elif goto_form_idx:
            # If a goto form was specified
            expsessinfo['curr_form_idx'] = goto_form_idx

            # Set our looping info
            expsessinfo['last_in_loop'][goto_form_idx] = form_idx

        elif form_idx == exf.count():
            expsessinfo['finished'] = True

            request.session[expsess_key] = expsessinfo
            return HttpResponseRedirect(reverse('terminate_experiment'),args=(experiment_id))
        else:
            expsessinfo['curr_form_idx']+=1

        return expsessinfo['curr_form_idx']

        # # Check whether the next form has conditions associated with it and make sure that conditions are met
        # nextform = exf[next_form_idx]

        # if nextform.condition:
        #     # Parse the condition string to get a list of the conditions that need to be met
        #     conditions = parse_condition_string(nextform.condition, expsessinfo=expsessinfo)

        #     # Evaluate the conditions
        #     met_conditions = evaluate_conditions(conditions)

        #     # Add logic pertaining to unmet conditions


        # if nextform.condition_matlab:
        #     pass

        # # Update our session storage
        # request.session[expsess_key] = expsessinfo    

        # # Update the next variable for this session
        # request.session['next'] = reverse('serve_form', args=(experiment_id,))

        # return next_form_idx


class ExperimentXAttribute(models.Model):
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    attribute = models.ForeignKey('Attribute', db_column='attribute_id',db_constraint=True, on_delete=models.CASCADE)
