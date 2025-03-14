import pytest
from django.urls import reverse_lazy

from common.fields import AutoCompleteField
from footnotes.models import Footnote
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("queryset, url_pattern_name, label, help_text, attrs, expected_url"),
    [
        (
            Footnote.objects.all(),
            None,
            "Footnotes",
            "Search for footnotes",
            {"min-length": 2},
            reverse_lazy("footnote-list"),
        ),
        (
            WorkBasket.objects.all(),
            "workbaskets:workbasket-autocomplete-list",
            "Workbaskets",
            "Search for workbaskets",
            {},
            reverse_lazy("workbaskets:workbasket-autocomplete-list"),
        ),
    ],
)
def test_autocompletefield_url_pattern_name(
    queryset,
    url_pattern_name,
    label,
    help_text,
    attrs,
    expected_url,
):
    """Tests that a custom URL pattern name can be provided for resolving the
    API source URL of the field's autocomplete widget."""
    field = AutoCompleteField(
        queryset=queryset,
        url_pattern_name=url_pattern_name,
        label=label,
        help_text=help_text,
        attrs=attrs,
    )

    assert not field.queryset.difference(queryset)
    assert field.label == label
    assert field.help_text == help_text
    for key, value in attrs.items():
        assert field.widget.attrs.get(key) == value
    assert field.widget.attrs.get("source_url") == expected_url
