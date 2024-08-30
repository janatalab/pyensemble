# models.py
#
# Specifies the core Ensemble models
#
import os
import hashlib
import json
import urllib
import pandas as pd

from django.conf import settings

from django.db import models

from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.contrib.sites.models import Site
from django.urls import reverse
from django.http import JsonResponse

from django.core.serializers.json import DjangoJSONEncoder

from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField, EncryptedDateField

from django.utils import timezone

from datetime import datetime
from dateutil.relativedelta import relativedelta
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from pyensemble.storage_backends import use_media_storage, use_data_storage

from pyensemble.utils.parsers import parse_function_spec, fetch_experiment_method
from pyensemble import tasks


import pdb

#
# Base class tables
#
class Attribute(models.Model):
    name = models.CharField(max_length=50)
    attribute_class = models.CharField(db_column='class', max_length=15)  # Field renamed because it was a Python reserved word.

class DataFormat(models.Model):
    df_type = models.CharField(max_length=15,default='enum')
    enum_values = models.CharField(max_length=512, null=True, blank=True, default=None)

    # Mechanism for saving range information to be associated with a slider.
    # The dictionary stored in the JSON field is expected to have the following key, value pairs:
    # min: <float> - the minimum value of the range
    # max: <float> - the maximum value of the range
    # step: <float> - the step size for the slider
    # anchors: {} - a dictionary in which the key specifies the numeric value at which a label should be centered, and the value is the text value to be displayed at that location
    _range_hash = models.CharField(null=True, max_length=128, db_column='range_hash')
    range_data = models.JSONField(null=True)

    class Meta:
        unique_together = (("df_type", "enum_values"),)

    def choice(self):
        if self.df_type == 'enum':
            self._choice = 'enum(%s)'%(self.enum_values)
        else:
            self._choice = self.df_type

        return self._choice

    @property
    def range_hash(self):
        if self.range_data:
            m = hashlib.md5()
            range_data_str = json.dumps(self.range_data)
            m.update(range_data_str.encode('utf-8'))
            self._range_hash = m.hexdigest()
        else:
            self._range_hash = ''

        return self._range_hash

@receiver(pre_save, sender=DataFormat)
def generate_range_hash(sender, instance, **kwargs):
    instance.range_hash


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
        ('slider','slider'),
    ]

    html_field_type = models.CharField(max_length=10, blank=False, choices=HTML_FIELD_TYPE_OPTIONS, default='radiogroup')

    audio_path = models.CharField(max_length=50, blank=True)

    locked = models.BooleanField(default=False)

    forms = models.ManyToManyField('Form', through='FormXQuestion')

    # class Meta:
    #     unique_together = (("_unique_hash", "data_format"),)

    def __str__(self):
        return self.text

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
            self._unique_hash = m.hexdigest()
        else:
            self._unique_hash = ''

        return self._unique_hash

@receiver(pre_save, sender=Question)
def generate_question_hash(sender, instance, **kwargs):
    instance.unique_hash

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

    is_group = models.BooleanField(default=False, help_text="Subjects participate in groups")

    forms = models.ManyToManyField('Form', through='ExperimentXForm')

    # Method for generating reporting data
    session_reporting_script = models.CharField(max_length=100, blank=True)

    # Method to be called (asynchronously) if the session has been completed
    post_session_callback = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.title

    @property
    def cache_key(self):
        return f'experiment_{self.id}'

    # Method for determining loops in the experiment
    def get_loop_info(self):
        self._loop_info = []

        # Get the forms that are the ends of loops
        endloop_forms = self.experimentxform_set.exclude(goto__isnull=True)

        # Extract start and stop values
        start_stop_list = endloop_forms.values('goto','form_order')

        self._loop_info = {d['goto']:d['form_order'] for d in start_stop_list}

        return self._loop_info

    # Get the last form that is presented without any conditions attached, i.e. all subjects would have responded to, that also has a question on it, i.e. for which there would be a response in the Response table.
    def last_nonconditional_form_with_question(self):
        last_form = self.experimentxform_set.order_by('form_order').filter(
        form__question__isnull=False,
        condition__exact="").last().form

        return last_form

