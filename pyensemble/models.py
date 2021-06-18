# models.py
#
# Specifies the core Ensemble models
#
import hashlib

from django.db import models
from django.urls import reverse

from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField, EncryptedDateField

from django.utils import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

from pyensemble.utils.parsers import parse_function_spec, fetch_experiment_method

import pdb

#
# Base class tables
#
class Attribute(models.Model):
    name = models.CharField(max_length=50)
    attribute_class = models.CharField(db_column='class', max_length=15)  # Field renamed because it was a Python reserved word.

class DataFormat(models.Model):
    df_type = models.CharField(max_length=15,default='enum')
    enum_values = models.CharField(max_length=512, blank=True)

    class Meta:
        unique_together = (("df_type", "enum_values"),)

    def choice(self):
        if self.df_type == 'enum':
            self._choice = 'enum(%s)'%(self.enum_values)
        else:
            self._choice = self.df_type

        return self._choice

class Question(models.Model):
    _unique_hash = models.CharField(max_length=128, unique=True, db_column='unique_hash')
    text = models.TextField(blank=False)
    category = models.CharField(max_length=64, blank=True)

    data_format = models.ForeignKey('DataFormat', db_constraint=True, on_delete=models.CASCADE)
    value_range = models.CharField(max_length=30, blank=True)
    value_default = models.CharField(max_length=30, blank=True)

    HTML_FIELD_TYPE_OPTIONS = [
        ('radiogroup','radiogroup'),
        ('checkbox','checkbox'),
        ('textarea','textarea'),
        ('text','text'),
        ('menu','menu'),
        ('numeric','numeric'),
    ]

    html_field_type = models.CharField(max_length=10, blank=False, choices=HTML_FIELD_TYPE_OPTIONS, default='radiogroup')

    audio_path = models.CharField(max_length=50, blank=True)

    locked = models.BooleanField(default=False)

    forms = models.ManyToManyField('Form', through='FormXQuestion')

    class Meta:
        unique_together = (("_unique_hash", "data_format"),)

    def __unicode__(self):
        return self.text

    def choices(self):
        items = self.data_format.enum_values.split('","')
        return [(idx,lbl.replace('"','')) for idx,lbl in enumerate(items)]

    @property
    def unique_hash(self):
        if self.text:
            m = hashlib.md5()
            m.update(self.text.encode('utf-8'))
            self._unique_hash = m.digest()
        else:
            self._unique_hash = ''

        return self._unique_hash

class Form(models.Model):
    name = models.CharField(unique=True, max_length=50)
    category = models.CharField(max_length=19, blank=True)
    header = models.TextField(blank=True)
    footer = models.TextField(blank=True)
    header_audio_path = models.CharField(max_length=50, blank=True)
    footer_audio_path = models.CharField(max_length=50, blank=True)
    version = models.FloatField(blank=True, null=True)
    locked = models.BooleanField(default=False)
    visit_once = models.BooleanField(default=False)

    questions = models.ManyToManyField('Question', through='FormXQuestion')
    experiments = models.ManyToManyField('Experiment', through='ExperimentXForm')

    # Add visited and can_visit properties

class Experiment(models.Model):
    title = models.CharField(unique=True, max_length=50)
    description = models.TextField(blank=True)
    irb_id = models.CharField(max_length=30, blank=True)
    sona_url = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=30,default='en')
    play_question_audio = models.BooleanField(default=False)
    params = models.TextField(blank=True)
    locked = models.BooleanField(default=False)

    forms = models.ManyToManyField('Form', through='ExperimentXForm')

