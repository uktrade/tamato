from unittest.mock import patch

import pytest

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
