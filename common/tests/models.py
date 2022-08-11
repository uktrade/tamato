"""These models are for testing purposes only and will not be migrated into the
database outside of a test environment."""
from typing import List

from django.db import models

from common.fields import NumericSID
from common.fields import ShortDescription
from common.models import TrackedModel
from common.models.mixins.description import DescribedMixin
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from common.validators import UpdateType


class TestModel1(TrackedModel, ValidityMixin, DescribedMixin):
    __test__ = False
    record_code = "01"
    subrecord_code = "01"

    taric_template = "test_template"

    identifying_fields = ("sid",)

    sid = NumericSID()
    name = models.CharField(max_length=24, null=True)


class TestModel2(TrackedModel, ValidityMixin):
    __test__ = False
    record_code = "02"
    subrecord_code = "01"

    custom_sid = models.PositiveIntegerField()
    description = models.CharField(max_length=24, null=True)

    identifying_fields = ("custom_sid",)


class TestModel3(TrackedModel, ValidityMixin):
    __test__ = False
    record_code = "03"
    subrecord_code = "01"

    sid = models.PositiveIntegerField()
    linked_model = models.ForeignKey(TestModel1, null=True, on_delete=models.PROTECT)


class TestModelDescription1(DescriptionMixin, TrackedModel):
    __test__ = False
    record_code = "01"
    subrecord_code = "02"

    identifying_fields = (
        "described_record__sid",
        "validity_start",
    )

    described_record = models.ForeignKey(
        TestModel1,
        on_delete=models.PROTECT,
        related_name="descriptions",
    )
    description = ShortDescription()


def generate_model_history(factory, number=5, **kwargs) -> List:
    objects = []
    kwargs["update_type"] = kwargs.get("update_type", UpdateType.CREATE)
    current = factory.create(**kwargs)
    objects.append(current)
    kwargs["update_type"] = UpdateType.UPDATE
    kwargs["version_group"] = kwargs.get("version_group", current.version_group)
    for _ in range(number - 1):
        current = factory.create(**kwargs)
        objects.append(current)

    return objects


def model_with_history(factory, date_ranges, **kwargs):
    class Models:
        """
        A convenient system to store tracked models.

        Creates a number of historic models for both test model types.

        Creates an active model for each test model type.

        Then creates a number of future models for each type as well.
        """

        all_models = generate_model_history(
            factory, valid_between=date_ranges.earlier, **kwargs
        )

        active_model = factory.create(
            valid_between=date_ranges.current, update_type=UpdateType.UPDATE, **kwargs
        )

        all_models.append(active_model)

        all_models.extend(
            generate_model_history(
                factory,
                valid_between=date_ranges.future,
                update_type=UpdateType.UPDATE,
                **kwargs,
            ),
        )

    return Models
