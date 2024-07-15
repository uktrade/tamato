from typing import Optional

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.template.response import TemplateResponse
from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView

from common.validators import UpdateType
from common.views.mixins import BusinessRulesMixin
from common.views.mixins import TrackedModelDetailMixin
from common.views.mixins import WithPaginationListMixin
from workbaskets.views.mixins import WithCurrentWorkBasket


def handler403(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/403.jinja", status=403)


def handler500(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/500.jinja", status=500)


class WithPaginationListView(WithPaginationListMixin, FilterView):
    """Generic filtered list view enabling pagination."""


class TamatoListView(WithCurrentWorkBasket, WithPaginationListView):
    """Base view class for listing tariff components including those in the
    current workbasket, with pagination."""


class TrackedModelDetailView(
    WithCurrentWorkBasket,
    TrackedModelDetailMixin,
    DetailView,
):
    """Base view class for displaying a single TrackedModel."""


class TrackedModelChangeView(
    WithCurrentWorkBasket,
    PermissionRequiredMixin,
    BusinessRulesMixin,
):
    update_type: UpdateType
    success_path: Optional[str] = None

    @property
    def success_url(self):
        return self.object.get_url(self.success_path)

    def get_result_object(self, form):
        """
        Overridable used to get a saved result.

        In the default case (this implementation) a new version of a
        TrackedModel instance is created. However, this function may be
        overridden to provide alternative behaviour, such as simply updating the
        TrackedModel instance.
        """
        # compares changed data against model fields to prevent unexpected kwarg TypeError
        # e.g. `geographical_area_group` is a field on `MeasureUpdateForm` and included in cleaned data,
        # but isn't a field on `Measure` and would cause a TypeError on model save()
        model_fields = [f.name for f in self.model._meta.get_fields()]
        form_changed_data = [f for f in form.changed_data if f in model_fields]
        changed_data = {name: form.cleaned_data[name] for name in form_changed_data}

        return form.instance.new_version(
            workbasket=self.workbasket,
            update_type=self.update_type,
            **changed_data,
        )

    @transaction.atomic
    def form_valid(self, form):
        self.object = self.get_result_object(form)
        violations = self.form_violates(form)

        if violations:
            transaction.set_rollback(True)
            return self.form_invalid(form)

        return FormMixin.form_valid(self, form)
