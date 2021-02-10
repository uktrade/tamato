from datetime import date

from crispy_forms_gds.choices import Choice
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Q
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from certificates import models
from common.filters import ACTIVE_STATE_CHOICES
from common.filters import LazyMultipleChoiceFilter
from common.filters import TamatoFilter
from common.jinja2 import break_words
from common.util import TaricDateRange


def certificate_type_choices():
    certificate_types = models.CertificateType.objects.current()
    return [
        Choice(
            certificate_type.sid,
            "{0} - {1}".format(
                certificate_type.sid, break_words(certificate_type.description)
            ),
        )
        for certificate_type in certificate_types
    ]


class CertificateFilter(TamatoFilter):
    search_fields = (
        "sid",
        StringAgg("descriptions__description", delimiter=" "),
    )  # XXX order is important

    certificate_type = LazyMultipleChoiceFilter(
        choices=certificate_type_choices,
        widget=forms.CheckboxSelectMultiple,
        field_name="certificate_type__sid",
        label="Certificate Type",
        help_text="Select all that apply",
        required=False,
    )

    active_state = MultipleChoiceFilter(
        choices=ACTIVE_STATE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        method="filter_active_state",
        label="Active state",
        help_text="Select all that apply",
        required=False,
    )

    clear_url = reverse_lazy("certificate-ui-list")

    def filter_active_state(self, queryset, name, value):

        active_status_filter = Q()
        current_date = TaricDateRange(date.today(), date.today())
        if value == ["active"]:
            active_status_filter = Q(valid_between__upper_inf=True) | Q(
                valid_between__contains=current_date
            )
        if value == ["terminated"]:
            active_status_filter = Q(valid_between__fully_lt=current_date)

        return queryset.filter(active_status_filter)

    class Meta:
        model = models.Certificate
        fields = []
