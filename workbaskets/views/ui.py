import boto3
from botocore.client import Config
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.base import TemplateView
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView

from common.filters import TamatoFilter
from common.pagination import build_pagination_list
from common.views import DashboardView
from common.views import WithPaginationListView
from exporter.models import Upload
from workbaskets import forms
from workbaskets import tasks
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore
from workbaskets.validators import WorkflowStatus
from workbaskets.views.decorators import require_current_workbasket


class WorkBasketFilter(TamatoFilter):
    search_fields = (
        "id",
        "author",
        "reason",
        "title",
    )
    clear_url = reverse_lazy("workbaskets:workbasket-ui-list")

    class Meta:
        model = WorkBasket
        fields = ["search", "status"]


class WorkBasketList(WithPaginationListView):
    """UI endpoint for viewing and filtering workbaskets."""

    template_name = "workbaskets/list.jinja"
    filterset_class = WorkBasketFilter
    search_fields = [
        "title",
        "reason",
    ]

    def get_queryset(self):
        return WorkBasket.objects.order_by("-updated_at")


class WorkBasketConfirmCreate(DetailView):
    template_name = "workbaskets/confirm_create.jinja"
    model = WorkBasket
    queryset = WorkBasket.objects.all()


class WorkBasketCreate(CreateView):
    """UI endpoint for creating workbaskets."""

    permission_required = "workbaskets.add_workbasket"
    template_name = "workbaskets/create.jinja"
    form_class = forms.WorkbasketCreateForm

    def form_valid(self, form):
        user = get_user_model().objects.get(username=self.request.user.username)
        self.object = form.save(commit=False)
        self.object.author = user
        self.object.save()
        return redirect(
            reverse(
                "workbaskets:workbasket-ui-confirm-create",
                kwargs={"pk": self.object.pk},
            ),
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class SelectWorkbasketView(WorkBasketList):
    template_name = "workbaskets/select-workbasket.jinja"
    permission_required = "workbaskets.change_workbasket"

    def get_queryset(self):
        return (
            WorkBasket.objects.exclude(status=WorkflowStatus.PUBLISHED)
            .exclude(status=WorkflowStatus.ARCHIVED)
            .exclude(status=WorkflowStatus.SENT)
            .order_by("-updated_at")
        )


class WorkBasketDetail(DetailView):
    """UI endpoint for viewing a specified workbasket."""

    model = WorkBasket
    template_name = "workbaskets/detail.jinja"
    paginate_by = 50
    # paginate_by = 2

    def get_context_data(self, **kwargs):
        """
        Although this is a detail view of a WorkBasket instance, it provides a
        view of its contained items (TrackedModel instances) as a paged list.

        A paginator and related objects are therefore added to page context.
        """
        items = self.get_object().tracked_models.all()

        paginator = Paginator(items, WorkBasketDetail.paginate_by)
        try:
            page_number = int(self.request.GET.get("page", 1))
        except ValueError:
            page_number = 1
        page_obj = paginator.get_page(page_number)

        context = super().get_context_data(**kwargs)

        context["paginator"] = paginator
        context["page_obj"] = page_obj
        context["is_paginated"] = True
        context["object_list"] = items
        context["page_links"] = build_pagination_list(
            page_number,
            page_obj.paginator.num_pages,
        )

        return context


class WorkBasketSubmit(PermissionRequiredMixin, SingleObjectMixin, RedirectView):
    """UI endpoint for submitting a workbasket to HMRC CDS."""

    model = WorkBasket
    permission_required = "workbaskets.change_workbasket"

    def get_redirect_url(self, *args, **kwargs) -> str:
        return reverse("dashboard")

    def get(self, *args, **kwargs):
        workbasket: WorkBasket = self.get_object()

        (
            tasks.transition.si(
                workbasket.pk,
                "submit_for_approval",
            )
            | tasks.transition.si(
                workbasket.pk,
                "approve",
                self.request.user.pk,
                settings.TRANSACTION_SCHEMA,
            )
        ).delay()

        return super().get(*args, **kwargs)


class WorkBasketDeleteChanges(PermissionRequiredMixin, ListView):
    """UI for user review of WorkBasket item deletion."""

    template_name = "workbaskets/delete_changes.jinja"
    permission_required = "workbaskets.change_workbasket"

    def _workbasket(self):
        """Get the WorkBasket instance associated with this view's deletion."""

        try:
            workbasket = WorkBasket.objects.get(pk=self.kwargs["pk"])
        except WorkBasket.DoesNotExist:
            workbasket = WorkBasket.objects.none()
        return workbasket

    def _session_store(self, workbasket):
        """Get the current user's SessionStore for the WorkBasket that they're
        deleting, containing ids of the items that have been selected for
        deletion."""

        return SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{workbasket.pk}",
        )

    def get_queryset(self):
        """Get TrackedModelQuerySet of instances that are candidates for
        deletion."""

        workbasket = self._workbasket()
        store = self._session_store(workbasket)
        return workbasket.tracked_models.filter(pk__in=store.data.keys())

    def post(self, request, *args, **kwargs):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            return redirect("dashboard")

        # By reverse ordering on record_code + subrecord_code we're able to
        # delete child entities first, avoiding protected foreign key
        # violations.
        object_list = self.get_queryset().record_ordering().reverse()

        for obj in object_list:
            # Unlike situations where TrackedModels are superceded and are
            # subject to UpdateType.DELETE, WorkBasket item deletion really
            # should remove rows from the DB.
            try:
                obj.delete()
            except ProtectedError:
                # TODO Capture deletion failure and present back to UI.
                # UI component(s) design in the backlog for this: TP-1148.
                pass

        workbasket = self._workbasket()
        session_store = self._session_store(workbasket)
        session_store.clear()

        redirect_url = reverse(
            "workbaskets:workbasket-ui-delete-changes-done",
            kwargs={"pk": self.kwargs["pk"]},
        )
        return redirect(redirect_url)


