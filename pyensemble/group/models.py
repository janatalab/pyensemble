from django.db import models
from django.conf import settings

from django.utils import timezone

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from pyensemble.models import AbstractSession

import polling2

import pdb

#
# Models for supporting group sessions
#

class Group(models.Model):
    name = models.CharField(max_length=255, unique=True, blank=False)
    description = models.TextField(max_length=1024, blank=True)

    def __str__(self):
        return self.name


class GroupSubject(models.Model):
    group = models.ForeignKey('Group', db_constraint=True, on_delete=models.CASCADE)
    subject = models.ForeignKey('pyensemble.Subject', db_constraint=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.group.name}: {self.subject.name_first} {self.subject.name_last}'

def init_session_context():
    return {'state': ''}


class GroupSession(AbstractSession):
    group = models.ForeignKey('Group', db_constraint=True, on_delete=models.CASCADE)

    ticket = models.OneToOneField('pyensemble.Ticket', db_constraint=True, on_delete=models.CASCADE)

    experimenter_attached = models.BooleanField(default=False)

    # Mechanism for saving overall session parameters
    params = models.JSONField(default=dict)

    # Mechanism for caching current (trial) context
    context = models.JSONField(default=init_session_context)

    # Group session notetaking
    notes = models.TextField(blank=True)

    # Mechanism for indicating session state
    class States(models.IntegerChoices):
        UNKNOWN = 0
        READY = 1
        RUNNING = 2
        COMPLETED = 3
        ABORTED = 4
    
    state = models.PositiveSmallIntegerField(choices=States.choices, default=States.UNKNOWN)

    terminal_states = [States.COMPLETED, States.ABORTED]

    class Meta:
        unique_together = (("group","experiment","ticket"),)

    def __str__(self):
        return "Group: %s, Experiment: %s, Session %d"%(self.group.name, self.experiment.title, self.id)

    @property
    def cache_key(self):
        return f'groupsession_{self.id}'

    @property
    def num_users(self):
        return self.groupsessionsubjectsession_set.count()

    # The place we need to enforce modifiability is on our save() method in order to prevent changes once we've saved ourselves once in a terminal state. So, we need to overwrite the default save method.
    @property
    def modifiable(self):
        self._modifiable=True
        if self.state in terminal_states:
            self._modifiable=False

        return self._modifiable


    def set_context_state(self, state):
        # Set the trial state in the context dictionary
        context = self.context
        context.update({'state': state})

        self.context = context
        self.save()

    def get_context_state(self):
        if not self.context:
            state = 'undefined'
        else:
            state = self.context.get('state','undefined')
        return state

    def cleanup(self):
        # Expire the ticket
        self.ticket.used = True
        self.ticket.expiration_datetime = timezone.now()
        self.ticket.save()

        # Flag all the user sessions as expired
        self.groupsessionsubjectsession_set.all().expire_sessions()

    # Methods that operate across users connected to this session
    # We don't currently use the responding_complete method, relying instead on setting of user state. This method affords an added layer of verification that all users are synchronized at the same location in the progression through a series of trials
    def responding_complete(self, trial_num):
        self._responding_complete = False
        if trial_num == 0:
            self._responding_complete =  True

        else:
            # Search the trial_info field the Response table contains an entry for the designated trial for all session users
            responded = Response.objects.filter(session__in=self.groupsessionsubjectsession_set, trial_info__trial_num=trial_num)

            if responded.count() == self.num_users:
                self._responding_complete =  True

        return self._responding_complete

    # Methods that signal synchrony among subjects
    def group_ready_server(self):
        return self.groupsessionsubjectsession_set.all().ready_server()

    def group_ready_client(self):
        return self.groupsessionsubjectsession_set.all().ready_client()

    # Methods that return when synchrony has been achieved
    def wait_group_ready_server(self, timeout=120):
        try:
            polling2.poll(self.group_ready_server, step=0.5, timeout=timeout)
            return True

        except polling2.TimeoutException:
            return False

    def wait_group_ready_client(self, timeout=120):
        try:
            polling2.poll(self.group_ready_client, step=0.5, timeout=timeout)
            return True

        except polling2.TimeoutException:
            return False

    # Methods used by an experimenter to set state on all connected subject sessions
    def set_group_response_pending(self):
        self.groupsessionsubjectsession_set.all().set_state('RESPONSE_PENDING')

    def set_group_busy(self):
        self.groupsessionsubjectsession_set.all().set_state('BUSY')

    def set_group_exit_loop(self):
        self.groupsessionsubjectsession_set.all().set_state('EXIT_LOOP')


