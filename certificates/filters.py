from crispy_forms_gds.choices import Choice
from django import forms
from django.contrib.postgres.aggregates import StringAgg
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from certificates import models
from common.filters import ActiveStateMixin
from common.filters import LazyMultipleChoiceFilter
from common.filters import TamatoFilter
from common.jinja2 import break_words


def certificate_type_choices():
    certificate_types = models.CertificateType.objects.current()
    return [
        Choice(
            certificate_type.sid,
            mark_safe(
                "{0} - {1}".format(
                    certificate_type.sid,
                    break_words(certificate_type.description),
                ),
            ),
        )
        for certificate_type in certificate_types
    ]


class CertificateFilter(TamatoFilter, ActiveStateMixin):
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

    clear_url = reverse_lazy("certificate-ui-list")

    class Meta:
        model = models.Certificate
        fields = ["search", "certificate_type", "active_state"]