class ResponseQuerySet(models.QuerySet):
    # Method to export response data to a Pandas DataFrame
    def to_dataframe(self):
        # Initialize an empty dataframe
        df = pd.DataFrame()

        # We have to iterate over question types so that we export the correct data type for each variable
        data_types = self.values_list('question__data_format__df_type', 'question__html_field_type').distinct()

        for dtype in data_types:
            # Get the subset corresponding to this data type
            response_subset = self.filter(question__data_format__df_type= dtype[0])

            # Get a list of the fields whose values we want to extract
            extract_fields = [
                'subject_id',
                'response_order',
                'form__name',
                'question__text',
                'trial_info',
                'jspsych_data',
                'misc_info',
            ]

            # Determine which field carries the response value
            if (dtype[0] == 'enum') and (dtype[1] != 'checkbox'):
                value_field = 'response_enum'
                agg_func="mean"
            else:
                value_field = 'response_text'
                agg_func=lambda x: ",".join(x)

            # Add the response value field to the list of fields to extract
            extract_fields.append(value_field)

            # Extract the data
            response_data = response_subset.values(*extract_fields)

            # Convert to dataframe
            resp_df = pd.DataFrame(response_data)

            # Pivot the dataframe to get questions into columns
            resp_df = resp_df.pivot_table(
                index= 'subject_id',
                columns= ['form__name','question__text'],
                values= value_field,
                aggfunc= agg_func)

            # Merge with existing dataframe
            if df.empty:
                df = resp_df
            else:
                df = df.merge(resp_df, left_index=True, right_index=True)

        return df

class ResponseManager(models.Manager):
    def get_queryset(self):
        return ResponseQuerySet(self.model, using=self._db)

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
    response_float = models.FloatField(null=True, blank=True)
    jspsych_data = models.TextField(blank=True) # field for storing data returned by jsPsych
    decline = models.BooleanField(default=False)
    misc_info = models.TextField(blank=True)

    trial_info = models.JSONField(null=True) # field for storing trial information/context

    objects = ResponseManager()

    def response_value(self):
        if self.question.data_format.df_type == 'enum':
            return self.question.choices()[self.response_enum][1]
        else:
            return self.response_text


class AbstractSession(models.Model):
    class Meta:
        abstract = True

    # Which experiment is this session associated with
    experiment = models.ForeignKey(Experiment, db_constraint=True, on_delete=models.CASCADE)

    # When did this session start?
    start_datetime = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    # When did this session end?
    end_datetime = models.DateTimeField(blank=True, null=True)

    # User's timezone
    timezone = models.CharField(max_length=64, blank=True, default=settings.TIME_ZONE)

    # Should this session be excluded from consideration in experiment-wide calculations
    exclude = models.BooleanField(default=False)

    # Has the session been flagged as having expired
    expired = models.BooleanField(default=False, blank=True)

    # If the participant is being referred from a source other than PyEnsemble, e.g. Prolific, have a field for storing the session identifier at the origin, if available and desired.
    origin_sessid = models.CharField(max_length=64, null=True, blank=True)

    # Reporting data
    reporting_data = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    # Has the post-session method associated with the experiment, if any, been executed
    executed_postsession_callback = models.BooleanField(default=False)

    # Conversion to local time of session
    def localtime(self, time):
        tz = settings.TIME_ZONE
        
        if self.timezone:
            tz = self.timezone

        return timezone.localtime(time, zoneinfo.ZoneInfo(tz))

    # Access start of session in local time
    @property
    def start(self):
        self._start = None

        if self.start_datetime:
            self._start = self.localtime(self.start_datetime)

        return self._start

    # Access end of session in local time
    @property
    def end(self):
        self._end = None

        if self.end_datetime:
            self._end = self.localtime(self.end_datetime)
            
        return self._end

    '''
    Method to run the reporting script, if any, that has been associated with the experiment. Note that this method does not return a view, but rather a data dictionary, encoded as JSON, that can be used in a view.

    We may want to add a default reporting script that provides basic session statistics
    '''

    def reporting(self, *args, **kwargs):
        # Get our reporting script
        session_reporting_script = self.experiment.session_reporting_script

        if not session_reporting_script:
            # raise ValueError(f"No reporting script specified for {self.experiment.title}")
            session_reporting_script = 'debug.reporting.default()'

        # Check whether we want to use cached reporting data
        use_cached = kwargs.get('use_cached', False)

        # Check whether we have cached reporting data
        data = {}
        if use_cached:
            data = self.reporting_data

        # Run the reporting if none are currently available
        if not data:
            # Parse the specified reporting script call
            funcdict = parse_function_spec(session_reporting_script)

            # Fetch the reporting method
            method = fetch_experiment_method(funcdict['func_name'])

            # Execute the method
            response = method(self, *args, **kwargs)

            # Convert the response data back out to a dict
            data = json.loads(response.content)

            # Cache the data
            self.reporting_data = data
            self.save()

        return JsonResponse(data)

    '''
    Method to execute an optional method, specified in the experiment, that runs asynchronously on completed sessions.
    '''
    def run_post_session(self, *args, **kwargs):
        # Get our callback
        callback = self.experiment.post_session_callback

        if not callback:
            return

        # Parse the function call specification
        funcdict = parse_function_spec(callback)

        # Get our method
        method = fetch_experiment_method(funcdict['func_name'])

        # Evaluate our method
        response = method(self, *funcdict['args'],**funcdict['kwargs'])

        # Indicate that we've executed the callback
        self.executed_postsession_callback = True
        self.save()

        return response


