from functools import wraps

from workbaskets.models import WorkBasket


def require_current_workbasket(view_func):
    """View decorator which redirects user to choose or create a workbasket
    before continuing."""

    @wraps(view_func)
    def check_for_current_workbasket(request, *args, **kwargs):
        if WorkBasket.current(request) is None:
            workbasket = WorkBasket.objects.editable().last()
            if not workbasket:
                workbasket = WorkBasket.objects.create(
                    author=request.user,
                )

            workbasket.save_to_session(request.session)

        return view_func(request, *args, **kwargs)

    return check_for_current_workbasket