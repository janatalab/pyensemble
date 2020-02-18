# models.py
#
# Specifies the core Ensemble models
#

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField, EncryptedDateField

#
# Base class tables
#
class Attribute(models.Model):
    attribute_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    class_field = models.CharField(db_column='class', max_length=15)  # Field renamed because it was a Python reserved word.

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
    condition = models.TextField(blank=True)
    condition_matlab = models.CharField(max_length=40, blank=True)
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

class Session(models.Model):
    session_id = models.IntegerField(primary_key=True)
    date_time = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    ticket = models.ForeignKey('Ticket', db_column='ticket_id', db_constraint=True, on_delete=models.CASCADE, related_name='+')
    subject = models.ForeignKey('Subject', db_column='subject_id', db_constraint=True, on_delete=models.CASCADE)
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

    ticket_id = models.IntegerField(primary_key=True)
    ticket_code = models.CharField(max_length=32)
    experiment = models.ForeignKey('Experiment', db_column='experiment_id', db_constraint=True, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=6,
        choices=TICKET_TYPE_CHOICES,
        default='master',
        )
    used = models.BooleanField(default=False)
    expiration_datetime = models.DateTimeField(blank=True, null=True)
    session = models.ForeignKey('Session',db_column='session_id',on_delete=models.CASCADE,related_name='+')
    assigned = models.BooleanField(default=False)


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
