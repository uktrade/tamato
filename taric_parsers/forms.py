from typing import Sequence

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction

from importer.models import ImportBatch
from importer.namespaces import TARIC_RECORD_GROUPS
from taric_parsers.chunker import chunk_taric
from taric_parsers.importer import run_batch


class TaricParserFormMixin:
    """Mixin for taric parser forms, providing common taric_file clean and
    processing support."""

    def process_file(
        self,
        file: InMemoryUploadedFile,
        batch,
        user,
        workbasket_title: str,
        record_group: Sequence[str] = None,
    ):
        """
        Create ImporterXmlChunk associate with `batch`, and schedule parser
        execution against `batch` conditional upon a chunk havinfg been created.

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
                username=user.username,
                workbasket_title=workbasket_title,
            )
        return chunk_count


class UploadTaricForm(TaricParserFormMixin, forms.ModelForm):
    """
    Generic TARIC file import form, used to import TARIC files containing any.

    type of entity - Additional Codes, Certificates, Footnotes, etc.
    """

    class Meta:
        model = ImportBatch
        fields = ["name"]

    taric_file = forms.FileField(
        required=True,
        help_text="TARIC3 XML file containing non-goods entities.",
    )

    commodities_only = forms.BooleanField(
        required=False,
        label="Commodities Only",
    )

    xsd_file = settings.PATH_XSD_TARIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].help_text = (
            "Import name also used to name the workbasket created by and "
            "associated with the import."
        )

        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "name",
            "commodities_only",
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
        import_batch = super().save(commit=False)
        import_batch.goods_import = False
        import_batch.author = user
        import_batch.save()

        if self.cleaned_data["commodities_only"]:
            record_group = list(TARIC_RECORD_GROUPS["commodities"])
        else:
            record_group = None

        chunk_count = self.process_file(
            self.files["taric_file"],
            import_batch,
            user,
            record_group=record_group,
            workbasket_title=f"Import for {self.cleaned_data['name']}",
        )

        if chunk_count < 1:
            import_batch.failed_empty()
            import_batch.save()

        return import_batch