class Response(models.Model):
    date_time = models.DateTimeField(auto_now_add=True)
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE)
    session = models.ForeignKey('Session', db_constraint=True, on_delete=models.CASCADE)
    form = models.ForeignKey('Form', db_constraint=True, on_delete=models.CASCADE)
    form_order = models.PositiveSmallIntegerField(null=False,default=None)

    question = models.ForeignKey('Question', db_constraint=True, on_delete=models.CASCADE)
    form_question_num = models.PositiveSmallIntegerField(null=False,default=None)
    question_iteration = models.PositiveSmallIntegerField(null=False,default=1)

    stimulus = models.ForeignKey('Stimulus', db_constraint=True, on_delete=models.CASCADE, null=True)

    response_order = models.PositiveSmallIntegerField(null=False,default=None)
    response_text = models.TextField(blank=True)
    response_enum = models.IntegerField(blank=True, null=True)
    jspsych_data = models.TextField(blank=True)
    decline = models.BooleanField(default=False)
    misc_info = models.TextField(blank=True)

class Session(models.Model):
    date_time = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    ticket = models.ForeignKey('Ticket', db_constraint=True, on_delete=models.CASCADE, related_name='+')
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE,null=True)
    age = models.PositiveSmallIntegerField(null=True)

    # If the participant is being referred from a source other than PyEnsemble, e.g. Prolific, have a field for storing the session identifier at the origin, if available and desired.
    origin_sessid = models.CharField(max_length=64, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.subject and self.subject.dob != Subject.dob.field.get_default().date():
            self.age = relativedelta(datetime.now(),self.subject.dob).years
        super().save(*args, **kwargs)


class Stimulus(models.Model):
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

    ID_ORIGINS = [
        ('PYENS', 'PyEnsemble'),
        ('PRLFC', 'Prolific')
    ]

    subject_id = models.CharField(primary_key=True, max_length=32)
    id_origin = models.CharField(max_length=12, choices=ID_ORIGINS, default='PYENS')
    date_entered = models.DateField(auto_now_add=True)
    name_last = EncryptedCharField(max_length=24)
    name_first = EncryptedCharField(max_length=24)
    name_middle = EncryptedCharField(max_length=24)
    name_suffix = EncryptedCharField(max_length=24)
    passphrase = EncryptedCharField(max_length=64)
    security_questions = models.TextField()
    security_responses = EncryptedTextField(max_length=128)
    email = EncryptedEmailField(max_length=48)
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
        max_length=4,
        choices=RACE_OPTIONS,
        default='UN',
        )
    dob = EncryptedDateField(default=datetime(1900,1,1))
    notes = models.TextField()

class Ticket(models.Model):
    TICKET_TYPE_CHOICES=[
        ('master','Master'),
        ('user','User'),
    ]

    ticket_code = models.CharField(max_length=32)
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=6,
        choices=TICKET_TYPE_CHOICES,
        default='master',
        )
    used = models.BooleanField(default=False)
    expiration_datetime = models.DateTimeField(blank=True, null=True)

    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE,null=True)

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
    unique_hash = models.CharField(max_length=32, unique=True)

    child = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='children',
    )
    parent = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='parents',
    )
    mapping_name = models.CharField(blank=False, max_length=256)
    mapping_value_double = models.FloatField(blank=True, null=True)
    mapping_value_text = models.CharField(blank=True, max_length=256)

    def save(self, *args, **kwargs):
        m = hashlib.md5()
        m.update(self.child.name.encode('utf-8'))
        m.update(self.parent.name.encode('utf-8'))
        m.update(self.mapping_name.encode('utf-8'))
        m.update(str(self.mapping_value_double).encode('utf-8'))
        m.update(self.mapping_value_text.encode('utf-8'))
        self.unique_hash = m.hexdigest()
        super(AttributeXAttribute, self).save(*args, **kwargs)

class StimulusXAttribute(models.Model):
    unique_hash = models.CharField(max_length=32, unique=True)

    stimulus = models.ForeignKey('Stimulus', db_constraint=True, on_delete=models.CASCADE)
    attribute = models.ForeignKey('Attribute', db_constraint=True, on_delete=models.CASCADE)
    attribute_value_double = models.FloatField(blank=True, null=True)
    attribute_value_text = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        m = hashlib.md5()
        m.update(self.stimulus.name.encode('utf-8'))
        m.update(self.attribute.name.encode('utf-8'))
        m.update(str(self.attribute_value_double).encode('utf-8'))
        m.update(self.attribute_value_text.encode('utf-8'))
        self.unique_hash = m.hexdigest()
        super(StimulusXAttribute, self).save(*args, **kwargs)

