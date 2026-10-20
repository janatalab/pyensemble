"""Application roles and access checks, independent of Django admin privileges."""

from enum import IntEnum
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class Role(IntEnum):
    EDITOR = 1
    RELEASE_MANAGER = 2
    ACCOUNT_ADMINISTRATOR = 3


ROLE_GROUPS = {
    Role.EDITOR: 'Editor',
    Role.RELEASE_MANAGER: 'Release manager',
    Role.ACCOUNT_ADMINISTRATOR: 'Account administrator',
}


def has_role(user, minimum_role):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    eligible_groups = [
        name for role, name in ROLE_GROUPS.items() if role >= minimum_role
    ]
    return user.groups.filter(name__in=eligible_groups).exists()


def check_access(request, minimum_role):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not has_role(request.user, minimum_role):
        raise PermissionDenied(
            f'{ROLE_GROUPS[minimum_role]} access is required. '
            'Contact an account administrator.'
        )
    return None


def role_required(minimum_role):
    """Require a role even when the view is called outside the URL middleware."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            denial = check_access(request, minimum_role)
            if denial is not None:
                return denial
            return view(request, *args, **kwargs)

        wrapped.required_role = minimum_role
        return wrapped
    return decorator


def participant_view(view):
    """Explicitly allow an experiment-specific participant endpoint."""
    view.participant_access = True
    return view
