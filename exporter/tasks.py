from celery import shared_task
from django.core.management import call_command


@shared_task
def upload_workbaskets():
    # TODO the code in upload_workbaskets should be split out
    #      and called from both, instead of calling the management
    #      command from here.
    call_command("upload_workbaskets")
