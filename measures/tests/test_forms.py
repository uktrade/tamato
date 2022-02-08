from unittest.mock import patch

import pytest

from common.tests import factories
from measures.forms import MeasureForm

pytestmark = pytest.mark.django_db


@patch("measures.models.Measure.diff_components")
def test_diff_components_not_called(
    diff_components,
    measure_form,
    duty_sentence_parser,
):
    measure_form.save(commit=False)

    assert diff_components.called == False


@patch("measures.models.Measure.diff_components")
def test_diff_components_called(diff_components, measure_form, duty_sentence_parser):
    measure_form.data.update(duty_sentence="6.000%")
    measure_form.save(commit=False)

    assert diff_components.called == True


def test_error_raised_if_no_duty_sentence(session_request):
    measure = factories.MeasureFactory.create()

    with pytest.raises(
        AttributeError,
        match="Measure instance is missing `duty_sentence` attribute. Try calling `with_duty_sentence` queryset method",
    ):
        MeasureForm(data={}, instance=measure, request=session_request)
