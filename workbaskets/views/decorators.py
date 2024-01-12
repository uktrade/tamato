from functools import wraps

from django.shortcuts import redirect

from workbaskets.models import WorkBasket


def require_current_workbasket(view_func):
    """View decorator which redirects user to select a new current workbasket
    before continuing."""

    @wraps(view_func)
    def check_for_current_workbasket(request, *args, **kwargs):
        try:
            if WorkBasket.current(request):
                return view_func(request, *args, **kwargs)
            return redirect("workbaskets:no-active-workbasket")
        except WorkBasket.DoesNotExist:
            return redirect("workbaskets:no-active-workbasket")

    return check_for_current_workbasket
