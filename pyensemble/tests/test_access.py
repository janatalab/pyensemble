from importlib import import_module

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import URLResolver, get_resolver, resolve, reverse

from pyensemble.access import (
    ROLE_GROUPS, Role, has_role, participant_view, role_required,
)
from pyensemble.middleware import InterfaceAccessMiddleware
from pyensemble.models import Experiment, Form, FormXQuestion, ExperimentXForm, Question


def endpoint(request):
    return HttpResponse('ok')


class InterfaceAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.unassigned = user_model.objects.create_user('unassigned', password='password')
        cls.users = {}
        for role, name in ROLE_GROUPS.items():
            user = user_model.objects.create_user(name, password='password')
            user.groups.add(Group.objects.get(name=name))
            cls.users[role] = user
        cls.superuser = user_model.objects.create_superuser(
            'superuser', 'superuser@example.com', 'password',
        )

    def setUp(self):
        self.middleware = InterfaceAccessMiddleware(endpoint)
        self.factory = RequestFactory()

    def request_for(self, path, user):
        request = self.factory.get(path)
        request.user = user
        request.resolver_match = resolve(path)
        return request

    def test_role_hierarchy(self):
        for actual_role, user in self.users.items():
            for minimum_role in Role:
                with self.subTest(actual=actual_role, minimum=minimum_role):
                    self.assertEqual(
                        has_role(user, minimum_role), actual_role >= minimum_role,
                    )

    def test_unassigned_anonymous_and_inactive_accounts_have_no_role(self):
        for user in (self.unassigned, AnonymousUser()):
            for role in Role:
                self.assertFalse(has_role(user, role))
        for user in (*self.users.values(), self.superuser):
            user.is_active = False
            for role in Role:
                self.assertFalse(has_role(user, role))

    def test_staff_flag_does_not_grant_a_role(self):
        self.unassigned.is_staff = True
        self.assertFalse(has_role(self.unassigned, Role.EDITOR))

    def test_active_superuser_has_all_roles(self):
        for role in Role:
            self.assertTrue(has_role(self.superuser, role))

    def test_membership_changes_take_effect_without_a_new_login(self):
        self.client.force_login(self.unassigned)
        self.assertEqual(self.client.get('/').status_code, 403)
        group = Group.objects.get(name='Editor')
        self.unassigned.groups.add(group)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.unassigned.groups.remove(group)
        self.assertEqual(self.client.get('/').status_code, 403)

    def test_suspension_blocks_existing_session(self):
        user = self.users[Role.EDITOR]
        self.client.force_login(user)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertRedirects(
            self.client.get('/'), '/accounts/login/?next=/', fetch_redirect_response=False,
        )

    def test_all_resolved_routes_obey_policy(self):
        seen_public = set()

        def visit(patterns, prefix=''):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    namespace = f'{pattern.namespace}:' if pattern.namespace else ''
                    visit(pattern.url_patterns, prefix + namespace)
                    continue
                if pattern.name is None:
                    continue
                name = prefix + pattern.name
                kwargs = {
                    key: 'auth' if key == 'app_label' else 'test'
                    for key in pattern.pattern.regex.groupindex
                }
                kwargs.update({
                    key: 1 if converter.__class__.__name__ == 'IntConverter' else 'test'
                    for key, converter in pattern.pattern.converters.items()
                })
                path = reverse(name, kwargs=kwargs)
                match = resolve(path)
                public = name in self.middleware.public_views
                if public:
                    seen_public.add(name)
                minimum_role = (
                    Role.ACCOUNT_ADMINISTRATOR if 'admin' in match.app_names
                    else getattr(match.func, 'required_role', Role.EDITOR)
                )
                for user in (AnonymousUser(), self.unassigned, *self.users.values()):
                    with self.subTest(route=name, user=str(user)):
                        request = self.request_for(path, user)
                        allowed = public or has_role(user, minimum_role)
                        if allowed:
                            self.assertIsNone(self.middleware.process_view(
                                request, match.func, (), kwargs,
                            ))
                        elif not user.is_authenticated:
                            response = self.middleware.process_view(
                                request, match.func, (), kwargs,
                            )
                            self.assertEqual(response.status_code, 302)
                            self.assertTrue(response.url.startswith('/accounts/login/?next='))
                        else:
                            with self.assertRaises(PermissionDenied):
                                self.middleware.process_view(request, match.func, (), kwargs)

        visit(get_resolver().url_patterns)
        self.assertEqual(seen_public, self.middleware.public_views)

    def test_new_unclassified_endpoint_is_protected(self):
        request = self.request_for('/', self.unassigned)
        with self.assertRaises(PermissionDenied):
            self.middleware.process_view(request, endpoint, (), {})

    def test_custom_participant_endpoint_can_be_explicitly_public(self):
        request = self.request_for('/', AnonymousUser())
        public_endpoint = participant_view(lambda request: HttpResponse('participant'))
        self.assertIsNone(self.middleware.process_view(request, public_endpoint, (), {}))

    def test_required_role_decorator_and_middleware_agree(self):
        view = role_required(Role.RELEASE_MANAGER)(endpoint)
        for role, user in self.users.items():
            request = self.request_for('/', user)
            if role >= Role.RELEASE_MANAGER:
                self.assertIsNone(self.middleware.process_view(request, view, (), {}))
                self.assertEqual(view(request).status_code, 200)
            else:
                with self.assertRaises(PermissionDenied):
                    self.middleware.process_view(request, view, (), {})
                with self.assertRaises(PermissionDenied):
                    view(request)
        request = self.request_for('/', AnonymousUser())
        self.assertEqual(view(request).status_code, 302)

    def test_real_interface_requests_require_explicit_role(self):
        paths = [
            '/', '/editor/', '/stimulus/', '/reporting/', '/import/',
            '/import/json/', '/integrations/spotify/search/',
            '/export/experiment/1/', '/integrity/verify_response_form_question_match/',
            '/group/session/exclude/', '/group/session/exit_loop/',
        ]
        for path in paths:
            with self.subTest(path=path, user='anonymous'):
                self.assertEqual(self.client.get(path).status_code, 302)
        self.client.force_login(self.unassigned)
        for path in paths:
            with self.subTest(path=path, user='unassigned'):
                self.assertContains(self.client.get(path), 'Access denied', status_code=403)
                self.assertEqual(self.client.post(path).status_code, 403)

    def test_each_role_can_use_editor_importer_and_integration_interfaces(self):
        for user in (*self.users.values(), self.superuser):
            self.client.force_login(user)
            for path in ('/', '/editor/', '/stimulus/', '/import/',
                         '/integrations/spotify/search/'):
                with self.subTest(user=str(user), path=path):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_admin_requires_account_administrator_and_django_admin_privileges(self):
        for role in (Role.EDITOR, Role.RELEASE_MANAGER):
            user = self.users[role]
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            self.client.force_login(user)
            self.assertEqual(self.client.get('/admin/').status_code, 403)
        user = self.users[Role.ACCOUNT_ADMINISTRATOR]
        self.client.force_login(user)
        # Role membership does not silently grant Django staff/model permissions.
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_anonymous_participant_registration_and_verification_still_work(self):
        self.assertEqual(self.client.get('/register/participant/').status_code, 200)
        self.assertEqual(self.client.get('/verify-email/missing/invalid/').status_code, 200)
        self.assertEqual(
            self.client.get('/group/session/attach/participant/').status_code, 200,
        )
        response = self.client.post('/record/timezone', {'timezone': 'UTC'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['timezone'], 'UTC')

    def test_participant_start_retains_ticket_validation_without_an_editor_role(self):
        experiment = Experiment.objects.create(title='Participant experiment')
        path = reverse('run_experiment', args=[experiment.pk])
        for user in (None, self.unassigned):
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for params in ({}, {'tc': 'invalid-ticket'}):
                with self.subTest(user=str(user), params=params):
                    self.assertContains(
                        self.client.get(path, params), 'Ticket Error', status_code=400,
                    )

    def test_denied_relationship_writes_do_not_modify_definitions(self):
        experiment = Experiment.objects.create(title='Test')
        form = Form.objects.create(name='Test form')
        for user in (None, self.unassigned):
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for path, body in (
                (f'/editor/forms/add/{experiment.pk}/', '["Test form"]'),
                (f'/editor/questions/add/{form.pk}/', '["Test question"]'),
            ):
                response = self.client.post(path, body, content_type='application/json')
                self.assertEqual(response.status_code, 302 if user is None else 403)
        self.assertFalse(ExperimentXForm.objects.exists())
        self.assertFalse(FormXQuestion.objects.exists())
        self.assertFalse(Question.objects.exists())

    def test_editor_can_still_add_an_experiment_form(self):
        experiment = Experiment.objects.create(title='Test')
        form = Form.objects.create(name='Test form')
        self.client.force_login(self.users[Role.EDITOR])
        response = self.client.post(
            f'/editor/forms/add/{experiment.pk}/', '["Test form"]',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ExperimentXForm.objects.filter(
            experiment=experiment, form=form,
        ).exists())

    def test_logout_requires_csrf_protected_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users[Role.EDITOR])
        self.assertEqual(client.get(reverse('logout')).status_code, 405)
        self.assertEqual(client.post(reverse('logout')).status_code, 403)
        response = client.get('/')
        self.assertContains(response, 'method="post" action="/accounts/logout/"')
        token = client.cookies['csrftoken'].value
        self.assertEqual(
            client.post(reverse('logout'), {'csrfmiddlewaretoken': token}).status_code,
            302,
        )
        self.assertNotIn('_auth_user_id', client.session)

    def test_role_migration_is_idempotent_and_does_not_assign_users(self):
        from django.apps import apps
        from django.db import connection

        migration = import_module('pyensemble.migrations.0027_interface_roles')
        editor = connection.schema_editor()
        migration.create_roles(apps, editor)
        migration.create_roles(apps, editor)
        self.assertEqual(Group.objects.filter(name__in=ROLE_GROUPS.values()).count(), 3)
        self.assertFalse(self.unassigned.groups.exists())