class Session(AbstractSession):
    # The participant associated with this session
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE,null=True)

    # The ticket used to access this session
    ticket = models.ForeignKey('Ticket', db_constraint=True, on_delete=models.CASCADE, related_name='+')

    # Participant's age at the time of the session
    age = models.PositiveSmallIntegerField(null=True)

    def calc_age(self, *args, **kwargs):
        # Calculate the participant's age the first time the save method is called
        if not self.age:
            if self.subject and self.subject.dob != Subject.dob.field.get_default().date():
                self.age = relativedelta(datetime.now(), self.subject.dob).years
                self.save()

        return self.age


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
    location = models.FileField(storage=use_media_storage(), max_length=512, blank=True)
    url = models.URLField(max_length=512, blank=True)

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
        ('group','Group')
    ]

    ticket_code = models.CharField(max_length=32)
    participant_code = models.CharField(max_length=4, blank=True, default='')
    experimenter_code = models.CharField(max_length=4, blank=True, default='')

    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)

    type = models.CharField(
        max_length=6,
        choices=TICKET_TYPE_CHOICES,
        default='master',
        )

    used = models.BooleanField(default=False)

    validfrom_datetime = models.DateTimeField(blank=True, null=True)
    expiration_datetime = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=64, blank=True, default=settings.TIME_ZONE)

    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE,null=True)

    @property
    def url(self):
        if not getattr(self,'_url', None):
            path = reverse('run_experiment', args=(self.experiment.pk,))
            path += '?' + urllib.parse.urlencode({'tc':self.ticket_code})

            domain = Site.objects.get_current().domain

            if settings.PORT:
                # Used in debugging using runsslserver
                url = f"{domain}{settings.PORT}{path}"
            else:
                # Used in production
                url = f"{domain}/{settings.INSTANCE_LABEL}/{path}"

            # Remove any double forward slash
            url = url.replace('//','/')

            self._url = f"https://{url}"

        return self._url

    def localtime(self, time):
        tz = settings.TIME_ZONE

        if self.timezone:
            tz = self.timezone

        return timezone.localtime(time, zoneinfo.ZoneInfo(tz))

    @property
    def start(self):
        self._start = None
        if self.validfrom_datetime:
            self._start = self.localtime(self.validfrom_datetime)
        return self._start

    @property
    def end(self):
        self._end = None
        if self.expiration_datetime:
            self._end = self.localtime(self.expiration_datetime)
        return self._end

    @property
    def expired(self):
        if self.expiration_datetime and (self.expiration_datetime < timezone.now()):
            self._expired=True
        else:
            self._expired=False

        return self._expired

