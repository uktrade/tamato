from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Layout
from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from importer import models
from importer.chunker import chunk_taric
from importer.management.commands.run_import_batch import run_batch
from importer.namespaces import TARIC_RECORD_GROUPS
from workbaskets.validators import WorkflowStatus


class UploadTaricForm(forms.ModelForm):
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

        chunk_taric(self.files["taric_file"], batch, record_group=record_group)
        run_batch(batch=batch.name, username=user.username, status=self.data["status"])

        return batch

    class Meta:
        model = models.ImportBatch
        fields = ["name", "split_job", "dependencies"]
