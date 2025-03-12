from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.decorators import method_decorator
from django.views import generic

from common.validators import UpdateType
from common.views import TrackedModelCopyView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import forms
from measures import models
from workbaskets.views.decorators import require_current_workbasket

from .mixins import MeasureMixin


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureCopy(
    MeasureMixin,
    TrackedModelCopyView,
    TrackedModelDetailMixin,
    generic.UpdateView,
):
    form_class = forms.MeasureCopyForm
    update_type = UpdateType.CREATE
    permission_required = "common.change_trackedmodel"
    template_name = "measures/copy.jinja"
    success_path = "confirm-copy"


@method_decorator(require_current_workbasket, name="dispatch")
class MeasureConfirmCopy(MeasureMixin, PermissionRequiredMixin, TrackedModelDetailView):
    permission_required = "common.change_trackedmodel"
    queryset = models.Measure.objects.all()
    template_name = "common/confirm_create.jinja"