class WorkBasketDeleteChangesDone(TemplateView):
    template_name = "workbaskets/delete_changes_confirm.jinja"


def download_envelope(request):
    """
    Creates s3 resource using AWS environment variables.

    Tries to get filename from most recent s3 upload. If no upload exists, returns 404.

    Generates presigned url from s3 client using bucket and file names.

    Returns `HttpResponseRedirect` with presigned url passed as only argument.
    """
    s3 = boto3.resource(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        last_added = (
            settings.HMRC_STORAGE_DIRECTORY
            + Upload.objects.latest("created_date").filename
        )
    except Upload.DoesNotExist as err:
        raise Http404("No uploaded envelope available for download")

    url = s3.meta.client.generate_presigned_url(
        ClientMethod="get_object",
        ExpiresIn=3600,
        Params={
            "Bucket": settings.HMRC_STORAGE_BUCKET_NAME,
            "Key": last_added,
        },
    )

    return HttpResponseRedirect(url)


@method_decorator(require_current_workbasket, name="dispatch")
class EditWorkbasketView(DashboardView):
    template_name = "common/edit-workbasket.jinja"
    permission_required = "workbaskets.change_workbasket"

    def dispatch(self, request, *args, **kwargs):
        workbasket_pk = request.GET.get("workbasket")

        if workbasket_pk:
            workbasket = WorkBasket.objects.get(pk=workbasket_pk)

            if workbasket:
                workbasket.save_to_session(request.session)

        return super().dispatch(request, *args, **kwargs)


@method_decorator(require_current_workbasket, name="dispatch")
class PreviewWorkbasketView(TemplateView):
    template_name = "common/preview-workbasket.jinja"

    def dispatch(self, request, *args, **kwargs):
        workbasket_pk = request.GET.get("workbasket")

        if workbasket_pk:
            workbasket = WorkBasket.objects.get(pk=workbasket_pk)

            if workbasket:
                workbasket.save_to_session(request.session)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workbasket"] = WorkBasket.load_from_session(self.request.session)
        return context


@method_decorator(require_current_workbasket, name="dispatch")
class ReviewWorkbasketView(TemplateResponseMixin, FormMixin, View):
    template_name = "common/review-workbasket.jinja"

    def dispatch(self, request, *args, **kwargs):
        workbasket_pk = request.GET.get("workbasket")

        if workbasket_pk:
            workbasket = WorkBasket.objects.get(pk=workbasket_pk)

            if workbasket:
                workbasket.save_to_session(request.session)

        return super().dispatch(request, *args, **kwargs)

    form_class = forms.SelectableObjectsForm

    # Form action mappings to URL names.
    action_success_url_names = {
        "publish-all": "workbaskets:workbasket-ui-submit",
        "remove-selected": "workbaskets:workbasket-ui-delete-changes",
        "page-prev": "workbaskets:review-workbasket",
        "page-next": "workbaskets:review-workbasket",
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
