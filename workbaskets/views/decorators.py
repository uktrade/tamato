from functools import wraps

from django.shortcuts import redirect
from rest_framework.reverse import reverse

from workbaskets.models import WorkBasket


def require_current_workbasket(view_func):
    """
    View decorator which redirects user to choose or create a workbasket before
    continuing.
    """

    @wraps(view_func)
    def check_for_current_workbasket(request, *args, **kwargs):
        if WorkBasket.current(request) is None:
            request.session["return_to"] = request.build_absolute_uri()
            return redirect(reverse("workbasket-ui-choose-or-create"))

        return view_func(request, *args, **kwargs)

    return check_for_current_workbasket
