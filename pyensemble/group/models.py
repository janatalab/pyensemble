from django.db import models

#
# Models for supporting group sessions
#

class Group(models.Model):
    name = models.CharField(max_length=256, unique=True, blank=False)
    description = models.TextField(max_length=1024, blank=True)

    def __str__(self):
        return self.name


class GroupSubject(models.Model):
    group = models.ForeignKey('Group', db_constraint=True, on_delete=models.CASCADE)
    subject = models.ForeignKey('pyensemble.Subject', db_constraint=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.group.name}: {self.subject.name_first} {self.subject.name_last}'


class GroupSession(models.Model):
    group = models.ForeignKey('Group', db_constraint=True, on_delete=models.CASCADE)
    experiment = models.ForeignKey('pyensemble.Experiment', db_constraint=True, on_delete=models.CASCADE)
    ticket = models.OneToOneField('pyensemble.Ticket', db_constraint=True, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    experimenter_attached = models.BooleanField(default=False)

    # Mechanism for saving overall session parameters
    params = models.JSONField(default=dict)

    # Mechanism for caching current context
    context = models.JSONField(default=dict)

    # Mechanism for indicating session state
    class States(models.IntegerChoices):
        UNKNOWN = 0
        READY = 1
        RUNNING = 2
        COMPLETED = 3
        ABORTED = 4
    
    state = models.PositiveSmallIntegerField(choices=States.choices, default=States.UNKNOWN)

    terminal_states = [States.COMPLETED, States.ABORTED]

    @property
    def num_users(self):
        return self.user_session_set.count()

    @property
    def modifiable(self):
        self._modifiable=True
        if self.state in terminal_states:
            self._modifiable=False

        return self._modifiable

    def responding_complete(self, trial_num):
        self._responding_complete = False
        if trial_num == 0:
            self._responding_complete =  True

        else:
            # Search the trial_info field the Response table contains an entry for the designated trial for all session users
            responded = Response.objects.filter(session__in=self.user_session_set, trial_info__trial_num=trial_num)

            if responded.count() == self.num_users:
                self._responding_complete =  True

        return self._responding_complete

    def users_ready(self):
        # Get number of users attached to this session
        num_users = self.groupsessionsubjectsession_set.count()

        # Get number of users in ready state
        ready_users = self.groupsessionsubjectsession_set.filter(state=GroupSessionSubjectSession.States.READY)

        return num_users == ready_users.count()


    class Meta:
        unique_together = (("group","experiment","ticket"),)

    def __str__(self):
        return "Group: %s, Experiment: %s, Session %d"%(self.group.name, self.experiment.title, self.id)

    def get_cache_key(self):
        return f'groupsession_{self.id}'


class GroupSessionSubjectSession(models.Model):
    group_session = models.ForeignKey('GroupSession', db_constraint=True, on_delete=models.CASCADE)
    user_session = models.ForeignKey('pyensemble.Session', db_constraint=True, on_delete=models.CASCADE)

    # Mechanism for indicating participant session state
    class States(models.IntegerChoices):
        UNKNOWN = 0
        READY = 1
        RESPONSE_PENDING = 2
    
    state = models.PositiveSmallIntegerField(choices=States.choices, default=States.UNKNOWN)

    class Meta:
        unique_together = (('group_session','user_session'),)