"""Common views."""
import time
from typing import Optional
from typing import Type

import django.contrib.auth.views
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import OperationalError
from django.db import connection
from django.db.models import Model
from django.db.models import QuerySet
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views import generic
from django_filters.views import FilterView
from redis.exceptions import TimeoutError as RedisTimeoutError

from common.business_rules import BusinessRuleViolation
from common.models import TrackedModel
from common.models import Transaction
from common.pagination import build_pagination_list
from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.views.mixins import WithCurrentWorkBasket


def index(request):
    """Home page of the tariff editor."""
    workbasket = WorkBasket.objects.is_not_approved().last()

    if not workbasket:
        id = WorkBasket.objects.values_list("pk", flat=True).last() or 1
        workbasket = WorkBasket.objects.create(
            title=f"Workbasket {id}",
            author=request.user,
        )

    paginator = Paginator(workbasket.tracked_models, per_page=10)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "common/index.jinja",
        context={
            "workbasket": workbasket,
            "page_obj": page,
            "paginator": paginator,
        },
    )


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


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"


class CreateView(PermissionRequiredMixin, generic.CreateView):
    """Base view class for creating a new tracked model."""

    permission_required = "common.add_trackedmodel"
    UPDATE_TYPE = UpdateType.CREATE

    def form_valid(self, form):
        transaction = self.get_transaction()
        transaction.save()
        self.object = form.save(commit=False)
        self.object.update_type = self.UPDATE_TYPE
        self.object.transaction = transaction
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_transaction(self):
        return Transaction()

    def get_success_url(self):
        return self.object.get_url("confirm-create")


class UpdateView(PermissionRequiredMixin, generic.UpdateView):
    """Base view class for creating an updated version of a TrackedModel."""

    UPDATE_TYPE = UpdateType.UPDATE
    permission_required = "common.add_trackedmodel"
    template_name = "common/edit.jinja"

    def get_success_url(self):
        return self.object.get_url("confirm-update")


class DeleteView(CreateView):
    """Base view class for deleting a TrackedModel."""

    UPDATE_TYPE = UpdateType.DELETE


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

        if self.request.method == "POST":
            obj = obj.new_version(
                WorkBasket.current(self.request),
                save=False,
            )

        return obj


class TrackedModelDetailView(
    WithCurrentWorkBasket,
    TrackedModelDetailMixin,
    generic.DetailView,
):
    """Base view class for displaying a single TrackedModel."""


class BusinessRulesMixin:
    """Check business rules on form_submission."""

    validate_business_rules = []

    def form_valid(self, form):
        """
        If any of the specified business rules are violated, reshow the form
        with the violations as form errors.

        :param form: The submitted form
        """
        violations = False
        workbasket = WorkBasket.current(self.request)
        transaction = workbasket.transactions.last()

        for rule in self.validate_business_rules:
            try:
                rule(transaction).validate(form.instance)
            except BusinessRuleViolation as v:
                form.add_error(None, v.args[0])
                violations = True

        if violations:
            return self.form_invalid(form)

        return super().form_valid(form)
