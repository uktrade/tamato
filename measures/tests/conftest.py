import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError

from common.tests import factories
from common.validators import ApplicabilityCode
from common.validators import UpdateType


@pytest.fixture
def unique_identifying_fields(approved_workbasket):
    """Provides a function for checking a model of the specified factory class cannot be
    created with the same identifying_fields as an existing instance.

    Usage:
        assert unique_identifying_fields(FactoryClass)
    """
    # TODO allow factory or model instance as argument

    def check(factory):
        existing = factory(workbasket=approved_workbasket)

        with pytest.raises(ValidationError):
            duplicate = factory(
                valid_between=existing.valid_between,
                **{
                    field: getattr(existing, field)
                    for field in factory._meta.model.identifying_fields
                },
            )

        return True

    return check


@pytest.fixture
def validity_period_contained(date_ranges, approved_workbasket):
    """Provides a function for checking a model's validity period must be contained
    within the validity period of the specified model.

    Usage:
        assert validity_period_contained("field_name", ContainerModelFactory, ContainedModelFactory)
    """
    # TODO drop the `dependency_name` argument, inspect the model for a ForeignKey to
    # the specified container model. Add `field_name` kwarg for disambiguation if
    # multiple ForeignKeys.

    def check(dependency_name, dependency_factory, dependent_factory):
        dependency = dependency_factory.create(
            workbasket=approved_workbasket, valid_between=date_ranges.starts_with_normal
        )

        with pytest.raises(ValidationError):
            dependent = dependent_factory.create(
                valid_between=date_ranges.normal,
                **{dependency_name: dependency},
            )

        return True

    return check


@pytest.fixture
def must_exist(approved_workbasket):
    """Provides a function for checking a model's foreign key link instance must exist.

    Usage:
        assert must_exist("field_name", LinkedModelFactory, ModelFactory)
    """
    # TODO drop the `dependency_name` argument, as with validity_period_contained

    def check(dependency_name, dependency_factory, dependent_factory):
        dependency = dependency_factory.create(workbasket=approved_workbasket)
        non_existent_id = dependency.pk
        dependency.delete()

        with pytest.raises(ValidationError):
            dependent_factory.create(
                **{f"{dependency_name}_id": non_existent_id},
            )

        return True

    return check


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
