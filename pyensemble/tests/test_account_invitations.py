import hashlib
import re
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from pyensemble.access import ROLE_GROUPS, Role, has_role
from pyensemble.models import AccountInvitation, AccountInvitationDelivery


PASSWORD = 'An-unusual-account-password-739!'


class AccountInvitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = get_user_model().objects.create_user(
            'administrator', 'administrator@example.com', PASSWORD,
        )
        cls.administrator.groups.add(Group.objects.get(name='Account administrator'))

    def setUp(self):
        self.client.force_login(self.administrator)

    def invite(self, email='new@example.com', role=Role.EDITOR):
        return self.client.post(reverse('account-invitations'), {
            'email': email, 'role': role.value,
        })

    def acceptance_path(self):
        link = re.search(
            r'https://testserver/accounts/accept/\d+/[A-Za-z0-9_-]+/',
            mail.outbox[-1].body,
        ).group()
        return urlsplit(link).path

    def acceptance_data(self, username='new-user'):
        return {'username': username, 'password1': PASSWORD, 'password2': PASSWORD}

    def age_invitation(self):
        AccountInvitation.objects.update(issued_at=timezone.now() - timedelta(minutes=2))

    def test_invitation_records_only_token_digest_and_sends_email(self):
        response = self.invite(email='New@Example.COM')
        self.assertRedirects(response, reverse('account-invitations'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        invitation = AccountInvitation.objects.get()
        token = self.acceptance_path().rstrip('/').split('/')[-1]
        self.assertEqual(
            invitation.token_digest, hashlib.sha256(token.encode('ascii')).hexdigest(),
        )
        self.assertNotEqual(invitation.token_digest, token)
        self.assertEqual(invitation.invited_by, self.administrator)
        self.assertEqual(invitation.expires_at - invitation.issued_at, timedelta(hours=24))
        self.assertIsNotNone(invitation.sent_at)
        self.assertFalse(get_user_model().objects.filter(email='new@example.com').exists())
        self.assertIsNotNone(AccountInvitationDelivery.objects.get().sent_at)

    def test_acceptance_page_is_read_only_and_not_cacheable(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        response = self.client.get(path)
        self.assertContains(response, 'new@example.com')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
        invitation = AccountInvitation.objects.get()
        self.assertIsNone(invitation.accepted_at)
        self.assertFalse(get_user_model().objects.filter(username='new-user').exists())

    def test_each_invited_role_is_verified_and_inherits_access(self):
        for role in Role:
            with self.subTest(role=role):
                self.client.force_login(self.administrator)
                self.invite(email=f'role{role.value}@example.com', role=role)
                path = self.acceptance_path()
                self.client.logout()
                response = self.client.post(path, self.acceptance_data(f'role{role.value}'))
                self.assertContains(response, 'email address was verified')
                user = get_user_model().objects.get(username=f'role{role.value}')
                self.assertTrue(user.check_password(PASSWORD))
                self.assertTrue(user.is_active)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertEqual(list(user.groups.values_list('name', flat=True)), [ROLE_GROUPS[role]])
                self.assertTrue(has_role(user, role))
                self.assertTrue(has_role(user, Role.EDITOR))
                invitation = AccountInvitation.objects.get(email=f'role{role.value}@example.com')
                self.assertEqual(invitation.accepted_user, user)
                self.assertIsNotNone(invitation.accepted_at)
                self.assertNotIn('_auth_user_id', self.client.session)
                response = self.client.post(reverse('login'), {
                    'username': user.username, 'password': PASSWORD,
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.client.get('/').status_code, 200)

    def test_acceptance_does_not_trust_posted_email_role_or_admin_flags(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        data = self.acceptance_data()
        data.update(email='attacker@example.com', role=3, is_staff=True, is_superuser=True)
        self.assertEqual(self.client.post(path, data).status_code, 200)
        user = get_user_model().objects.get(username='new-user')
        self.assertEqual(user.email, 'new@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(has_role(user, Role.RELEASE_MANAGER))

    def test_token_is_single_use(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        self.client.post(path, self.acceptance_data())
        self.assertEqual(self.client.get(path).status_code, 400)
        self.assertEqual(
            self.client.post(path, self.acceptance_data('second-user')).status_code, 400,
        )
        self.assertFalse(get_user_model().objects.filter(username='second-user').exists())

    def test_expired_revoked_wrong_and_missing_tokens_cannot_create_accounts(self):
        self.invite()
        path = self.acceptance_path()
        invitation = AccountInvitation.objects.get()
        self.client.logout()
        for field, value in (
            ('expires_at', timezone.now()),
            ('revoked_at', timezone.now()),
            ('sent_at', None),
        ):
            with self.subTest(field=field):
                original = getattr(invitation, field)
                AccountInvitation.objects.filter(pk=invitation.pk).update(**{field: value})
                self.assertEqual(self.client.post(path, self.acceptance_data()).status_code, 400)
                AccountInvitation.objects.filter(pk=invitation.pk).update(**{field: original})
        for invalid_path in (
            reverse('account-invitation-accept', args=[invitation.pk, 'x' * 43]),
            reverse('account-invitation-accept', args=[invitation.pk, 'short']),
            reverse('account-invitation-accept', args=[999999, 'x' * 43]),
        ):
            self.assertEqual(self.client.post(invalid_path, self.acceptance_data()).status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='new-user').exists())

    def test_deactivated_or_demoted_inviter_invalidates_pending_links(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        self.administrator.is_active = False
        self.administrator.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(path).status_code, 400)
        self.administrator.is_active = True
        self.administrator.save(update_fields=['is_active'])
        self.administrator.groups.clear()
        self.assertEqual(self.client.get(path).status_code, 400)

    def test_password_validation_and_username_conflict_do_not_consume_token(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        for data in (
            {'username': 'new-user', 'password1': '123', 'password2': '123'},
            {'username': 'new-user', 'password1': PASSWORD, 'password2': 'mismatch'},
            self.acceptance_data('administrator'),
            self.acceptance_data('invalid username'),
        ):
            response = self.client.post(path, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertIsNone(AccountInvitation.objects.get().accepted_at)
        self.assertEqual(self.client.post(path, self.acceptance_data()).status_code, 200)
        self.assertTrue(get_user_model().objects.filter(username='new-user').exists())

    def test_existing_account_email_is_never_overwritten_or_given_a_new_role(self):
        existing = get_user_model().objects.create_user('existing', 'New@Example.com', PASSWORD)
        response = self.invite()
        self.assertContains(response, 'An account already uses this email')
        self.assertFalse(AccountInvitation.objects.exists())
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(existing.groups.exists())

    def test_account_created_after_invitation_blocks_acceptance(self):
        self.invite()
        path = self.acceptance_path()
        get_user_model().objects.create_user('existing', 'new@example.com', PASSWORD)
        self.client.logout()
        response = self.client.post(path, self.acceptance_data())
        self.assertContains(response, 'An account already uses this address')
        self.assertIsNone(AccountInvitation.objects.get().accepted_at)
        self.assertFalse(get_user_model().objects.filter(username='new-user').exists())

    def test_resending_rotates_token_and_role(self):
        self.invite()
        old_path = self.acceptance_path()
        self.age_invitation()
        self.invite(role=Role.RELEASE_MANAGER)
        new_path = self.acceptance_path()
        self.assertNotEqual(old_path, new_path)
        self.assertEqual(AccountInvitation.objects.count(), 1)
        self.assertEqual(AccountInvitationDelivery.objects.count(), 2)
        self.client.logout()
        self.assertEqual(self.client.get(old_path).status_code, 400)
        self.client.post(new_path, self.acceptance_data())
        self.assertTrue(has_role(
            get_user_model().objects.get(username='new-user'), Role.RELEASE_MANAGER,
        ))

    def test_resend_cooldown_preserves_existing_link(self):
        self.invite()
        path = self.acceptance_path()
        response = self.invite()
        self.assertContains(response, 'Wait at least 60 seconds')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AccountInvitationDelivery.objects.count(), 1)
        self.client.logout()
        self.assertEqual(self.client.get(path).status_code, 200)

    def test_hourly_limit_counts_attempts_not_only_successful_deliveries(self):
        self.invite()
        invitation = AccountInvitation.objects.get()
        AccountInvitationDelivery.objects.bulk_create([
            AccountInvitationDelivery(invitation=invitation, sender=self.administrator)
            for _ in range(19)
        ])
        response = self.invite(email='another@example.com')
        self.assertContains(response, 'Invitation limit reached')
        self.assertEqual(len(mail.outbox), 1)

    def test_revoke_requires_post_and_blocks_acceptance(self):
        self.invite()
        path = self.acceptance_path()
        revoke_url = reverse('account-invitation-revoke', args=[AccountInvitation.objects.get().pk])
        self.assertEqual(self.client.get(revoke_url).status_code, 405)
        self.assertEqual(self.client.post(revoke_url).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.post(path, self.acceptance_data()).status_code, 400)
        self.client.force_login(self.administrator)
        self.age_invitation()
        self.invite()
        self.assertIsNone(AccountInvitation.objects.get().revoked_at)

    def test_accepted_invitation_cannot_be_resent_or_used_to_revoke_account(self):
        self.invite()
        path = self.acceptance_path()
        self.client.logout()
        self.client.post(path, self.acceptance_data())
        self.client.force_login(self.administrator)
        self.age_invitation()
        self.assertContains(self.invite(), 'An account already uses this email')
        invitation = AccountInvitation.objects.get()
        response = self.client.post(
            reverse('account-invitation-revoke', args=[invitation.pk]), follow=True,
        )
        self.assertContains(response, 'Revoke account access separately')
        self.assertTrue(get_user_model().objects.get(username='new-user').is_active)

    def test_lower_roles_cannot_manage_invitations(self):
        for role in (Role.EDITOR, Role.RELEASE_MANAGER):
            user = get_user_model().objects.create_user(f'role{role.value}')
            user.groups.add(Group.objects.get(name=ROLE_GROUPS[role]))
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('account-invitations')).status_code, 403)
            self.assertEqual(self.invite().status_code, 403)
        self.assertFalse(AccountInvitation.objects.exists())
        self.client.logout()
        self.assertEqual(self.invite().status_code, 302)

    def test_superuser_can_invite_without_group_membership(self):
        user = get_user_model().objects.create_superuser(
            'superuser', 'superuser@example.com', PASSWORD,
        )
        self.client.force_login(user)
        self.assertEqual(self.invite(role=Role.ACCOUNT_ADMINISTRATOR).status_code, 302)
        self.assertEqual(AccountInvitation.objects.get().invited_by, user)

    def test_other_administrator_can_revoke_and_replace_an_invitation(self):
        self.invite()
        old_path = self.acceptance_path()
        user = get_user_model().objects.create_user('another-administrator')
        user.groups.add(Group.objects.get(name='Account administrator'))
        self.client.force_login(user)
        invitation = AccountInvitation.objects.get()
        self.assertEqual(self.client.post(
            reverse('account-invitation-revoke', args=[invitation.pk]),
        ).status_code, 302)
        self.age_invitation()
        self.invite()
        invitation.refresh_from_db()
        self.assertEqual(invitation.invited_by, user)
        self.assertEqual(self.client.get(old_path).status_code, 400)

    def test_only_account_administrators_see_management_link(self):
        self.assertContains(self.client.get('/'), 'Account invitations')
        self.administrator.groups.clear()
        self.administrator.groups.add(Group.objects.get(name='Editor'))
        self.assertNotContains(self.client.get('/'), 'Account invitations')

    @override_settings(ACCOUNT_INVITATION_ORIGIN='https://trusted.example.org')
    def test_email_link_uses_configured_origin_not_request_host(self):
        self.invite()
        self.assertIn('https://trusted.example.org/accounts/accept/', mail.outbox[-1].body)
        self.assertNotIn('https://testserver/', mail.outbox[-1].body)

    def test_missing_or_unsafe_origin_blocks_send_explicitly(self):
        for origin in (
            '', 'http://example.org', 'https://user:password@example.org',
            'https://example.org/path', 'https://example.org?query=1',
            'https://[invalid', 'https://example.org:invalid', 'https://example.org\n',
        ):
            with self.subTest(origin=origin), override_settings(ACCOUNT_INVITATION_ORIGIN=origin):
                self.assertContains(self.invite(), 'Configure ACCOUNT_INVITATION_ORIGIN')
        self.assertFalse(AccountInvitation.objects.exists())

    @override_settings(DEBUG=True, ACCOUNT_INVITATION_ORIGIN='http://localhost:8000')
    def test_development_allows_local_http_origin(self):
        self.assertEqual(self.invite().status_code, 302)
        self.assertIn('http://localhost:8000/accounts/accept/', mail.outbox[-1].body)

    @patch('pyensemble.accounts.send_email', side_effect=SMTPException('sensitive server detail'))
    def test_smtp_failure_is_visible_and_retryable_without_creating_account(self, send):
        with self.assertLogs('pyensemble.accounts', level='ERROR') as logs:
            response = self.invite()
        self.assertContains(response, 'The email could not be sent')
        self.assertNotContains(response, 'sensitive server detail')
        self.assertNotIn('sensitive server detail', '\n'.join(logs.output))
        self.assertIsNone(AccountInvitation.objects.get().sent_at)
        self.assertIsNone(AccountInvitationDelivery.objects.get().sent_at)
        self.assertFalse(get_user_model().objects.filter(email='new@example.com').exists())
        self.age_invitation()
        send.side_effect = None
        send.return_value = 1
        self.assertEqual(self.invite().status_code, 302)
        self.assertIsNotNone(AccountInvitation.objects.get().sent_at)

    @patch('pyensemble.accounts.send_email', return_value=0)
    def test_zero_email_submission_is_not_success(self, send):
        with self.assertLogs('pyensemble.accounts', level='ERROR'):
            response = self.invite()
        self.assertContains(response, 'The email was not sent')
        self.assertIsNone(AccountInvitation.objects.get().sent_at)

    def test_invalid_email_and_role_are_rejected_without_sending(self):
        for data in (
            {'email': 'invalid', 'role': '1'},
            {'email': 'new@example.com', 'role': '999'},
        ):
            response = self.client.post(reverse('account-invitations'), data)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(AccountInvitation.objects.exists())

    def test_management_and_acceptance_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.administrator)
        self.assertEqual(client.post(reverse('account-invitations'), {
            'email': 'new@example.com', 'role': '1',
        }).status_code, 403)
        self.invite()
        path = self.acceptance_path()
        self.assertEqual(client.post(
            reverse('account-invitation-revoke', args=[AccountInvitation.objects.get().pk]),
        ).status_code, 403)
        client.logout()
        self.assertEqual(client.post(path, self.acceptance_data()).status_code, 403)
        self.assertEqual(client.get(path).status_code, 200)
        token = client.cookies['csrftoken'].value
        data = self.acceptance_data()
        data['csrfmiddlewaretoken'] = token
        self.assertContains(client.post(path, data), 'email address was verified')

    def test_acceptance_preserves_same_origin_csrf_checks(self):
        self.invite()
        path = self.acceptance_path()
        client = Client(enforce_csrf_checks=True)
        response = client.get(path, secure=True)
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        data = self.acceptance_data()
        data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        for origin in ('null', 'https://untrusted.example.org'):
            with self.subTest(origin=origin):
                self.assertEqual(client.post(
                    path, data, secure=True, HTTP_ORIGIN=origin,
                ).status_code, 403)
                self.assertIsNone(AccountInvitation.objects.get().accepted_at)
        self.assertContains(client.post(
            path, data, secure=True, HTTP_ORIGIN='https://testserver',
        ), 'email address was verified')
