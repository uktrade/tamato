import pytest

from common.tests import factories
from workbaskets.forms import SelectableObjectField
from workbaskets.forms import SelectableObjectsForm
from workbaskets.forms import WorkbasketCreateForm

pytestmark = pytest.mark.django_db


def test_workbasket_form_validation():
    form = WorkbasketCreateForm(
        {
            "title": "some title",
            "reason": "",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors
    assert "reason" in form.errors

    form = WorkbasketCreateForm(
        {
            "title": "",
            "reason": "some reason",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors

    form = WorkbasketCreateForm(
        {
            "title": "some title",
            "reason": "some reason",
        },
    )
    assert not form.is_valid()
    assert "title" in form.errors


def test_workbasket_create_form_valid_data():
    """Test that WorkbasketCreateForm is valid when required fields in data."""
    data = {"title": "123", "reason": "testing testing"}
    form = WorkbasketCreateForm(data=data)

    assert form.is_valid()


def test_workbasket_create_form_invalid_data():
    """Test that WorkbasketCreateForm is not valid when required fields not in
    data."""
    form = WorkbasketCreateForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["title"]
    assert "This field is required." in form.errors["reason"]


def test_selectable_objects_form():
    """Test that the SelectableObjectsForm creates a SelectableObjectField for
    each item passed to it, and the class methods and properties provide the
    expected data for the item."""
    measures = factories.MeasureFactory.create_batch(5)
    form = SelectableObjectsForm(initial={}, prefix=None, objects=measures)
    # grab a list of the ids tacked on to the end of the field name, as this
    # should be the pk of the measure.
    form_fields_keys = [str.partition("_")[2] for str in form.fields.keys()]
    measure_pks = [str(measure.pk) for measure in measures]

    # Check that the fields in the form has the same length as the measures we made.
    assert len(form.fields) == 5
    # Check that the ids added to the end of the field names, match the measure pks.
    assert form_fields_keys == measure_pks
    # Check that the field name class method returns the right name.
    for item in measures:
        assert (
            SelectableObjectsForm.field_name_for_object(measures[measures.index(item)])
            == f"selectableobject_{item.pk}"
        )
    # Check that the id class method returns the right id.
    for item in measures:
        assert (
            SelectableObjectsForm.object_id_from_field_name(
                list(form.fields.keys())[measures.index(item)],
            )
            == measure_pks[measures.index(item)]
        )
    # Check that the cleaned_data_no_prefix property returns a list of the data with no prefixes.
    form.cleaned_data = {
        f"selectableobject_{measure_pks[0]}": True,
        f"selectableobject_{measure_pks[1]}": True,
        f"selectableobject_{measure_pks[2]}": True,
        f"selectableobject_{measure_pks[3]}": False,
        f"selectableobject_{measure_pks[4]}": False,
    }
    # The cleaned_data_no_prefix property is created using cleaned_data, so providing cleaned_data should
    # create the object for us, so we just need to check it matches what we expect.
    assert form.cleaned_data_no_prefix == {
        measure_pks[0]: True,
        measure_pks[1]: True,
        measure_pks[2]: True,
        measure_pks[3]: False,
        measure_pks[4]: False,
    }
    # Check that the fields are of SelectableObjectField type
    for item in measures:
        assert type(form.fields[f"selectableobject_{item.pk}"]) is SelectableObjectField
