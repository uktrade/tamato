import hashlib
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import BaseCommand
from workbaskets.models import WorkflowStatus
from django.test import Client


def get_envelope():
    pass


def upload_envelopes():
    # TODO
    # Can use test client and view with status=authorized ?
    # Save to django storage setup to s3

    # This uses the test client to grab data via a view, this is a bit of a hack
    # but seems does provide a really simple API to get the data in the required
    # format.
    client = Client()
    request = client.get('/api/workbaskets.xml', status=str(WorkflowStatus.PUBLISHED))
    response = request.render()

    content_file = ContentFile(response.content)
    filename = f'{hashlib.sha256(response.content).hexdigest()}.xml'
    default_storage.save(f'tohmrc/staging/{filename}', content_file)


class Command(BaseCommand):
    help = "Generate envelope files and upload them to S3"

    def handle(self, *args, **options):
        upload_envelopes()
