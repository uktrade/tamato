import lxml
import magic
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Layout
from defusedxml.common import DTDForbidden
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from common.util import parse_xml
from importer import models
from importer.chunker import chunk_taric
from importer.management.commands.run_import_batch import run_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.validators import WorkflowStatus

if settings.SENTRY_ENABLED:
    from sentry_sdk import capture_exception


def get_mime_type(file):
    """Get MIME by reading the header of the file."""
    initial_pos = file.tell()
    file.seek(0)
    mime_type = magic.from_buffer(file.read(1024), mime=True)
    file.seek(initial_pos)
    return mime_type


class ImportForm(forms.ModelForm):
    def process_file(
        file,
        batch,
        user,
        record_group=TARIC_RECORD_GROUPS["commodities"],
        status=WorkflowStatus.EDITING,
        partition_scheme_setting=settings.TRANSACTION_SCHEMA,
        workbasket_id=None,
    ):
        chunk_taric(file, batch, record_group=record_group)
        run_batch(
            batch=batch.name,
            status=status,
            partition_scheme_setting=partition_scheme_setting,
            username=user.username,
            record_group=record_group,
            workbasket_id=workbasket_id,
        )

    def clean_taric_file(self):
        data = self.cleaned_data["taric_file"]
        generic_error_message = "The selected file could not be uploaded - try again"

        mime_type = get_mime_type(data)
        if mime_type not in ["text/xml", "application/xml"]:
            raise ValidationError("The selected file must be XML")

        try:
            xml_file = parse_xml(data)
        except (lxml.etree.XMLSyntaxError, DTDForbidden) as e:
            if settings.SENTRY_ENABLED:
                capture_exception(e)
            raise ValidationError(generic_error_message)

        with open(settings.PATH_XSD_COMMODITIES_TARIC) as xsd_file:
            xmlschema = lxml.etree.XMLSchema(file=xsd_file)

        try:
            xmlschema.assertValid(xml_file)
        except lxml.etree.DocumentInvalid as e:
            if settings.SENTRY_ENABLED:
                capture_exception(e)
            raise ValidationError(generic_error_message)

        # read() in an InMemoryUploadedFile returns an empty string the second time it is called
        # calling seek(0) again fixes this
        # https://code.djangoproject.com/ticket/7812
        data.seek(0)
        return data

    class Meta:
        model = models.ImportBatch
        fields = ["name", "split_job", "dependencies"]


class UploadTaricForm(ImportForm):
    status = forms.ChoiceField(choices=WorkflowStatus.choices, required=True)
    taric_file = forms.FileField(required=True)
    commodities = forms.BooleanField(
        label="Commodities Only",
        required=False,
        initial=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            *self.fields,
            Button("submit", "Upload"),
        )

    @transaction.atomic
    def save(self, user: User, commit=True):
        batch = super().save(commit)

        if self.data.get("commodities") is not None:
            record_group = TARIC_RECORD_GROUPS["commodities"]
        else:
            record_group = None

        self.process_file(
            self.files["taric_file"],
            batch,
            user,
            record_group=record_group,
            status=self.data["status"],
        )

        return batch
