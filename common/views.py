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
from django.urls import reverse
from django.views import generic
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.base import View
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView
from redis.exceptions import TimeoutError as RedisTimeoutError

from common.business_rules import BusinessRuleViolation
from common.models import TrackedModel
from common.models import Transaction
from common.pagination import build_pagination_list
from common.validators import UpdateType
from workbaskets.forms import SelectableObjectsForm
from workbaskets.forms import SelectedObjectsStore
from workbaskets.models import WorkBasket
from workbaskets.views.mixins import WithCurrentWorkBasket


class DashboardView(TemplateResponseMixin, FormMixin, View):
    """
    UI endpoint providing a dashboard view, including a WorkBasket (list) of
    paged user-selectable TrackedModel instances (items). Pages contain a
    configurable maximum number of items.

    Items are selectable (they form selections) via an associated checkbox
    widget so that bulk operations may be performed against them.

    Each page displays a maximum number of items (10 being the default), with
    user selections preserved when navigating between pages.

    Item selection is preserved in the user's session. Whenever page navigation
    or a bulk operation is performed, item selection state is updated.

    Unless client-side JavaScript is used to perform RESTful updates on checkbox
    check/uncheck, then we can't realistically save state changes when
    navigating away from the list view to other pages (i.e. HTTP GET requests
    for the application or other website).

    User item selection changes are calculated and applied to the Django
    Session object by performing a three way diff between:
    * Current selection state held in the session,
    * Available list items (have any new items been added, or somehow removed),
    * User submitted changes (from form POST requests)

    Note:
    --
    Options considered to manage paged selection:
    * Full list in form, hiding items not on current page. This would require
      either including all items in GET request's URI after POST, dropping use
      of GET after POST, neither seem very reasonable.
    * Use django formtools wizard. This doesn't fit the wizard's usecase and
      design very well and may make for an over complicated implementation.
    * Store user selection in the session. Simplest, complete and most elegant.
    """

    form_class = SelectableObjectsForm
    template_name = "common/index.jinja"

    default_page_size = 4
    # Form action mappings to URL names.
    action_success_urls = {
        "publish-all": "TODO-PUBLISH-URL",
        "remove-selected": "TODO-REMOVE-SELECTED",
        "page-prev": "index",
        "page-next": "index",
    }

    def __init__(self, **kwargs):
        self.per_page = kwargs.pop(
            "per_page",
            DashboardView.default_page_size,
        )
        super().__init__(**kwargs)
        self.workbasket = self._get_workbasket()
        self.paginator = Paginator(
            self.workbasket.tracked_models,
            per_page=self.per_page,
        )

    def _get_workbasket(self):
        workbasket = WorkBasket.objects.is_not_approved().last()
        if not workbasket:
            id = WorkBasket.objects.values_list("pk", flat=True).last() or 1
            workbasket = WorkBasket.objects.create(
                title=f"Workbasket {id}",
                author=self.request.user,
            )
        return workbasket

    def get(self, request, *args, **kwargs):
        """Service GET requests by displaying the page and form."""
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Manage POST requests, which can either be requests to change the
        paged form data while preserving the user's form changes, or finally
        submit the form data for processing."""
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def add_url_page_param(self, url, form_action):
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        page_number = 1
        if form_action == "page-prev":
            page_number = page.previous_page_number()
        elif form_action == "page-next":
            page_number = page.next_page_number()
        return f"{url}?page={page_number}"

    def get_success_url(self):
        form_action = self.request.POST.get("form-action")
        success_url = reverse(self.action_success_urls[form_action])
        if form_action in ("page-prev", "page-next"):
            success_url = self.add_url_page_param(
                success_url,
                form_action,
            )
        return success_url

    def get_initial(self):
        store = SelectedObjectsStore(self.request.session, "DASHBOARD_FORM")
        return store.data.copy()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        kwargs["field_id_prefix"] = "tracked_model"

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        context.update(
            {
                "workbasket": self.workbasket,
                "page_obj": page,
                "paginator": self.paginator,
            },
        )
        return context

    def form_valid(self, form):
        # TODO:
        # * Update the SelectedObjectStore with current selections.
        return super().form_valid(form)


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
    """Create a new tracked model."""

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
    """Create an updated version of a TrackedModel."""

    UPDATE_TYPE = UpdateType.UPDATE
    permission_required = "common.add_trackedmodel"
    template_name = "common/edit.jinja"

    def get_success_url(self):
        return self.object.get_url("confirm-update")


class DeleteView(CreateView):
    """Create a deletion of a TrackedModel."""

    UPDATE_TYPE = UpdateType.DELETE


class WithPaginationListView(FilterView):
    """Generic list view enabling pagination and adds a page link list to the
    context."""

    paginator_class = Paginator
    paginate_by = settings.REST_FRAMEWORK["PAGE_SIZE"]

    def get_context_data(self, *, object_list=None, **kwargs):
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
    pass


class TrackedModelDetailMixin:
    """Allows detail URLs to use <Identifying-Fields> instead of <pk>"""

    model: Type[TrackedModel]
    required_url_kwargs = None

    def get_object(self, queryset: Optional[QuerySet] = None) -> Model:
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
    pass


class BusinessRulesMixin:
    """Check business rules on form_submission."""

    validate_business_rules = []

    def form_valid(self, form):
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