class ExperimentXStimulus(models.Model):
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    stimulus = models.ForeignKey('Stimulus', db_constraint=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("experiment", "stimulus"),)

class FormXQuestion(models.Model):
    form = models.ForeignKey('Form', db_constraint=True, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', db_constraint=True, on_delete=models.CASCADE)
    question_iteration = models.IntegerField(default=1)
    form_question_num = models.IntegerField()
    required = models.BooleanField(default=True)

    class Meta:
        unique_together = (("form","question","form_question_num","question_iteration"),)

class ExperimentXForm(models.Model):
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    form = models.ForeignKey('Form', db_constraint=True, on_delete=models.CASCADE)
    form_order = models.IntegerField()

    FORM_HANDLER_OPTIONS = [
        ('form_generic','form_generic'),
        ('form_stimulus_s','form_stimulus_s'),
        ('form_generic_s','form_generic_s'),
        ('form_image_s','form_image_s'),
        ('form_feedback','form_feedback'),
        ('form_end_session','form_end_session'),
        ('form_consent','form_consent'),
        ('form_subject_register','form_subject_register'),
        ('form_subject_email','form_subject_email'),
    ]

    form_handler = models.CharField(max_length=50, blank=True, choices=FORM_HANDLER_OPTIONS, default='form_generic')
    goto = models.IntegerField(blank=True, null=True)
    repeat = models.IntegerField(blank=True, null=True)
    condition = models.TextField(blank=True)
    condition_script = models.CharField(max_length=100, blank=True)
    stimulus_script = models.CharField(max_length=100, blank=True)
    break_loop_button = models.BooleanField(default=False)
    break_loop_button_text = models.CharField(max_length=50, blank=True)
    continue_button_text = models.CharField(max_length=50, blank=True, default='Next')

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

        expsess_key = 'experiment_%d'%(self.experiment.id,)
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
        if met_conditions and self.condition_script:
            from pyensemble import experiments

            # Parse the function call specification
            funcdict = parse_function_spec(self.condition_script)

            # Perform any argument variable substitution
            for idx,arg in enumerate(funcdict['args']):
                if arg == 'stimulus_id':
                    funcdict['args'][idx] = expsessinfo.get('stimulus_id', None)

            # Pass along our session_id
            funcdict['kwargs'].update({'session_id': expsessinfo['session_id']})

            method = fetch_experiment_method(funcdict['func_name'])

            # Call the select function with the parameters to get the trial specification
            met_conditions = method(request, *funcdict['args'],**funcdict['kwargs'])

        return met_conditions

    def next_form_idx(self, request):
        next_form_idx = None
        experiment_id = self.experiment.id

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
        num_visits = expsessinfo['visit_count'][form_idx]

        # See whether a break loop flag was set
        if currform.break_loop_button and currform.break_loop_button_text == request.POST['submit']:
            # If the user chose to exit the loop
            expsessinfo['curr_form_idx'] += 1

        elif num_repeats and num_visits == num_repeats:
            # If the repeat value is set and we have visited it this number of times, then move on
            expsessinfo['curr_form_idx'] +=1

        elif goto_form_idx:
            # If a goto form was specified
            # stored 1-indexed in database
            expsessinfo['curr_form_idx'] = goto_form_idx-1

            # Set our looping info
            expsessinfo['last_in_loop'][goto_form_idx-1] = form_idx

        elif form_idx == exf.count():
            expsessinfo['finished'] = True

            request.session[expsess_key] = expsessinfo
            return HttpResponseRedirect(reverse('terminate_experiment'),args=(experiment_id))
        else:
            expsessinfo['curr_form_idx']+=1

        return expsessinfo['curr_form_idx']

class ExperimentXAttribute(models.Model):
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    attribute = models.ForeignKey('Attribute', db_constraint=True, on_delete=models.CASCADE)
