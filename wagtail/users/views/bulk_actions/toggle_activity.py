from django import forms
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from wagtail.core import hooks
from wagtail.users.views.bulk_actions.user_bulk_action import UserBulkAction
from wagtail.users.views.users import change_user_perm


class ActivityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mark_as_active'] = forms.BooleanField(
            required=False
        )
        self.fields['apply_on_applicable'] = forms.BooleanField(
            required=False
        )


class ToggleActivityBulkAction(UserBulkAction):
    display_name = _("Toggle activity")
    action_type = "toggle_activity"
    aria_label = _("Mark users as active or inactive")
    template_name = "wagtailusers/bulk_actions/confirm_bulk_toggle_activity.html"
    action_priority = 20
    form_class = ActivityForm

    def check_perm(self, obj):
        return self.request.user.has_perm(change_user_perm)

    def get_execution_context(self):
        return {
            'mark_as_active': self.cleaned_form.cleaned_data['mark_as_active'],
            'user': self.request.user
        }

    def prepare_action(self, objects):
        if self.cleaned_form.cleaned_data['apply_on_applicable']:
            return
        if not self.request.user.is_superuser:
            return
        if not self.cleaned_form.cleaned_data['mark_as_active']:
            for user in objects:
                if user == self.request.user:
                    context = self.get_context_data()
                    context['users'] = list(filter(lambda x: x['user'].pk != user.pk, context['users']))
                    context['mark_self_as_inactive'] = [user]
                    return TemplateResponse(self.request, self.template_name, context)

    @classmethod
    def execute_action(cls, objects, **kwargs):
        cls.mark_as_active = kwargs.get('mark_as_active', False)
        user = kwargs.get('user', None)
        if user is not None:
            objects = list(filter(lambda x: x.pk != user.pk, objects))
        for user in objects:
            user.is_active = cls.mark_as_active
            user.save()
            cls.num_parent_objects += 1

    def get_success_message(self):
        activity_status = "active" if self.mark_as_active else "inactive"
        return ngettext(
            "%(num_parent_objects)d user has been marked as %(activity_status)s",
            "%(num_parent_objects)d users have been marked as %(activity_status)s",
            self.num_parent_objects
        ) % {
            'num_parent_objects': self.num_parent_objects,
            'activity_status': activity_status
        }


@hooks.register('register_user_bulk_action')
def toggle_activity(request):
    return ToggleActivityBulkAction(request)
