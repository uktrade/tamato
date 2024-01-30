from django.contrib import admin
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()


class UserCreationForm(auth_forms.UserCreationForm):
    class Meta(auth_forms.UserCreationForm.Meta):
        model = User
        fields = auth_forms.UserCreationForm.Meta.fields


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta(auth_forms.UserChangeForm.Meta):
        model = User
        fields = auth_forms.UserCreationForm.Meta.fields


class UserAdmin(UserAdmin):
    model = User
    form = UserChangeForm
    add_form = UserCreationForm
    readonly_fields = ("current_workbasket",)
    fieldsets = UserAdmin.fieldsets + (
        ("Workbasket", {"fields": ("current_workbasket",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets


admin.site.register(User, UserAdmin)
