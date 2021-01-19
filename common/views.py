import django.contrib.auth.views
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views import generic

from common.models import Transaction
from common.validators import UpdateType
from workbaskets.models import WorkBasket


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


class UpdateView(generic.UpdateView):
    """Create an updated version of a TrackedModel."""

    UPDATE_TYPE = UpdateType.UPDATE


class DeleteView(CreateView):
    """Create a deletion of a TrackedModel."""

    UPDATE_TYPE = UpdateType.DELETE
