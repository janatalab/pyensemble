"""Invitation-only creation of verified research-interface accounts."""

import hashlib
import logging
import secrets
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from pyensemble.access import ROLE_GROUPS, Role, has_role, role_required
from pyensemble.account_forms import AccountInvitationForm, AcceptAccountInvitationForm
from pyensemble.models import AccountInvitation, AccountInvitationDelivery
from pyensemble.tasks import send_email


logger = logging.getLogger(__name__)
INVITATION_LIFETIME = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(seconds=60)
HOURLY_SEND_LIMIT = 20


def invitation_origin():
    origin = settings.ACCOUNT_INVITATION_ORIGIN.rstrip('/')
    message = (
        'Configure ACCOUNT_INVITATION_ORIGIN as the trusted HTTPS origin '
        '(for example https://ensemble.example.org). HTTP localhost is '
        'allowed only with DEBUG enabled.'
    )
    try:
        parsed = urlsplit(origin)
        parsed.port
    except ValueError:
        raise ValidationError(message) from None
    local_http = (
        settings.DEBUG and parsed.scheme == 'http'
        and parsed.hostname in ('localhost', '127.0.0.1', '::1')
    )
    if (
        not parsed.netloc or not parsed.hostname
        or parsed.username or parsed.password
        or parsed.path or parsed.query or parsed.fragment
        or '\\' in origin or any(character.isspace() for character in origin)
        or (parsed.scheme != 'https' and not local_http)
    ):
        raise ValidationError(message)
    return origin


def issue_invitation(sender, email, role):
    origin = invitation_origin()
    now = timezone.now()
    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        # Serialize sends by an administrator, including the hourly limit.
        get_user_model().objects.select_for_update().get(pk=sender.pk)
        if AccountInvitationDelivery.objects.filter(
            sender=sender, attempted_at__gt=now - timedelta(hours=1),
        ).count() >= HOURLY_SEND_LIMIT:
            raise ValidationError('Invitation limit reached. Try again in an hour.')
        invitation, created = AccountInvitation.objects.get_or_create(
            email=email,
            defaults={
                'role': role, 'token_digest': '', 'issued_at': now,
                'expires_at': now + INVITATION_LIFETIME, 'invited_by': sender,
            },
        )
        invitation = AccountInvitation.objects.select_for_update().get(pk=invitation.pk)
        if (
            invitation.accepted_at
            or get_user_model().objects.filter(email__iexact=email).exists()
        ):
            raise ValidationError(
                'An account already uses this email address. '
                'Invitations cannot reset passwords or change existing roles.'
            )
        if not created and invitation.issued_at > now - RESEND_COOLDOWN:
            raise ValidationError('Wait at least 60 seconds before resending an invitation.')
        invitation.role = role
        invitation.token_digest = hashlib.sha256(token.encode('ascii')).hexdigest()
        invitation.invited_by = sender
        invitation.issued_at = now
        invitation.expires_at = now + INVITATION_LIFETIME
        invitation.sent_at = None
        invitation.revoked_at = None
        invitation.save()
        delivery = AccountInvitationDelivery.objects.create(invitation=invitation, sender=sender)

    link = origin + reverse('account-invitation-accept', args=[invitation.pk, token])
    try:
        num_sent = send_email('pyensemble/accounts/invitation_email.html', {
            'to_email': email,
            'msg_subject': 'Invitation to create a PyEnsemble account',
            'invitation_link': link,
            'role': ROLE_GROUPS[Role(role)],
            'expires_at': invitation.expires_at,
        })
    except (SMTPException, OSError):
        logger.error('Account invitation delivery failed (attempt %s).', delivery.pk)
        raise ValidationError(
            'The email could not be sent. Check email configuration and retry '
            'after 60 seconds. No account was created.'
        ) from None
    if num_sent != 1:
        logger.error('Account invitation email was not submitted (attempt %s).', delivery.pk)
        raise ValidationError('The email was not sent. Retry after 60 seconds.')
    sent_at = timezone.now()
    AccountInvitationDelivery.objects.filter(pk=delivery.pk).update(sent_at=sent_at)
    AccountInvitation.objects.filter(
        pk=invitation.pk, token_digest=invitation.token_digest,
    ).update(sent_at=sent_at)
    logger.info('Account invitation submitted (attempt %s).', delivery.pk)


