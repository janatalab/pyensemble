# tasks.py
import hashlib
import traceback

from django.conf import settings

from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from django.utils import timezone

from pyensemble.models import Subject, Session, Ticket, Experiment, Attribute, Notification

import logging
logger = logging.getLogger(__name__)

import pdb


def fetch_subject_id(subject, scheme='nhdl'):
    subject_id=None
    exists = False

    # We have to first create our subject root and then check for existing matches in the database. The reason we have to do it in this order is because of the encryption of the subject table.
    if scheme=='nhdl':
        last = subject['name_last'].lower()
        first = subject['name_first'].lower()
        dob = subject['dob']

        subject_id_root = '%02d%s%s%02d'%(dob.month, str(last[0]+last[-1:]+first[0]), str(dob.year)[-2:], dob.day)

        # Get a list of all subjects with the same root
        subjects = Subject.objects.filter(subject_id__contains=subject_id_root)

        # Iterate over the existing subjects and see if we have a match
        for currsub in subjects:
            if currsub.name_last.lower() == last and currsub.name_first.lower() == first and currsub.dob == dob:
                return currsub.subject_id, True

        # If we found no match, create a new entry
        subject_id = subject_id_root+str(subjects.count()+1)
        return subject_id, False

    elif scheme=='email':
        # Create a hash of the email address and limit the length to 32 characters
        email = subject.email.lower()

        subject_id = hashlib.md5(email.encode('utf-8')).hexdigest()[:32]

        # Check for an existing subject with the same hash
        exists = Subject.objects.filter(subject_id=subject_id).exists()

        # Check whether the emails match
        if exists:
            emails_match = Subject.objects.get(subject_id=subject_id).email == email

            # If the subject does not exist, create a new entry.
            # Do this by appending a number to the end of the email and hashing it again.
            if not emails_match:
                raise ValueError('email hash collision')

        return subject_id, exists

    else:
        raise ValueError('unknown subject ID generator')


def create_tickets(ticket_request_data):
    # Get the number of existing tickets
    num_existing_tickets = Ticket.objects.count()

    # Initialize our new ticket list
    ticket_list = Ticket.objects.none()

    # Get our experiment
    experiment = ticket_request_data.get('experiment', None)

    if not experiment:
        experiment_id = ticket_request_data['experiment_id']
        experiment = Experiment.objects.get(id=experiment_id)

    # Get our ticket timezone
    timezone = ticket_request_data.get('timezone', settings.TIME_ZONE)

    # Get our ticket types
    ticket_types = [tt[0] for tt in Ticket.TICKET_TYPE_CHOICES]

    for ticket_type in ticket_types:
        num_tickets = ticket_request_data.get(f'num_{ticket_type}', 0)

        # Check whether the request is for a specific subject
        subject = ticket_request_data.get('subject', None)

        if num_tickets:
            validfrom_datetime = ticket_request_data.get(f'{ticket_type}_validfrom', None)
            expiration_datetime = ticket_request_data.get(f'{ticket_type}_expiration',None)

            # Add the ticket(s)
            for iticket in range(num_tickets):
                unencrypted_str = '%d_%d'%(num_existing_tickets+ticket_list.count(), experiment.id)
                encrypted_str = hashlib.md5(unencrypted_str.encode('utf-8')).hexdigest()

                # Add a new ticket to our list
                ticket = Ticket.objects.create(
                    ticket_code = encrypted_str,
                    experiment = experiment,
                    type = ticket_type,
                    validfrom_datetime = validfrom_datetime,
                    expiration_datetime = expiration_datetime,
                    timezone = timezone,
                    subject = subject
                )

                # If an attribute is specified, add it to the ticket
                attribute_name = ticket_request_data.get('attribute', None)
                if attribute_name:
                    # Get the attribute
                    attribute, _ = Attribute.objects.get_or_create(name=attribute_name)
                    ticket.attribute = attribute
                    ticket.save()

                ticket_list = ticket_list | Ticket.objects.filter(id=ticket.id)

    return ticket_list


'''
Define a method for generating a ticket for a subject to participate in the next experiment in the study.
'''
def create_next_experiment_ticket(session, **kwargs):
    # Get the next experiment in the study
    next_experiment = session.experiment.studyxexperiment_set.first().next_experiment()

    if not next_experiment:
        return None

    # Formulate our basic ticket request
    ticket_request = {
        'experiment': next_experiment,
        'subject': session.subject,
        'num_user': 1,
        'timezone': session.timezone,
    }

    # Update the ticket request with any additional parameters
    ticket_request.update(kwargs)

    # Create the ticket
    ticket = create_tickets(ticket_request).first()

    return ticket


def get_or_create_next_experiment_ticket(session, **kwargs):
    # Get the next experiment in the study
    next_experiment = session.experiment.studyxexperiment_set.first().next_experiment()

    if not next_experiment:
        return None

    # Get the existing ticket
    ticket = Ticket.objects.filter(experiment=next_experiment, subject=session.subject).first()

    # If the ticket does not exist, create it
    if not ticket:
        ticket = create_next_experiment_ticket(session, **kwargs)

    return ticket


def send_email(template_name, context):
    # Get our template
    template = loader.get_template(template_name)

    # Render the content as HTML
    html_content = template.render(context)
    
    # Create the text alternative
    text_content = strip_tags(html_content)

    # Get the from email address
    from_email = settings.DEFAULT_FROM_EMAIL

    # Get the message subject
    msg_subject = context.get("msg_subject","No subject")

    # Get the subject's email
    to_email = context.get("to_email", None)

    if not to_email:
        to_email = context['session'].subject.email

    # Construct the basic message
    message = EmailMultiAlternatives(
        msg_subject,
        text_content,
        from_email,
        [to_email]
    )

    # Add the HTML-formatted version
    message.attach_alternative(html_content, "text/html")

    # Send the message
    num_sent = message.send()

    return num_sent


# Create notifications
def create_notifications(session, notification_list):
    # Initialize our Notification queryset
    notifications = Notification.objects.none()

    for n in notification_list:
        # Create an entry in our notifications table
        nobj = Notification.objects.create(
            subject = session.subject,
            experiment = session.experiment,
            session = session,

            template = n['template'],
            scheduled = n['datetime'],
            context = n['context']
        )

        # Add the notification to our notifications QuerySet
        notifications = notifications | Notification.objects.filter(id=nobj.id)

    return notifications

# This should probably be implemented as a method on a Notification queryset manager
# @app.task()
def dispatch_notifications():
    # Get a list of unsent notifications that were scheduled to be sent prior to the present time
    notification_list = Notification.objects.filter(sent__isnull=True, scheduled__lte=timezone.now())

    for notification in notification_list:
        notification.dispatch()

    return notification_list.count()


def execute_postsession_callbacks():
    error_count = 0

    # Get a list of completed Sessions for which the Experiment has a post_session_callback
    sessions = Session.objects.exclude(experiment__post_session_callback__exact = "").exclude(end_datetime__isnull = True)

    # Get those that have not yet been executed
    sessions = sessions.filter(executed_postsession_callback = False)

    for session in sessions:
        try:
            session.run_post_session()

        except Exception as err:
            error_count += 1

            msg = f'postsession_callback execution failed for Session: {session.id}\nExperiment: {session.experiment}\nSubject: {session.subject.subject_id}\nError: {err}\n{traceback.format_exc()}'
            if settings.DEBUG:
                print(msg)
            else:
                logger.error(msg)

    return error_count
