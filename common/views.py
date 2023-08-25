"""Common views."""
import os
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
from common.models import Transaction
from common.pagination import build_pagination_list
from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.views.mixins import WithCurrentWorkBasket


class HomeView(FormView, View):
    template_name = "common/workbasket_action.jinja"
    form_class = forms.HomeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["workbasket_action"] == "EDIT":
            return redirect(reverse("workbaskets:workbasket-ui-list"))
        elif form.cleaned_data["workbasket_action"] == "CREATE":
            return redirect(reverse("workbaskets:workbasket-ui-create"))
        elif form.cleaned_data["workbasket_action"] == "PACKAGE_WORKBASKETS":
            return redirect(reverse("publishing:packaged-workbasket-queue-ui-list"))
        elif form.cleaned_data["workbasket_action"] == "PROCESS_ENVELOPES":
            return redirect(reverse("publishing:envelope-queue-ui-list"))
        elif form.cleaned_data["workbasket_action"] == "SEARCH":
            return redirect(reverse("search-page"))
        elif form.cleaned_data["workbasket_action"] == "IMPORT":
            return redirect(reverse("commodity_importer-ui-list"))


class SearchPageView(TemplateView):
    template_name = "common/search_page.jinja"


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

                    workbasket_id = task_info.get("args", [""])[0]
                    workbasket = WorkBasket.objects.get(id=workbasket_id)
                    num_completed, total = workbasket.rule_check_progress()

                    results.append(
                        {
                            "task_id": task_info.get("id"),
                            "workbasket_id": workbasket_id,
                            "date_time_start": date_time_start,
                            "checks_completed": f"{num_completed} out of {total}",
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

        if self.request.user.is_superuser:
            data["GIT_BRANCH"] = os.getenv("GIT_BRANCH", "Unavailable")
            data["GIT_COMMIT"] = os.getenv("GIT_COMMIT", "Unavailable")
            data["APP_UPDATED_TIME"] = datetime.fromtimestamp(
                os.path.getmtime(__file__),
            )
            data["LAST_TRANSACTION_TIME"] = (
                Transaction.objects.order_by("-updated_at").first().updated_at
            )

        return data


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"


class WithPaginationListMixin:
    """Mixin that can be inherited by a ListView subclass to enable this
    project's pagination capabilities."""

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


class WithPaginationListView(WithPaginationListMixin, FilterView):
    """Generic filtered list view enabling pagination."""


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

    def form_violates(self, form, transaction=None) -> bool:
        """
        If any of the specified business rules are violated, reshow the form
        with the violations as form errors.

        :param form: The submitted form
        :param transaction: The transaction containing the version of the object to be validated. Defaults to `self.object.transaction`
        """
        violations = False
        transaction = transaction or self.object.transaction

        for rule in self.validate_business_rules:
            try:
                rule(transaction).validate(self.object)
            except BusinessRuleViolation as v:
                form.add_error(None, v.args[0])
                violations = True

        return violations

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.

        Override the default form .post() method to check business rules
        when the form is otherwise valid.
        """
        form = self.get_form()
        if form.is_valid() and not self.form_violates(form):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


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


class DescriptionDeleteMixin:
    """Prevents the only description of the described object from being
    deleted."""

    def form_valid(self, form):
        described_object = self.object.get_described_object()
        if described_object.get_descriptions().count() == 1:
            form.add_error(
                None,
                "This description cannot be deleted because at least one description record is mandatory.",
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class SortingMixin:
    """
    Can be used to sort a queryset in a view using GET params. Checks the GET
    param against sort_by_fields to pass a valid field to .order_by(). If the
    GET param doesn't match the desired .order_by() field, a dictionary mapping
    can be added as custom_sorting.

    Example usage:

    class YourModelListView(SortingMixin, ListView):
        sort_by_fields = ["sid", "model", "valid_between"]
        custom_sorting = {
            "model": "model__polymorphic_ctype",
        }

        def get_queryset(self):
            self.queryset = YourModel.objects.all()
            return super().get_queryset()
    """

    def get_ordering(self):
        sort_by = self.request.GET.get("sort_by")
        order = self.request.GET.get("order")
        assert hasattr(
            self,
            "sort_by_fields",
        ), "SortingMixin requires class attribute sort_by_fields to be set"
        assert isinstance(self.sort_by_fields, list), "sort_by_fields must be a list"

        if sort_by and sort_by in self.sort_by_fields:
            if hasattr(self, "custom_sorting") and self.custom_sorting.get(sort_by):
                sort_by = self.custom_sorting.get(sort_by)

            if order == "desc":
                sort_by = f"-{sort_by}"

            return sort_by

        else:
            return None


def handler403(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/403.jinja", status=403)


def handler500(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/500.jinja", status=500)


class AccessibilityStatementView(TemplateView):
    template_name = "common/accessibility.jinja"
