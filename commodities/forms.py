from datetime import datetime

import lxml
import magic
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Submit
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from sentry_sdk import capture_exception

from common.util import parse_xml
from importer import models
from importer.chunker import chunk_taric
from importer.management.commands.run_import_batch import run_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.validators import WorkflowStatus


def get_mime_type(file):
    """Get MIME by reading the header of the file."""
    initial_pos = file.tell()
    file.seek(0)
    mime_type = magic.from_buffer(file.read(1024), mime=True)
    file.seek(initial_pos)
    return mime_type


class CommodityImportForm(forms.ModelForm):
    taric_file = forms.FileField(
        required=True,
        help_text="",
        label="Select an XML file",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "taric_file",
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean_taric_file(self):
        data = self.cleaned_data["taric_file"]
        generic_error_message = "The selected file could not be uploaded - try again"

        mime_type = get_mime_type(data)
        if mime_type not in ["text/xml", "application/xml"]:
            raise ValidationError("The selected file must be XML")

        try:
            xml_file = parse_xml(data)
        except lxml.etree.XMLSyntaxError as e:
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

    @transaction.atomic
    def save(self, user: User, workbasket_id: str, commit=True):
        # we don't ask the user to provide a name in the form so generate one here based on filename and timestamp
        now = datetime.now()
        current_time = now.strftime("%H%M%S")
        batch_name = f"{self.cleaned_data['taric_file'].name}_{current_time}"
        self.instance.name = batch_name
        batch = super().save(commit)

        record_group = TARIC_RECORD_GROUPS["commodities"]

        chunk_taric(self.cleaned_data["taric_file"], batch, record_group=record_group)
        run_batch(
            batch=batch.name,
            status=WorkflowStatus.EDITING,
            partition_scheme_setting=settings.TRANSACTION_SCHEMA,
            username=user.username,
            workbasket_id=workbasket_id,
            record_group=record_group,
        )

        return batch

    class Meta:
        model = models.ImportBatch
        exclude = ["name", "split_job", "dependencies"]