@receiver(pre_save, sender=Ticket)
def generate_tiny_codes(sender, instance, **kwargs):
    instance.participant_code=instance.ticket_code[:4]
    instance.experimenter_code=instance.ticket_code[-4:]


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
        m.update(str(self.stimulus.location).encode('utf-8'))
        m.update(self.attribute.name.encode('utf-8'))
        # m.update(str(self.attribute_value_double).encode('utf-8'))
        # m.update(self.attribute_value_text.encode('utf-8'))
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
        ('group_trial','group_trial'),
    ]

    form_handler = models.CharField(max_length=50, blank=True, choices=FORM_HANDLER_OPTIONS, default='form_generic')

    goto = models.IntegerField(blank=True, null=True)
    repeat = models.IntegerField(blank=True, null=True)

    # Not-fully-debugged vestige of original Ensemble implementation of how conditional form execution was specified. 
    condition = models.TextField(blank=True)

    '''
    Path to an optional method within a module located under experiments that is evaluated to determine whether this form should be served to the participant
    '''
    condition_script = models.CharField(max_length=100, blank=True)

    '''
    Path to an optional method with a module located under experiments that is evaluated in order to obtain a stimulus identifier, a JSPsych timeline, or any other data that is needed for running the trial associated with the form
    '''
    stimulus_script = models.CharField(max_length=100, blank=True)

    '''
    Path to an optional method within a module located under experiments that is evaluated to determine whether the participant's response should be accepted and recorded to the Response table. This method can be used to trap inadvertent double submissions. The executed method should return True if the response is to be recorded.
    '''
    record_response_script = models.CharField(max_length=100, blank=True)

    break_loop_button = models.BooleanField(default=False)
    break_loop_button_text = models.CharField(max_length=50, blank=True)
    continue_button_text = models.CharField(max_length=50, blank=True, default='Next')

    '''
    Should forms be validated in the client rather than with the Django form-validators. Client-side validation is currently used only to validate completion of required fields, not correct data types.
    '''
    use_clientside_validation = models.BooleanField(default=False)

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

        expsessinfo = request.session.get(self.experiment.cache_key, None)

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
            # Parse the function call specification
            funcdict = parse_function_spec(self.condition_script)

            # Perform any argument variable substitution
            for idx,arg in enumerate(funcdict['args']):
                if arg == 'stimulus_id':
                    funcdict['args'][idx] = expsessinfo.get('stimulus_id', None)

            # Pass along our session_id
            funcdict['kwargs'].update({'session_id': expsessinfo['session_id']})

            # Fetch our callable method
            method = fetch_experiment_method(funcdict['func_name'])

            # Call the select function with the parameters to get the trial specification
            met_conditions = method(request, *funcdict['args'], **funcdict['kwargs'])

        return met_conditions


    def record_response(self, request):
        self._record_response = True

        if self.record_response_script:
            expsessinfo = request.session.get(self.experiment.cache_key, None)

            # Parse the function call specification
            funcdict = parse_function_spec(self.record_response_script)

            # Pass along our session_id
            funcdict['kwargs'].update({'session_id': expsessinfo['session_id']})

            # Fetch our callable method
            method = fetch_experiment_method(funcdict['func_name'])

            # Call the select function with the parameters to get the trial specification
            self._record_response = method(request, *funcdict['args'], **funcdict['kwargs'])

        return self._record_response

    # Method to determine whether we are in a loop
    def in_loop(self, request):
        self._in_loop = False

        if self.last_in_loop(request):
            self._in_loop = True

        return self._in_loop

    # Method to return the last form in the loop we are in, if in a loop
    def last_in_loop(self, request):
        self._last_in_loop = None

        expsessinfo = request.session.get(self.experiment.cache_key, None)

        # Get the form we are on 
        currform_idx = expsessinfo['curr_form_idx']

        # Get all loops that begin on a form with a lesser form index
        possible_loop_starts = []

        first_last_in_loop = self.experiment.get_loop_info()
        for start_idx in first_last_in_loop.keys():
            if start_idx <= currform_idx+1:
                possible_loop_starts.append(start_idx)

        if possible_loop_starts:
            # Get the start of the loop we are in. Nested loops are not supported!
            loop_start = max(possible_loop_starts)

            # Get the last form index of our loop
            last_in_loop = first_last_in_loop[loop_start]

            # If our form index is less than or equal to the last one, we are in the loop
            if currform_idx+1 <= last_in_loop:
                self._last_in_loop = last_in_loop

        return self._last_in_loop

    def next_form_idx(self, request):
        next_form_idx = None
        experiment_id = self.experiment.id

        # Get our experiment session info
        expsessinfo = request.session.get(self.experiment.cache_key, None)

        # Get our session object
        session = Session.objects.get(pk=expsessinfo['session_id'])

        # Get our form stack - should be a better way to do this relative to self
        exf = self.experiment.experimentxform_set.order_by('form_order')

        # Get our current form
        form_idx = expsessinfo['curr_form_idx']
        form_idx_str = str(form_idx)

        currform = exf[form_idx]

        check_conditional = True

        # Fetch our variables that control looping
        num_repeats = self.repeat
        goto_form_idx = self.goto 
        if form_idx_str in expsessinfo['visit_count'].keys():
            num_visits = expsessinfo['visit_count'][form_idx_str]
        else:
            num_visits = 0

        # Check whether an EXIT_LOOP flag has been set in a group session
        if hasattr(session, 'groupsessionsubjectsession'):
            gsss = session.groupsessionsubjectsession

            if gsss.state == gsss.States.EXIT_LOOP:
                # Clear our state
                gsss.state = gsss.States.UNKNOWN
                gsss.save()

                # Check whether we are in a loop and get the idx of the last form if we are
                last_in_loop = self.last_in_loop(request)

                if last_in_loop:
                    # Move to form after end of loop. Remember that curr_form_idx is the actual 1-indexed form_idx-1
                    expsessinfo['curr_form_idx'] = last_in_loop
                    return expsessinfo['curr_form_idx']

        # See whether a break loop flag was set
        if currform.break_loop_button and currform.break_loop_button_text == request.POST['submit']:

            # If the user chose to exit the loop
            expsessinfo['curr_form_idx'] += 1

        elif num_repeats and num_visits >= num_repeats:
            # If the repeat value is set and we have visited it this number of times, then move on
            expsessinfo['curr_form_idx'] +=1

        elif goto_form_idx:
            # If a goto form was specified
            # stored 1-indexed in database
            expsessinfo['curr_form_idx'] = goto_form_idx-1

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
    attribute_value_double = models.FloatField(blank=True, null=True)
    attribute_value_text = models.TextField(blank=True)


