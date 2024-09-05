"""Common views."""

import os
import time
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import boto3
import django.contrib.auth.views
import kombu.exceptions
from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError
from dbt_copilot_python.utility import is_copilot
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import OperationalError
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.celery import app as celery_app
from common.forms import HomeSearchForm
from common.models import Transaction
from exporter.sqlite.util import sqlite_dumps
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures.models import Measure
from publishing.models import PackagedWorkBasket
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from tasks.models import TaskAssignee
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus


class HomeView(LoginRequiredMixin, FormView):
    template_name = "common/homepage.jinja"
    form_class = HomeSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assignments = (
            TaskAssignee.objects.filter(user=self.request.user)
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
                == TaskAssignee.AssignmentType.WORKBASKET_WORKER
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
            if is_copilot():
                client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    region_name=settings.HMRC_PACKAGING_S3_REGION_NAME,
                )
            else:
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
        inspect = celery_app.control.inspect()
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


class MaintenanceView(TemplateView):
    template_name = "common/maintenance.jinja"


class AccessibilityStatementView(TemplateView):
    template_name = "common/accessibility.jinja"