@role_required(Role.ACCOUNT_ADMINISTRATOR)
@never_cache
@require_http_methods(['GET', 'POST'])
def invitations(request):
    form = AccountInvitationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            issue_invitation(request.user, form.cleaned_data['email'], form.cleaned_data['role'])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Invitation email submitted. The link expires in 24 hours.')
            return redirect('account-invitations')
    page = Paginator(
        AccountInvitation.objects.select_related('invited_by').order_by('-issued_at'), 25,
    ).get_page(request.GET.get('page'))
    return render(request, 'pyensemble/accounts/invitations.html', {'form': form, 'page': page})


@role_required(Role.ACCOUNT_ADMINISTRATOR)
@require_POST
def revoke_invitation(request, invitation_id):
    with transaction.atomic():
        invitation = get_object_or_404(
            AccountInvitation.objects.select_for_update(), pk=invitation_id,
        )
        if invitation.accepted_at:
            messages.error(request, 'This invitation was accepted. Revoke account access separately.')
        else:
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=['revoked_at'])
            logger.info('Account invitation %s revoked by user %s.', invitation.pk, request.user.pk)
            messages.success(request, 'Invitation revoked.')
    return redirect('account-invitations')


def usable_invitation(invitation, token):
    return (
        invitation is not None
        and len(token) == 43
        and constant_time_compare(
            invitation.token_digest, hashlib.sha256(token.encode('utf-8')).hexdigest(),
        )
        and invitation.sent_at is not None
        and invitation.accepted_at is None
        and invitation.revoked_at is None
        and invitation.expires_at > timezone.now()
        and invitation.invited_by is not None
        and has_role(invitation.invited_by, Role.ACCOUNT_ADMINISTRATOR)
    )


@sensitive_post_parameters('password1', 'password2')
@never_cache
@require_http_methods(['GET', 'POST'])
def accept_invitation(request, invitation_id, token):
    with transaction.atomic():
        invitation = (
            AccountInvitation.objects.select_for_update()
            .filter(pk=invitation_id).first()
        )
        if not usable_invitation(invitation, token):
            response = render(request, 'pyensemble/accounts/accept_invitation.html', status=400)
        else:
            form = AcceptAccountInvitationForm(
                request.POST if request.method == 'POST' else None,
            )
            # Include the verified address in password similarity validation.
            form.instance.email = invitation.email
            if request.method == 'POST' and form.is_valid():
                if get_user_model().objects.filter(email__iexact=invitation.email).exists():
                    form.add_error(None, 'An account already uses this address. Contact an administrator.')
                else:
                    try:
                        with transaction.atomic():
                            user = form.save(commit=False)
                            user.email = invitation.email
                            user.is_active = True
                            user.is_staff = False
                            user.is_superuser = False
                            user.save()
                            user.groups.add(Group.objects.get(name=ROLE_GROUPS[Role(invitation.role)]))
                            invitation.accepted_user = user
                            invitation.accepted_at = timezone.now()
                            invitation.save(update_fields=['accepted_user', 'accepted_at'])
                    except IntegrityError:
                        if not get_user_model().objects.filter(
                            username=form.cleaned_data['username'],
                        ).exists():
                            raise
                        logger.warning('Account creation conflict for invitation %s.', invitation.pk)
                        form.add_error(None, 'Account creation conflicted with another request. Try a different username.')
                    else:
                        logger.info('Account invitation %s accepted by user %s.', invitation.pk, user.pk)
                        response = render(request, 'pyensemble/accounts/accept_invitation.html', {
                            'created': True,
                        })
                        response['Referrer-Policy'] = 'same-origin'
                        response['X-Robots-Tag'] = 'noindex, nofollow'
                        return response
            response = render(request, 'pyensemble/accounts/accept_invitation.html', {
                'form': form, 'invitation': invitation,
            })
    response['Referrer-Policy'] = 'same-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