#
# Study models - studies are sets of experiments
#

# TODO: Create an Editor view, like the Experiment editor, that allows one to generate a study.

class Study(models.Model):
    title = models.CharField(unique=True, max_length=50)

    def __str__(self):
        return self.title

    @property
    def num_experiments(self):
        return StudyXExperiment.objects.filter(study=self).count()


class StudyXExperiment(models.Model):
    study = models.ForeignKey('Study', db_constraint=True, on_delete=models.CASCADE)
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    experiment_order = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = (("study","experiment", "experiment_order"),)

    def __str__(self):
        return self.experiment.title

    # Method to return the previous experiment in the series
    def prev(self):
        experiment = None

        if self.experiment_order > 1:
            experiment = StudyXExperiment.objects.get(
                study=self.study,
                experiment_order=self.experiment_order-1
                )

        return experiment     

    # Method to return the next experiment in the series
    def next(self):
        experiment = None

        if self.experiment_order < self.study.num_experiments:
            experiment = StudyXExperiment.objects.get(
                study=self.study,
                experiment_order=self.experiment_order+1
                )

        return experiment

# One of the needs associated with studies is to send various notifications with reminders or links pertaining to their participation. It would be nice for this to be automated rather than managed manually. 
# Necessary tasks include:
# 1) Generating subject-specific tickets for each experiment
# 2) Sending notifications (via email) before and/or after any given experiment
#
# Notifications can be scheduled by experiment-specific scheduling callbacks.
# These callbacks are specified in an Experiment's post_session_callback field.

# For now, we are making the assumption that if an experiment is part of a study it is part of only one study. This allows for some simplifying logic in terms of having only a single post_session_callback per experiment, as opposed to having the callback stored in a StudyXExperiment field.

