# tasks.py
import hashlib

# from pyensemble.celery import app

from django.conf import settings

from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from django.utils import timezone

import pdb


def fetch_subject_id(subject, scheme='nhdl'):
    from pyensemble.models import Subject

    subject_id=None
    exists = False
    last = subject['name_last'].lower()
    first = subject['name_first'].lower()
    dob = subject['dob']

    # We have to first create our subject root and then check for existing matches in the database. The reason we have to do it in this order is because of the encryption of the subject table.
    if scheme=='nhdl':
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

    else:
        raise ValueError('unknown subject ID generator')

def get_or_create_prolific_subject(request):
    from pyensemble.models import Subject

    # Get the Prolific ID
    prolific_id = request.GET.get('PROLIFIC_PID', None)

    # Make sure the parameter was actually specified
    if not prolific_id:
        return HttpResponseBadRequest('No Profilic ID specified')

    # Get or create a subject entry
    return Subject.objects.get_or_create(subject_id=prolific_id, id_origin='PRLFC')

def create_tickets(ticket_request_data):
    from pyensemble.models import Ticket, Experiment

    # Get the number of existing tickets
    num_existing_tickets = Ticket.objects.all().count()

    # Initialize our new ticket list
    ticket_list = []

    # Get our experiment
    experiment_id = ticket_request_data['experiment_id']
    experiment = Experiment.objects.get(id=experiment_id)

    # Get our ticket types
    ticket_types = [tt[0] for tt in Ticket.TICKET_TYPE_CHOICES]

    for ticket_type in ticket_types:
        num_tickets = ticket_request_data.get(f'num_{ticket_type}', 0)

        # Check whether the request is for a specific subject
        subject = ticket_request_data.get('subject', None)

        if num_tickets:
            expiration_datetime = ticket_request_data.get(f'{ticket_type}_expiration',None)

            # Add the ticket(s)
            for iticket in range(num_tickets):
                unencrypted_str = '%d_%d'%(num_existing_tickets+len(ticket_list), experiment_id)
                encrypted_str = hashlib.md5(unencrypted_str.encode('utf-8')).hexdigest()

                # Add a new ticket to our list
                ticket = Ticket.objects.create(
                    ticket_code=encrypted_str, 
                    experiment=experiment, 
                    type=ticket_type, 
                    expiration_datetime=expiration_datetime,
                    subject = subject
                )
                ticket_list.append(ticket)

    return ticket_list

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
    to_email = [context['subject'].email]

    # Construct the basic message
    message = EmailMultiAlternatives(
        msg_subject,
        text_content,
        from_email,
        to_email
    )

    # Add the HTML-formatted version
    message.attach_alternative(html_content, "text/html")

    # Send the message
    num_sent = message.send()

    return num_sent

# This should probably be implemented as a method on a Notification queryset manager
# @app.task()
def dispatch_notifications():
    from pyensemble.models import Notification
    
    # Get a list of unsent notifications that were scheduled to be sent prior to the present time
    notification_list = Notification.objects.filter(sent__isnull=True, scheduled__lte=timezone.now())

    for notification in notification_list:
        notification.dispatch()

def execute_postsession_callbacks():
    from pyensemble.models import Session 

    # Get a list of completed Sessions for which the Experiment has a post_session_callback, and the callback has not been executed
    sessions = Session.objects.exclude(
            end_datetime__isnull = True,
            experiment__post_session_callback__exact = "")

    sessions = sessions.filter(executed_postsession_callback = False)

    for session in sessions:
        session.run_post_session()