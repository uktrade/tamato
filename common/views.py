"""Common views."""

import os
import time
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

import boto3
import django.contrib.auth.views
import kombu.exceptions
from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError
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
from django.db.models import Q
from django.db.models import QuerySet
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.celery import app
from common.forms import HomeSearchForm
from common.models import TrackedModel
from common.models import Transaction
from common.pagination import build_pagination_list
from common.validators import UpdateType
from exporter.sqlite.util import sqlite_dumps
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures.models import Measure
from publishing.models import PackagedWorkBasket
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from tasks.models import UserAssignment
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus
from workbaskets.views.mixins import WithCurrentWorkBasket

from .celery import app as celery_app


class HomeView(LoginRequiredMixin, FormView):
    template_name = "common/homepage.jinja"
    form_class = HomeSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assignments = (
            UserAssignment.objects.filter(user=self.request.user)
            .assigned()
            .select_related("task__workbasket")
            .filter(
                Q(task__workbasket__status=WorkflowStatus.EDITING)
                | Q(task__workbasket__status=WorkflowStatus.ERRORED),
            )
        )
        assigned_workbaskets = []
        for assignment in assignments:
            workbasket = assignment.task.workbasket
            assignment_type = (
                "Assigned"
                if assignment.assignment_type
                == UserAssignment.AssignmentType.WORKBASKET_WORKER
                else "Reviewing"
            )
            rule_violations_count = workbasket.tracked_model_check_errors.count()
            assigned_workbaskets.append(
                {
                    "id": workbasket.id,
                    "description": workbasket.reason,
                    "rule_violations_count": rule_violations_count,
                    "assignment_type": assignment_type,
                },
            )

        context.update(
            {
                "assigned_workbaskets": assigned_workbaskets,
                "can_add_workbasket": self.request.user.has_perm(
                    "workbaskets.add_workbasket",
                ),
                "can_edit_workbasket": self.request.user.has_perm(
                    "workbaskets.change_workbasket",
                ),
                "can_view_reports": self.request.user.has_perm(
                    "reports.view_report_index",
                ),
            },
        )
        return context

    def get_search_result(self, search_term: str) -> Optional[str]:
        """
        Returns the outcome of a search for a given `search_term`.

        The search term is expected to be either a tariff element name or a tariff
        element ID, with a length between 2 and 18 characters.

        For a tariff element name, we attempt to find a matching key in `list_view_map` dict,
        returning the corresponding 'Find and edit' view URL of the matching element.

        For a tariff element ID, we perform case-insensitive DB lookups for tariff elements whose ID
        takes the form of the search term, returning the detail view URL of the matching element.

        If no match can be found for a given search term, then `None` is returned.
        """
        # Check if the search term matches an element name
        list_view_map = {
            "additional codes": "additional_code-ui-list",
            "certificates": "certificate-ui-list",
            "footnotes": "footnote-ui-list",
            "geographical areas": "geo_area-ui-list",
            "commodities": "commodity-ui-list",
            "measures": "measure-ui-search",
            "quotas": "quota-ui-list",
            "regulations": "regulation-ui-list",
        }
        match = list_view_map.get(search_term, None)
        if match:
            return match

        # Otherwise attempt to match the search term to an element ID
        search_len = len(search_term)
        if search_len == 2:
            match = (
                GeographicalArea.objects.filter(area_id__iexact=search_term)
                .current()
                .last()
            )
            return match.get_url() if match else None

        elif search_len == 4:
            match = (
                AdditionalCode.objects.filter(
                    type__sid__iexact=search_term[0],
                    code__iexact=search_term[1:],
                )
                .current()
                .last()
            )
            if match:
                return match.get_url()

            match = (
                Certificate.objects.filter(
                    certificate_type__sid__iexact=search_term[0],
                    sid__iexact=search_term[1:],
                )
                .current()
                .last()
            )
            if match:
                return match.get_url()

            match = (
                GeographicalArea.objects.filter(area_id__iexact=search_term)
                .current()
                .last()
            )
            return match.get_url() if match else None

        elif search_len == 5:
            match = (
                Footnote.objects.filter(
                    footnote_type__footnote_type_id__iexact=search_term[:2],
                    footnote_id=search_term[2:],
                )
                .current()
                .last()
            )
            return match.get_url() if match else None

        elif search_term.isnumeric():
            if search_len == 6 and search_term[0] == "0":
                match = (
                    QuotaOrderNumber.objects.filter(order_number=search_term)
                    .current()
                    .last()
                )
                return match.get_url() if match else None
            if search_len == 10:
                match = (
                    GoodsNomenclature.objects.filter(item_id=search_term)
                    .current()
                    .last()
                )
            if match:
                return match.get_url()
            else:
                match = Measure.objects.filter(sid=search_term).current().last()
                return match.get_url() if match else None

        elif search_len == 8:
            match = (
                Regulation.objects.filter(regulation_id__iexact=search_term)
                .current()
                .last()
            )
            return match.get_url() if match else None

        # No match has been found for the search term
        else:
            return None

    def form_valid(self, form):
        search_term = form.cleaned_data["search_term"]
        if not search_term:
            return self.get_success_url(reverse("search-page"))

        result = self.get_search_result(search_term)
        if result:
            return self.get_success_url(result)
        else:
            return self.get_success_url(reverse("search-page"))

    def get_success_url(self, url):
        return redirect(url)


