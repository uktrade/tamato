from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.urls import reverse_lazy

from certificates import models
from common.filters import ActiveStateMixin
from common.filters import LazyMultipleChoiceFilter
from common.filters import TamatoFilter
from common.filters import type_choices


class CertificateFilter(TamatoFilter, ActiveStateMixin):
    search_fields = (
        "sid",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is important

    certificate_type = LazyMultipleChoiceFilter(
        choices=type_choices(models.CertificateType.objects.latest_approved()),
        widget=forms.CheckboxSelectMultiple,
        field_name="certificate_type__sid",
        label="Certificate Type",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("certificate-ui-list")

    class Meta:
        model = models.Certificate
        fields = ["search", "certificate_type", "active_state"]
