"""Common views."""
import time
from typing import Optional
from typing import Tuple
from typing import Type

import django.contrib.auth.views
from django.conf import settings
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
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic import FormView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.base import View
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView
from redis.exceptions import TimeoutError as RedisTimeoutError

from common import forms
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.models import TrackedModel
from common.pagination import build_pagination_list
from common.validators import UpdateType
from exporter.models import Upload
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


class WorkbasketActionView(FormView, View):
    template_name = "common/workbasket_action.jinja"
    form_class = forms.WorkbasketActionForm

    def form_valid(self, form):
        if form.cleaned_data["workbasket_action"] == "EDIT":
            return redirect(reverse("workbaskets:select-workbasket"))
        elif form.cleaned_data["workbasket_action"] == "CREATE":
            return redirect(reverse("workbaskets:workbasket-ui-create"))


@method_decorator(require_current_workbasket, name="dispatch")
class DashboardView(TemplateResponseMixin, FormMixin, View):
    """
    UI endpoint providing a dashboard view, including a WorkBasket (list) of
    paged user-selectable TrackedModel instances (items). Pages contain a
    configurable maximum number of items.

    Items are selectable (user selections) via an associated checkbox
    widget so that bulk operations may be performed against them.

    Each page displays a maximum number of items (10 being the default), with
    user selections preserved when navigating between pages.

    Item selection is preserved in the user's session. Whenever page navigation
    or a bulk operation is performed, item selection state is updated.

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
    template_name = "common/dashboard.jinja"

    # Form action mappings to URL names.
    action_success_url_names = {
        "publish-all": "workbaskets:workbasket-ui-submit",
        "remove-selected": "workbaskets:workbasket-ui-delete-changes",
        "page-prev": "index",
        "page-next": "index",
    }

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    @property
    def paginator(self):
        return Paginator(self.workbasket.tracked_models, per_page=10)

    @property
    def latest_upload(self):
        return Upload.objects.order_by("created_date").last()

    @property
    def uploaded_envelope_dates(self):
        """Gets a list of all transactions from the `latest_approved_workbasket`
        in the order they were updated and returns a dict with the first and
        last transactions as values for "start" and "end" keys respectively."""
        if self.latest_upload:
            transactions = self.latest_upload.envelope.transactions.order_by(
                "updated_at",
            )
            return {
                "start": transactions.first().updated_at,
                "end": transactions.last().updated_at,
            }
        return None

    def _append_url_page_param(self, url, form_action):
        """Based upon 'form_action', append a 'page' URL parameter to the given
        url param and return the result."""
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        page_number = 1
        if form_action == "page-prev":
            page_number = page.previous_page_number()
        elif form_action == "page-next":
            page_number = page.next_page_number()
        return f"{url}?page={page_number}"

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

    def get_success_url(self):
        form_action = self.request.POST.get("form-action")
        if form_action in ("publish-all", "remove-selected"):
            return reverse(
                self.action_success_url_names[form_action],
                kwargs={"pk": self.workbasket.pk},
            )
        elif form_action in ("page-prev", "page-next"):
            return self._append_url_page_param(
                reverse(self.action_success_url_names[form_action]),
                form_action,
            )
        return reverse("index")

    def get_initial(self):
        store = SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{self.workbasket.pk}",
        )
        return store.data.copy()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        context.update(
            {
                "workbasket": self.workbasket,
                "page_obj": page,
                "uploaded_envelope_dates": self.uploaded_envelope_dates,
            },
        )
        return context

    def form_valid(self, form):
        store = SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{self.workbasket.pk}",
        )
        to_add = {
            key: value for key, value in form.cleaned_data_no_prefix.items() if value
        }
        to_remove = {
            key: value
            for key, value in form.cleaned_data_no_prefix.items()
            if key not in to_add
        }
        store.add_items(to_add)
        store.remove_items(to_remove)
        return super().form_valid(form)


@method_decorator(require_current_workbasket, name="dispatch")
class MyWorkbasketView(DashboardView):
    template_name = "common/my-workbasket.jinja"

    def dispatch(self, request, *args, **kwargs):
        workbasket_pk = request.GET.get("workbasket")

        if workbasket_pk:
            workbasket = WorkBasket.objects.get(pk=workbasket_pk)

            if workbasket:
                workbasket.save_to_session(request.session)

        return super().dispatch(request, *args, **kwargs)


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
