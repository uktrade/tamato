from celery import shared_task
from django.db.transaction import atomic

from workbaskets.models import WorkBasket


@shared_task
@atomic
def transition(instance_id: int, state: str, *args):
    """
    Runs the named state transition on the passed workbasket instance.

    The task will fail if the transition raises any exception and the state
    transition will not be applied. Any extra arguments passed to the task will
    be passed along to the transition function.
    """

    instance = WorkBasket.objects.get(pk=instance_id)
    getattr(instance, state)(*args)
    instance.save()
