from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Layout
from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from importer import models
from importer.chunker import chunk_taric
from importer.management.commands.run_import_batch import run_batch
from workbaskets.validators import WorkflowStatus


class UploadTaricForm(forms.ModelForm):
    status = forms.ChoiceField(choices=WorkflowStatus.choices, required=True)
    taric_file = forms.FileField(required=True)

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

        chunk_taric(self.files["taric_file"], batch)
        run_batch(batch=batch.name, username=user.username, status=self.data["status"])

        return batch

    class Meta:
        model = models.ImportBatch
        fields = ["name", "split_job", "dependencies"]
