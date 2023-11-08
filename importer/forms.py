import os

import lxml
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from defusedxml.common import DTDForbidden
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from sentry_sdk import capture_exception

from common.util import get_mime_type
from common.util import parse_xml
from importer.chunker import chunk_taric
from importer.management.commands.run_import_batch import run_batch
from importer.models import ImportBatch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus
from workbaskets.validators import tops_jira_number_validator


class ImportFormMixin:
    """Mixin for importer forms, providing common taric_file clean and
    processing support."""

    def process_file(
        self,
        file: InMemoryUploadedFile,
        batch,
        user,
        record_group=TARIC_RECORD_GROUPS["commodities"],
        status=WorkflowStatus.EDITING,
        partition_scheme_setting=settings.TRANSACTION_SCHEMA,
        workbasket_id=None,
    ):
        """
        Split the uploaded file into chunks, associate with `batch`, and
        schedule parser execution against `batch` conditional upon chunks having
        been created.

        The function returns the number of chunks created by the chunker.

        Note that a zero chunk count can result, for instance, when an imported
        file contains no entities of interest, as can happen when a TGB file
        contains only non-400 record code elements. A value of 0 (zero) is
        returned by this function in such cases.
        """

        chunk_count = chunk_taric(file, batch, record_group=record_group)
        if chunk_count:
            run_batch(
                batch_id=batch.pk,
                status=status,
                partition_scheme_setting=partition_scheme_setting,
                username=user.username,
                record_group=record_group,
                workbasket_id=workbasket_id,
            )
        return chunk_count

    def clean_taric_file(self):
        """Perform validation checks against the uploaded file."""
        uploaded_taric_file = self.cleaned_data["taric_file"]
        generic_error_message = "The selected file could not be uploaded - try again"

        mime_type = get_mime_type(uploaded_taric_file)
        if mime_type not in ["text/xml", "application/xml"]:
            raise ValidationError("The selected file must be XML")

        try:
            xml_file = parse_xml(uploaded_taric_file)
        except (lxml.etree.XMLSyntaxError, DTDForbidden) as e:
            if settings.SENTRY_ENABLED:
                capture_exception(e)
            raise ValidationError(generic_error_message)

        with open(self.xsd_file) as xsd_file:
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
        uploaded_taric_file.seek(0)
        return uploaded_taric_file


class UploadTaricForm(ImportFormMixin, forms.ModelForm):
    """
    Generic TARIC file import form, used to import TARIC files containing any.

    type of entity - Additional Codes, Certificates, Footnotes, etc.
    """

    class Meta:
        model = ImportBatch
        fields = ["name", "split_job", "dependencies"]

    status = forms.ChoiceField(
        choices=[(c.value, c.label) for c in WorkflowStatus.unchecked_statuses()],
        initial=WorkflowStatus.EDITING.value,
        required=True,
        help_text="Status of workbasket created by the import.",
    )
    taric_file = forms.FileField(
        required=True,
        help_text="TARIC3 XML file containing non-goods entities.",
    )
    xsd_file = settings.PATH_XSD_TARIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].help_text = (
            "Import name also used to name the workbasket created by and "
            "associated with the import."
        )
        self.fields["split_job"].help_text = (
            "Very large imports, such as an initial EU seed file import, may "
            "require splitting. You almost certainly won't require this."
        )
        self.fields["dependencies"].help_text = (
            "If other, active imports must complete before this import is "
            "started, then they should be set as depenedencies. You probably "
            "don't require this unless you are importing many TARIC files at "
            "once."
        )

        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "name",
            "split_job",
            "dependencies",
            "status",
            "taric_file",
            Submit(
                "submit",
                "Upload",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @transaction.atomic
    def save(self, user: User):
        workbasket = WorkBasket.objects.create(
            title=f"Data Import {self.cleaned_data['name']}",
            author=user,
            approver=user,
            status=self.cleaned_data["status"],
        )

        batch = super().save(commit=False)
        batch.goods_import = False
        batch.author = user
        batch.workbasket = workbasket
        batch.save()

        self.process_file(
            self.files["taric_file"],
            batch,
            user,
            record_group=None,
            status=self.cleaned_data["status"],
            workbasket_id=workbasket.id,
        )

        return batch


class CommodityImportForm(ImportFormMixin, forms.Form):
    """Form used to create new instances of ImportBatch via upload of a
    commodity code file."""

    taric_file = forms.FileField(
        label="Upload a TARIC file",
        help_text=(
            "Valid TARIC files contain XML and usually have a .xml file name "
            "extension. They contain goods nomenclature items and related "
            "items."
        ),
    )
    workbasket_title = forms.CharField(
        max_length=255,
        validators=[tops_jira_number_validator],
        strip=True,
        label="Tops/Jira number",
        help_text=(
            "Your Tops/Jira number is needed to associate your import's "
            "workbasket with your Jira ticket. You can find this number at the "
            "end of the web address for your Jira ticket. Your workbasket will "
            "be given a unique number that may be different to your Tops/Jira "
            "number. "
        ),
    )

    xsd_file = settings.PATH_XSD_COMMODITIES_TARIC

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "taric_file",
            "workbasket_title",
            Submit(
                "submit",
                "Upload",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        # Derive ImportBatch.name from the uploaded filename - if a file has
        # been submitted.
        taric_file = (
            self.request.FILES["taric_file"]
            if "taric_file" in self.request.FILES
            else None
        )
        if taric_file:
            cleaned_data["name"] = taric_file.name

        return cleaned_data

    def clean_workbasket_title(self):
        workbasket_title = self.cleaned_data["workbasket_title"]
        if WorkBasket.objects.filter(title=workbasket_title):
            raise ValidationError("WorkBasket title already exists.")
        return workbasket_title

    @transaction.atomic
    def save(self):
        """
        Save an instance of ImportBatch using the form data and related, derived
        values.

        NOTE: because this save() method initiates import batch processing -
        which results in a background task being started - it doesn't currently
        make sense to use commit=False. process_file() should be moved into the
        view if this (common) behaviour becomes required.
        """
        file_name = os.path.splitext(self.cleaned_data["name"])[0]
        description = f"TARIC {file_name} commodity code changes"
        workbasket = WorkBasket.objects.create(
            title=self.cleaned_data["workbasket_title"],
            reason=description,
            author=self.request.user,
        )
        workbasket.save()

        batch = ImportBatch(
            author=self.request.user,
            name=self.cleaned_data["name"],
            goods_import=True,
            workbasket=workbasket,
        )
        # ensure at the start of the file stream
        self.files["taric_file"].seek(0, os.SEEK_SET)
        batch.taric_file.save(
            self.files["taric_file"].name,
            ContentFile(self.files["taric_file"].read()),
        )
        batch.save()

        chunk_count = self.process_file(
            self.files["taric_file"],
            batch,
            self.request.user,
            workbasket_id=batch.workbasket.id,
        )
        if not chunk_count:
            # No chunks to process so the import is considered done and
            # succeeded.
            batch.succeeded()
            batch.save()

        return batch
