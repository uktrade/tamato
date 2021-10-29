from django import forms
from django.urls import reverse_lazy
from django_filters import MultipleChoiceFilter

from common.filters import AutoCompleteFilter
from common.filters import TamatoFilter
from common.filters import TamatoFilterBackend
from geo_areas.models import GeographicalArea
from quotas import models
from quotas import validators
from quotas.forms import QuotaFilterForm


class OrderNumberFilterBackend(TamatoFilterBackend):
    search_fields = ("order_number",)  # XXX order is significant


class QuotaFilter(TamatoFilter):

    order_number = AutoCompleteFilter(
        label="Order number",
        field_name="order_number",
        queryset=models.QuotaOrderNumber.objects.all(),
    )

    origin = AutoCompleteFilter(
        label="Geographical area(s)",
        field_name="origins",
        queryset=GeographicalArea.objects.all(),
    )

    mechanism = MultipleChoiceFilter(
        label="Administration mechanism",
        field_name="mechanism",
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all that apply",
        choices=validators.AdministrationMechanism.choices,
    )

    category = MultipleChoiceFilter(
        label="Quota category",
        field_name="category",
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all that apply",
        choices=validators.QuotaCategory.choices,
    )

    clear_url = reverse_lazy("quota-ui-list")

    class Meta:
        form = QuotaFilterForm

        model = models.QuotaDefinition
        fields = ["order_number"]
