from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from pyensemble.access import ROLE_GROUPS


class AccountInvitationForm(forms.Form):
    email = forms.EmailField(max_length=254)
    role = forms.TypedChoiceField(
        choices=[(role.value, name) for role, name in ROLE_GROUPS.items()],
        coerce=int,
        initial=1,
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class AcceptAccountInvitationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username',)
