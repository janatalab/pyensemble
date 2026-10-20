# middleware.py
#
# PyEnsemble middleware

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from pyensemble.access import Role, check_access


class InterfaceAccessMiddleware(MiddlewareMixin):
    public_views = frozenset({
        'login',
        'logout',
        'register-participant',
        'register_with_group',
        'verify_email',
        'run_experiment',
        'serve_form',
        'reset_session',
        'flush_session_cache',
        'feature_not_enabled',
        'record-timezone',
        'pyensemble-group:attach_participant',
        'pyensemble-group:groupuser_state',
        'pyensemble-group:wait_groupuser_state',
        'pyensemble-group:groupuser_exitloop',
        'pyensemble-group:group_trial_status',
        'pyensemble-group:set_client_ready',
    })

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if 'admin' in match.app_names:
            minimum_role = Role.ACCOUNT_ADMINISTRATOR
        elif (
            match.view_name in self.public_views
            or getattr(view_func, 'participant_access', False)
        ):
            return None
        else:
            minimum_role = getattr(view_func, 'required_role', Role.EDITOR)
        return check_access(request, minimum_role)


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.session.get('timezone')
        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()
        return self.get_response(request)