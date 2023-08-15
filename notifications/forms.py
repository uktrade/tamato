from django import forms

from notifications.models import NotifiedUser


class NotifiedUserAdminForm(forms.ModelForm):
    class Meta:
        model = NotifiedUser
        fields = [
            "email",
            "enrol_packaging",
            "enrol_api_publishing",
            "enrol_goods_report",
        ]
