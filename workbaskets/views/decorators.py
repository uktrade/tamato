from functools import wraps

from django.http import HttpResponseRedirect
from django.urls import reverse

from workbaskets.models import WorkBasket


def require_current_workbasket(view_func):
    """View decorator which redirects user to choose or create a workbasket
    before continuing."""

    @wraps(view_func)
    def check_for_current_workbasket(request, *args, **kwargs):
        try:
            if WorkBasket.current(request):
                return view_func(request, *args, **kwargs)
            return HttpResponseRedirect(reverse("workbasket-not-active"))
        except WorkBasket.DoesNotExist:
            return HttpResponseRedirect(reverse("workbasket-not-active"))

    return check_for_current_workbasket