class SearchPageView(TemplateView):
    template_name = "common/search_page.jinja"


class ResourcesView(TemplateView):
    template_name = "common/resources.jinja"


class HealthCheckView(View):
    """Endpoint for a Pingdom-compatible HTTP response health check."""

    content_type = "text/xml"
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    pingdom_template = (
        "<pingdom_http_custom_check>"
        "<status>{status}</status>"
        "<response_time>{response_time:.03f}</response_time>"
        "</pingdom_http_custom_check>"
    )

    @property
    def checks(self) -> List[callable]:
        return [
            self.check_database,
            self.check_redis_cache,
            self.check_celery_broker,
            self.check_s3,
        ]

    def check_database(self) -> Tuple[str, int]:
        try:
            connection.cursor()
            return "OK", 200
        except OperationalError:
            return "Database health check failed", 503

    def check_redis_cache(self) -> Tuple[str, int]:
        try:
            cache.set("__pingdom_test", 1, timeout=1)
            return "OK", 200
        except (RedisConnectionError, RedisTimeoutError):
            return "Redis cache health check failed", 503

    def check_celery_broker(self) -> Tuple[str, int]:
        try:
            conn = celery_app.broker_connection().ensure_connection(
                max_retries=0,
                timeout=10,
            )
            conn.close()
            return "OK", 200
        except kombu.exceptions.OperationalError:
            return "Celery broker health check failed", 503

    def check_s3(self) -> Tuple[str, int]:
        try:
            client = boto3.client(
                "s3",
                aws_access_key_id=settings.HMRC_PACKAGING_S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.HMRC_PACKAGING_S3_SECRET_ACCESS_KEY,
                endpoint_url=settings.S3_ENDPOINT_URL,
                region_name=settings.HMRC_PACKAGING_S3_REGION_NAME,
            )
            client.head_bucket(Bucket=settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME)
            return "OK", 200
        except (ClientError, EndpointConnectionError):
            return "S3 health check failed", 503

    def get(self, request, *args, **kwargs) -> HttpResponse:
        start_time = time.time()
        for check in self.checks:
            status, status_code = check()
            if status_code != 200:
                break
        response_time = time.time() - start_time
        content = self.pingdom_template.format(
            status=status,
            response_time=response_time,
        )
        return HttpResponse(
            content=content,
            status=status_code,
            reason=status,
            headers=self.headers,
            content_type=self.content_type,
        )


