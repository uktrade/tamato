"""Common views."""
import time
from datetime import datetime
from typing import Optional
from typing import Tuple
from typing import Type

import django.contrib.auth.views
import kombu.exceptions
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import OperationalError
from django.db import connection
from django.db import transaction
from django.db.models import Model
from django.db.models import QuerySet
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views import generic
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic.base import View
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView
from redis.exceptions import TimeoutError as RedisTimeoutError

from common import forms
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.celery import app
from common.models import TrackedModel
from common.pagination import build_pagination_list
from common.validators import UpdateType
from workbaskets.views.mixins import WithCurrentWorkBasket


class HomeView(FormView, View):
    template_name = "common/workbasket_action.jinja"
    form_class = forms.HomeForm

    def form_valid(self, form):
        if form.cleaned_data["workbasket_action"] == "EDIT":
            return redirect(reverse("workbaskets:workbasket-ui-list"))
        elif form.cleaned_data["workbasket_action"] == "CREATE":
            return redirect(reverse("workbaskets:workbasket-ui-create"))


class HealthCheckResponse(HttpResponse):
    """
    Formatted HTTP response for healthcheck.

    See https://readme.trade.gov.uk/docs/howtos/healthcheck.html
    """

    def __init__(self):
        super().__init__(content_type="text/xml")
        self["Cache-Control"] = "no-cache, no-store, must-revalidate"

        self.start_time = time.time()
        self.status = "OK"

    @property
    def content(self):
        return (
            "<pingdom_http_custom_check>"
            f"<status>{self.status}</status>"
            f"<response_time>{int(time.time() - self.start_time)}</response_time>"
            "</pingdom_http_custom_check>"
        )

    @content.setter
    def content(self, value):
        pass

    def fail(self, status):
        self.status_code = 503
        self.status = status
        return self


def healthcheck(request):
    """Healthcheck endpoint returns a 503 error if the database or redis is
    down."""
    response = HealthCheckResponse()

    try:
        connection.cursor()
    except OperationalError:
        return response.fail("DB missing")

    try:
        cache.set("__pingdom_test", 1, timeout=1)
    except RedisTimeoutError:
        return response.fail("Redis missing")

    return response


class AppInfoView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "common/app_info.jinja"

    def active_checks(self):
        results = []
        inspect = app.control.inspect()
        if not inspect:
            return results

        active_tasks = inspect.active()
        if not active_tasks:
            return results

        for _, task_info_list in active_tasks.items():
            for task_info in task_info_list:
                if (
                    task_info.get("name")
                    == "workbaskets.tasks.call_check_workbasket_sync"
                ):
                    date_time_start = make_aware(
                        datetime.fromtimestamp(
                            task_info.get("time_start"),
                        ),
                    ).strftime("%Y-%m-%d, %H:%M:%S")
                    results.append(
                        {
                            "task_id": task_info.get("id"),
                            "workbasket_id": task_info.get("args", [""])[0],
                            "date_time_start": date_time_start,
                        },
                    )

        return results

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        try:
            data["active_checks"] = self.active_checks()
            data["celery_healthy"] = True
        except kombu.exceptions.OperationalError as oe:
            data["celery_healthy"] = False

        return data


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"


class WithPaginationListView(FilterView):
    """Generic list view enabling pagination."""

    paginator_class = Paginator
    paginate_by = settings.REST_FRAMEWORK["PAGE_SIZE"]

    def get_context_data(self, *, object_list=None, **kwargs):
        """Adds a page link list to the context."""
        data = super().get_context_data(object_list=object_list, **kwargs)
        page_obj = data["page_obj"]
        page_number = page_obj.number
        data["page_links"] = build_pagination_list(
            page_number,
            page_obj.paginator.num_pages,
        )
        return data


class RequiresSuperuserMixin(UserPassesTestMixin):
    """Only allow superusers to see this view."""

    def test_func(self):
        return self.request.user.is_superuser


class TamatoListView(WithCurrentWorkBasket, WithPaginationListView):
    """Base view class for listing tariff components including those in the
    current workbasket, with pagination."""


class TrackedModelDetailMixin:
    """Allows detail URLs to use <Identifying-Fields> instead of <pk>"""

    model: Type[TrackedModel]
    required_url_kwargs = None

    def get_object(self, queryset: Optional[QuerySet] = None) -> Model:
        """
        Fetch the model instance by primary key or by identifying_fields in the
        URL.

        :param queryset Optional[QuerySet]: Get the object from this queryset
        :rtype: Model
        """
        if queryset is None:
            queryset = self.get_queryset()

        required_url_kwargs = self.required_url_kwargs or self.model.identifying_fields

        if any(key not in self.kwargs for key in required_url_kwargs):
            raise AttributeError(
                f"{self.__class__.__name__} must be called with {', '.join(required_url_kwargs)} in the URLconf.",
            )

        queryset = queryset.filter(**self.kwargs)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No {self.model.__name__} matching the query {self.kwargs}")

        return obj


class TrackedModelDetailView(
    WithCurrentWorkBasket,
    TrackedModelDetailMixin,
    generic.DetailView,
):
    """Base view class for displaying a single TrackedModel."""


class BusinessRulesMixin:
    """Check business rules on form_submission."""

    validate_business_rules: Tuple[Type[BusinessRule], ...] = tuple()

    def form_violates(self, form) -> bool:
        """
        If any of the specified business rules are violated, reshow the form
        with the violations as form errors.

        :param form: The submitted form
        """
        violations = False
        transaction = self.object.transaction

        for rule in self.validate_business_rules:
            try:
                rule(transaction).validate(self.object)
            except BusinessRuleViolation as v:
                form.add_error(None, v.args[0])
                violations = True

        return violations

    def form_valid(self, form):
        if self.form_violates(form):
            return self.form_invalid(form)

        return super().form_valid(form)


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


def handler403(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/403.jinja", status=403)


def handler500(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/500.jinja", status=500)