def group_filename(instance, filename):
    return "{0}/{1}/{2}".format(instance.group_session.experiment.title, instance.group_session.id, filename)

class GroupSessionFile(models.Model):
    group_session = models.ForeignKey('Group', db_constraint=True, on_delete=models.CASCADE)
    file = models.FileField(upload_to=group_filename)


class GroupSessionFileAttribute(models.Model):
    unique_hash = models.CharField(max_length=32, unique=True)

    file = models.ForeignKey('GroupSessionFile', db_constraint=True, on_delete=models.CASCADE)
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
        super(GroupSessionFileAttribute, self).save(*args, **kwargs)


class GroupSessionSubjectSessionQuerySet(models.QuerySet):
    def ready_server(self):
        return self.count() == self.filter(state=self.model.States.READY_SERVER).count()

    def ready_client(self):
        return self.count() == self.filter(state=self.model.States.READY_CLIENT).count()

    def set_state(self, state):
        if type(state) == str:
            state = state.upper()

            if state not in self.model.States.names:
                raise ValueError(f"{state} not a valid state")

            state = self.model.States[state]

        self.update(state=state)

    def expire_sessions(self):
        for session in self:
            session.user_session.expired=True
            session.user_session.save()


class GroupSessionSubjectSessionManager(models.Manager):
    def get_queryset(self):
        return GroupSessionSubjectSessionQuerySet(self.model, using=self._db)

class GroupSessionSubjectSession(models.Model):
    group_session = models.ForeignKey('GroupSession', db_constraint=True, on_delete=models.CASCADE)
    user_session = models.OneToOneField('pyensemble.Session', db_constraint=True, on_delete=models.CASCADE)

    #
    # Mechanism for indicating subject session state
    #

    '''
    UNKNOWN - Users start out in an unknown state and return to this state when on a form that doesn't pertain to a group trial

    READY_SERVER - used to indicate that a subject's session is ready for the next form. Used to synchronize subjects prior to calling of a method specified in the stimulus_script field of an ExperimentXForm instance.

    READY_CLIENT - used to indicate that the subject's browser is ready for a trial to commence. This is used for experiments in which an experimenter process initiates a trial once all subjects are declared ready on the client. 

    BUSY - Can be set to indicate that the subject is in the middle of a trial

    RESPONSE_PENDING - Can be used to signal that a experimenter or participant's client-side trial has completed and that the subject's form submission is being awaited

    EXIT_LOOP - This flag is used to signal that a loop should be exited. It is checked on the GET branch in pyensemble.views.serve_form()

    NOTE: By default, when a form uses a group_trial form handler, the READY_SERVER and READY_CLIENT states are automatically implemented, respectively, in pyensemble.views.serve_form and a JavaScript routine that is embedded in the group_trial.html template and automatically executes when the subject's browswer is ready. These states are the only states that are needed for self-standing group experiments, i.e. those that don't require an experimenter to initiate trials or send state-setting signals. 

    Experimenter-driven group sessions will likely depend on the READY_CLIENT states of participants to initialize or start trials, and may optionally set BUSY and RESPONSE_PENDING states for added control and status reporting.

    '''

    class States(models.IntegerChoices):
        UNKNOWN = 0
        READY_SERVER = 1
        READY_CLIENT = 2
        BUSY = 3
        RESPONSE_PENDING = 4
        EXIT_LOOP = 5
    
    state = models.PositiveSmallIntegerField(choices=States.choices, default=States.UNKNOWN)

    objects = GroupSessionSubjectSessionManager()

    class Meta:
        unique_together = (('group_session','user_session'),)

    def in_state(self, *args, **kwargs):
        # Have to refresh our state from the db
        self.refresh_from_db()

        for state in kwargs['state']:
            if self.state == self.States[state]:
                return True

        return False


    def wait_state(self, state, timeout=45):
        try:
            if not isinstance(state, list):
                state = [state]

            polling2.poll(self.in_state, kwargs={'state': state}, step=0.5, timeout=timeout)
            return True

        except polling2.TimeoutException:
            return False
