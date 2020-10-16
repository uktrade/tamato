from typing import Iterable
from typing import Optional
from typing import Type
from typing import Union

import pytest
from django.core.exceptions import ValidationError
from factory.django import DjangoModelFactory

from common.models import TrackedModel
from common.serializers import TrackedModelSerializer
from common.tests import factories
from common.tests.util import generate_test_import_xml as taric_xml
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from measures import serializers
from workbaskets.validators import WorkflowStatus


@pytest.fixture
def component_applicability():
    def check(field_name, value, factory=None, applicability_field=None):
        if applicability_field is None:
            applicability_field = f"duty_expression__{field_name}_applicability_code"

        if factory is None:
            factory = factories.MeasureComponentFactory

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.MANDATORY,
                    field_name: None,
                }
            )

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.NOT_PERMITTED,
                    field_name: value,
                }
            )

        return True

    return check


@pytest.fixture
def imported_fields_match(valid_user):
    """Provides a function for checking a model can be imported correctly.

    The function takes the following parameters:
        model: A model instance, or a factory class used to build the model.
            This model should not already exist in the database.
        serializer: An optional serializer class to convert the model to its TARIC XML
            representation. If not provided, the function attempts to use a serializer
            class named after the model, eg measures.serializers.<model-class-name>Serializer

    The function serializes the model to TARIC XML, inputs this to the importer, then
    fetches the newly created model from the database and compares the fields.

    It returns True if there are no discrepancies, allowing it to be used with `assert`.
    """

    def check(
        model: Union[TrackedModel, Type[DjangoModelFactory]],
        serializer: Optional[Type[TrackedModelSerializer]] = None,
    ) -> bool:
        if isinstance(model, type) and issubclass(model, DjangoModelFactory):
            model = model.build(update_type=UpdateType.CREATE)

        assert isinstance(
            model, TrackedModel
        ), "Either a factory or an object instance needs to be provided"

        if serializer is None:
            serializer = getattr(serializers, f"{model.__class__.__name__}Serializer")

        xml = taric_xml(serializer(model, context={"format": "xml"}).data)

        import_taric(
            xml,
            valid_user.username,
            WorkflowStatus.PUBLISHED,
        )
        imported = model.get_latest_version()

        checked_fields = (
            set(field.name for field in imported._meta.fields)
            - set(field.name for field in TrackedModel._meta.fields)
            - {"trackedmodel_ptr"}
        )

        for field in checked_fields:
            imported_value = getattr(imported, field)
            source_value = getattr(model, field)
            assert (
                imported_value == source_value
            ), f"imported '{field}' ({imported_value} - {type(imported_value)}) does not match source '{field}' ({source_value} - {type(source_value)})"

        return True

    return check