class AppInfoView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "common/app_info.jinja"
    DATETIME_FORMAT = "%d %b %Y, %H:%M"

    def active_tasks(self) -> Dict:
        inspect = app.control.inspect()
        if not inspect:
            return {}

        active_tasks = inspect.active()
        if not active_tasks:
            return {}

        return active_tasks

    @staticmethod
    def timestamp_to_datetime_string(timestamp):
        return make_aware(
            datetime.fromtimestamp(timestamp),
        ).strftime(AppInfoView.DATETIME_FORMAT)

    def active_envelope_generation(self, active_tasks):
        results = []

        for _, task_info_list in active_tasks.items():
            for task_info in task_info_list:
                if task_info.get("name") == "publishing.tasks.create_xml_envelope_file":
                    date_time_start = AppInfoView.timestamp_to_datetime_string(
                        task_info.get("time_start"),
                    )

                    packaged_workbasket_id = task_info.get("args", [""])[0]
                    packaged_workbasket = PackagedWorkBasket.objects.get(
                        id=packaged_workbasket_id,
                    )
                    workbasket_id = packaged_workbasket.workbasket.id

                    results.append(
                        {
                            "task_id": task_info.get("id"),
                            "packaged_workbasket_id": packaged_workbasket_id,
                            "workbasket_id": workbasket_id,
                            "date_time_start": date_time_start,
                        },
                    )

        return results

    def active_checks(self, active_tasks):
        results = []

        for _, task_info_list in active_tasks.items():
            for task_info in task_info_list:
                if (
                    task_info.get("name")
                    == "workbaskets.tasks.call_check_workbasket_sync"
                ):
                    date_time_start = AppInfoView.timestamp_to_datetime_string(
                        task_info.get("time_start"),
                    )

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
            active_tasks = self.active_tasks()
            data["celery_healthy"] = True
            data["active_checks"] = self.active_checks(active_tasks)
            data["active_envelope_generation"] = self.active_envelope_generation(
                active_tasks,
            )
        except kombu.exceptions.OperationalError as oe:
            data["celery_healthy"] = False

        if self.request.user.is_superuser:
            data["GIT_BRANCH"] = os.getenv("GIT_BRANCH", "Unavailable")
            data["GIT_COMMIT"] = os.getenv("GIT_COMMIT", "Unavailable")
            data["APP_UPDATED_TIME"] = AppInfoView.timestamp_to_datetime_string(
                os.path.getmtime(__file__),
            )
            last_transaction = Transaction.objects.order_by("updated_at").last()
            data["LAST_TRANSACTION_TIME"] = (
                format(
                    last_transaction.updated_at.strftime(AppInfoView.DATETIME_FORMAT),
                )
                if last_transaction
                else "No transactions"
            )
            last_published_tranx = Transaction.objects.published().last()
            data["LAST_PUBLISHED_TRANSACTION_ORDER"] = (
                last_published_tranx.order if last_published_tranx else 0
            )
            data["SQLITE_DUMP_DAYS"] = 30
            data["SQLITE_DUMP_LIST"] = sqlite_dumps(days_past=30)

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
    DetailView,
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
        ordered = self.request.GET.get("ordered")
        assert hasattr(
            self,
            "sort_by_fields",
        ), "SortingMixin requires class attribute sort_by_fields to be set"
        assert isinstance(self.sort_by_fields, list), "sort_by_fields must be a list"

        if sort_by and sort_by in self.sort_by_fields:
            if hasattr(self, "custom_sorting") and self.custom_sorting.get(sort_by):
                sort_by = self.custom_sorting.get(sort_by)

            if ordered == "desc":
                sort_by = f"-{sort_by}"

            return sort_by

        else:
            return None


def handler403(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/403.jinja", status=403)


def handler500(request, *args, **kwargs):
    return TemplateResponse(request=request, template="common/500.jinja", status=500)


class MaintenanceView(TemplateView):
    template_name = "common/maintenance.jinja"


class AccessibilityStatementView(TemplateView):
    template_name = "common/accessibility.jinja"
