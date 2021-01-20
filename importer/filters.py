from django import forms
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from common.filters import TamatoFilter
from importer import models


class ImportBatchFilter(TamatoFilter):
    """
    FilterSet for Import Batches.
    """

    search_fields = ("name",)

    clear_url = reverse_lazy("import_batch-ui-list")

    status = MultipleChoiceFilter(
        choices=models.ImporterChunkStatus.choices,
        widget=forms.CheckboxSelectMultiple,
        method="filter_status",
        label="Import status",
        help_text="Select all that apply",
        required=False,
    )

    def filter_status(self, queryset, name, value):
        if value:
            queryset = queryset.filter(chunks__status__in=value)
        return queryset

    class Meta:
        model = models.ImportBatch
        fields = []
