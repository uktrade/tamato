import django.contrib.auth.views
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views import generic
from django_filters.views import FilterView

from common.models import Transaction
from common.pagination import build_pagination_list
from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.views.mixins import WithCurrentWorkBasket


def index(request):
    workbaskets = []
    if request.user.is_authenticated:
        workbaskets = WorkBasket.objects.filter(author=request.user)
    return render(
        request,
        "common/index.jinja",
        context={
            "workbaskets": workbaskets,
        },
    )


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"


class CreateView(generic.CreateView):
    """Create a new tracked model."""

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


class UpdateView(CreateView):
    """Create an updated version of a TrackedModel."""

    UPDATE_TYPE = UpdateType.UPDATE


class DeleteView(CreateView):
    """Create a deletion of a TrackedModel."""

    UPDATE_TYPE = UpdateType.DELETE


class TamatoListView(WithCurrentWorkBasket, FilterView):
    """
    Generic list view for Tamato models. Enables pagination and
    adds a page link list to the context.
    """

    paginator_class = Paginator
    paginate_by = settings.REST_FRAMEWORK["PAGE_SIZE"]

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        page_obj = data["page_obj"]
        page_number = page_obj.number
        data["page_links"] = build_pagination_list(
            page_number, page_obj.paginator.num_pages
        )
        return data