# Note that all times are stored in UTC. It is up to the scheduler in an experiment-specific callback to work out the appropriate timezone offset.

class Notification(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        blank=False,
        null=False,
        editable=False,
        help_text="Time at which the notification entry was created"
    )
    scheduled = models.DateTimeField(
        null=False,
        help_text="Time for which sending of the notification is scheduled"
    )
    sent = models.DateTimeField(
        null=True,
        help_text="Time at which the notification was sent"
    )

    label = models.CharField(max_length=100, blank=True, help_text="Optional label for type of notification")
    template = models.CharField(max_length=100, blank=False)
    context = models.JSONField(null=False)

    # The participant associated with this notification
    subject = models.ForeignKey('Subject', db_constraint=True, on_delete=models.CASCADE)

    # Experiment that was the basis for this notification
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE, null=True)

    # Session that was the basis this notification
    session = models.ForeignKey('Session', db_constraint=True, on_delete=models.CASCADE, null=True)

    # Optional ticket that we want to associate with this notification
    ticket = models.ForeignKey('Ticket', null=True, db_constraint=True, on_delete=models.CASCADE)

    def dispatch(self):
        # Create the context that we send to the template
        context = {}

        # First, add our desired model fields
        context.update({
            'subject': self.subject,
            'experiment': self.experiment,
            'session': self.session,
            'ticket': self.ticket,
        })

        # Now add the context stored in a JSON field
        context.update(self.context)

        # Call the email-generating function
        tasks.send_email(self.template, context)

        # Log the time we sent the notification
        # This should be made more robust in terms of verifying that the send_mail function actually sent the email
        self.sent = timezone.now()
        self.save()

'''
    Models for saving files associated with Sessions and Experiments
'''

def session_filepath(instance, filename):
    return os.path.join('experiment', instance.session.experiment.title, 'session', str(instance.session.id), filename)


class SessionFile(models.Model):
    session = models.ForeignKey('Session', db_constraint=True, on_delete=models.CASCADE)
    file = models.FileField(storage=use_data_storage(), upload_to=session_filepath, max_length=512)

    class Meta:
        unique_together = (("session","file"),)


class SessionFileAttribute(models.Model):
    unique_hash = models.CharField(max_length=32, unique=True)

    file = models.ForeignKey('SessionFile', db_constraint=True, on_delete=models.CASCADE)
    attribute = models.ForeignKey('pyensemble.Attribute', db_constraint=True, on_delete=models.CASCADE)

    attribute_value_double = models.FloatField(blank=True, null=True)
    attribute_value_text = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        m = hashlib.md5()
        m.update(self.file.encode('utf-8'))
        m.update(self.attribute.name.encode('utf-8'))
        m.update(str(self.attribute_value_double).encode('utf-8'))
        m.update(self.attribute_value_text.encode('utf-8'))
        self.unique_hash = m.hexdigest()
        super(SessionFileAttribute, self).save(*args, **kwargs)


def experiment_filepath(instance, filename):
    return os.path.join('experiment', instance.experiment.title, filename)


class ExperimentFile(models.Model):
    experiment = models.ForeignKey('Experiment', db_constraint=True, on_delete=models.CASCADE)
    file = models.FileField(storage=use_data_storage(), upload_to=experiment_filepath, max_length=512)

    class Meta:
        unique_together = (("experiment","file"),)


class ExperimentFileAttribute(models.Model):
    unique_hash = models.CharField(max_length=32, unique=True)

    file = models.ForeignKey('ExperimentFile', db_constraint=True, on_delete=models.CASCADE)
    attribute = models.ForeignKey('pyensemble.Attribute', db_constraint=True, on_delete=models.CASCADE)

    attribute_value_double = models.FloatField(blank=True, null=True)
    attribute_value_text = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        m = hashlib.md5()
        m.update(self.file.encode('utf-8'))
        m.update(self.attribute.name.encode('utf-8'))
        m.update(str(self.attribute_value_double).encode('utf-8'))
        m.update(self.attribute_value_text.encode('utf-8'))
        self.unique_hash = m.hexdigest()
        super(ExperimentFileAttribute, self).save(*args, **kwargs)
