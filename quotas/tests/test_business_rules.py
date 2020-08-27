from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import DataError

from common.tests import factories
from common.tests.util import requires_measures
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from quotas.validators import AdministrationMechanism
from quotas.validators import SubQuotaType
from workbaskets.validators import WorkflowStatus


pytestmark = pytest.mark.django_db


@pytest.fixture
def published():
    return factories.WorkBasketFactory(status=WorkflowStatus.PUBLISHED)


def test_ON1(published):
    """Quota order number id + start date must be unique"""

    existing = factories.QuotaOrderNumberFactory(
        workbasket=published, update_type=UpdateType.CREATE
    )

    order_number = factories.QuotaOrderNumberFactory(
        order_number=existing.order_number,
        valid_between=existing.valid_between,
        update_type=UpdateType.CREATE,
    )

    with pytest.raises(ValidationError):
        order_number.workbasket.submit_for_approval()


def test_ON2(date_ranges, published):
    """There may be no overlap in time of two quota order numbers with the same quota
    order number id.
    """

    existing = factories.QuotaOrderNumberFactory(
        valid_between=date_ranges.normal, workbasket=published
    )

    order_number = factories.QuotaOrderNumberFactory(
        order_number=existing.order_number,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(ValidationError):
        order_number.workbasket.submit_for_approval()


def test_ON5(date_ranges, published):
    """There may be no overlap in time of two quota order number origins with the same
    quota order number SID and geographical area id.
    """

    order_number = factories.QuotaOrderNumberFactory(
        valid_between=date_ranges.normal, workbasket=published
    )
    existing = factories.QuotaOrderNumberOriginFactory(
        order_number=order_number,
        valid_between=date_ranges.starts_with_normal,
        workbasket=published,
    )

    origin = factories.QuotaOrderNumberOriginFactory(
        geographical_area=existing.geographical_area,
        order_number=order_number,
        update_type=UpdateType.CREATE,
        valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(ValidationError):
        origin.workbasket.submit_for_approval()


def test_ON6(date_ranges, published):
    """The validity period of the geographical area must span the validity period of the
    quota order number origin.
    """

    geo_area = factories.GeographicalAreaFactory(
        workbasket=published, valid_between=date_ranges.starts_with_normal
    )
    origin = factories.QuotaOrderNumberOriginFactory(
        geographical_area=geo_area,
        update_type=UpdateType.CREATE,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(ValidationError):
        origin.workbasket.submit_for_approval()


def test_ON7(date_ranges, published):
    """The validity period of the quota order number must span the validity period of
    the quota order number origin.
    """

    order_number = factories.QuotaOrderNumberFactory(
        workbasket=published, valid_between=date_ranges.starts_with_normal
    )
    origin = factories.QuotaOrderNumberOriginFactory(
        order_number=order_number,
        update_type=UpdateType.CREATE,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(ValidationError):
        origin.workbasket.submit_for_approval()


def test_ON8(date_ranges, published):
    """The validity period of the quota order number must span the validity period of
    the referencing quota definition.
    """

    order_number = factories.QuotaOrderNumberFactory(
        workbasket=published, valid_between=date_ranges.starts_with_normal
    )
    quota_def = factories.QuotaDefinitionFactory(
        order_number=order_number,
        update_type=UpdateType.CREATE,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(ValidationError):
        quota_def.workbasket.submit_for_approval()


@requires_measures
def test_ON9(date_ranges, published):
    """When a quota order number is used in a measure then the validity period of the
    quota order number must span the validity period of the measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """


@requires_measures
def test_ON10(date_ranges, published):
    """When a quota order number is used in a measure then the validity period of the
    quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """


@requires_measures
def test_ON11():
    """The quota order number cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """


@requires_measures
def test_ON12():
    """The quota order number origin cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """


@pytest.mark.parametrize(
    "area_code, expect_error",
    [
        (AreaCode.COUNTRY, True),
        (AreaCode.GROUP, False),
        (AreaCode.REGION, True),
    ],
)
def test_ON13(date_ranges, published, area_code, expect_error):
    """An exclusion can only be entered if the order number origin is a geographical
    area group (area code = 1).
    """

    geo_area = factories.GeographicalAreaFactory(
        area_code=area_code, workbasket=published
    )
    member_area = factories.GeographicalAreaFactory(
        area_code=AreaCode.COUNTRY,
        workbasket=published,
    )
    if area_code == AreaCode.GROUP:
        factories.GeographicalMembershipFactory(
            geo_group=geo_area,
            member=member_area,
        )
    origin = factories.QuotaOrderNumberOriginFactory(
        geographical_area=geo_area,
        workbasket=published,
    )
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory(
        origin=origin, excluded_geographical_area=member_area
    )

    try:
        exclusion.workbasket.submit_for_approval()
    except ValidationError as e:
        if not expect_error:
            raise e
    else:
        if expect_error:
            pytest.fail("Did not raise ValidationError")


def test_ON14(published):
    """The excluded geographical area must be a member of the geographical area group."""

    origin = factories.QuotaOrderNumberOriginFactory(
        geographical_area=factories.GeographicalAreaFactory(
            area_code=AreaCode.GROUP, workbasket=published
        ),
        workbasket=published,
    )
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory(origin=origin)

    with pytest.raises(ValidationError):
        exclusion.workbasket.submit_for_approval()


def test_QD1(published):
    """Quota order number id + start date must be unique"""

    existing = factories.QuotaDefinitionFactory(
        workbasket=published, update_type=UpdateType.CREATE
    )

    definition = factories.QuotaDefinitionFactory(
        order_number=existing.order_number,
        valid_between=existing.valid_between,
        update_type=UpdateType.CREATE,
    )

    with pytest.raises(ValidationError):
        definition.workbasket.submit_for_approval()


def test_QD2(date_ranges):
    """The start date must be less than or equal to the end date"""

    with pytest.raises(DataError):
        factories.QuotaDefinitionFactory(valid_between=date_ranges.backwards)


def test_QD7(date_ranges, published):
    """The validity period of the quota definition must be spanned by one of the
    validity periods of the referenced quota order number.
    """
    # "one of the validity periods" suggests an order number can have more than one
    # validity period, but this is not true. QD7 mirrors ON8, to check the same
    # constraint whether adding a quota definition or an order number.

    order_number = factories.QuotaOrderNumberFactory(
        valid_between=date_ranges.normal, workbasket=published
    )
    definition = factories.QuotaDefinitionFactory(
        order_number=order_number,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(ValidationError):
        definition.workbasket.submit_for_approval()


@requires_measures
def test_QD8():
    """The validity period of the monetary unit code must span the validity period of
    the quota definition.
    """


@requires_measures
def test_QD9():
    """The monetary unit code must always be the Euro ISO code (or Ecu for quota defined
    prior to the Euro Definition).
    """


@requires_measures
def test_QD10():
    """The validity period of the measurement unit code must span the validity period of
    the quota definition.
    """


@requires_measures
def test_QD11():
    """The validity period of the measurement unit qualifier code must span the validity
    period of the quota definition.
    """


@pytest.mark.skip("Quota events are not supported")
def test_QD12():
    """If quota events exist for a quota definition, the start date of the quota
    definition cannot be brought forward.
    """


@pytest.mark.skip("Quota events are not supported")
def test_QD13():
    """If quota events exist for a quota definition, the start date can only be
    postponed up to the date of the first quota event.
    """


@pytest.mark.skip("Quota events are not supported")
def test_QD14():
    """If quota events exist for a quota definition, the end date of the quota
    definition can be postponed.
    """


@pytest.mark.skip("Quota events are not supported")
def test_QD15():
    """If quota events exist for a quota definition, the end date can only be brought
    forward up to the date of the last quota event on that quota definition.
    """


def test_QA1(published):
    """The association between two quota definitions must be unique."""

    existing = factories.QuotaAssociationFactory(workbasket=published)

    assoc = factories.QuotaAssociationFactory(
        main_quota=existing.main_quota,
        sub_quota=existing.sub_quota,
        update_type=UpdateType.CREATE,
    )

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


def test_QA2(date_ranges, published):
    """The sub-quota’s validity period must be entirely enclosed within the validity
    period of the main quota
    """

    main = factories.QuotaDefinitionFactory(
        valid_between=date_ranges.normal, workbasket=published
    )
    sub = factories.QuotaDefinitionFactory(
        valid_between=date_ranges.overlap_normal, workbasket=published
    )
    assoc = factories.QuotaAssociationFactory(main_quota=main, sub_quota=sub)

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


@requires_measures
def test_QA3():
    """When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main quota.
    """


@pytest.mark.parametrize(
    "coefficient, expect_error",
    [
        (None, False),
        (1.0, False),
        (2.0, False),
        (0.0, True),
        (-1.0, True),
    ],
)
def test_QA4(coefficient, expect_error):
    """Whenever a sub-quota receives a coefficient, this has to be a strictly positive
    decimal number. When it is not specified a value of 1 is always assumed
    """

    kwargs = {}
    if coefficient is not None:
        kwargs["coefficient"] = coefficient

    try:
        factories.QuotaAssociationFactory(**kwargs)

    except ValidationError:
        if not expect_error:
            raise

    else:
        if expect_error:
            pytest.fail("Did not raise ValidationError")


def test_QA5(published):
    """Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the same
    volume as the ones associated with the parent quota. Moreover it must be defined
    with a coefficient not equal to 1
    """

    sub1 = factories.QuotaDefinitionFactory(volume=23000, workbasket=published)
    sub2 = factories.QuotaDefinitionFactory(volume=10000, workbasket=published)
    existing = factories.QuotaAssociationFactory(
        coefficient=Decimal("1.20000"),
        sub_quota=sub1,
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
        workbasket=published,
    )
    assoc = factories.QuotaAssociationFactory(
        coefficient=Decimal("1.20000"),
        main_quota=existing.main_quota,
        sub_quota=sub2,
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
    )

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


def test_QA5_pt2(published):
    """Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the same
    volume as the ones associated with the parent quota. Moreover it must be defined
    with a coefficient not equal to 1
    """

    assoc = factories.QuotaAssociationFactory(
        coefficient=Decimal("1.00000"),
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
    )

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


def test_QA5_pt3(published):
    """A sub-quota defined with the 'normal' type must have a coefficient of 1"""

    assoc = factories.QuotaAssociationFactory(
        coefficient=Decimal("1.20000"),
        sub_quota_relation_type=SubQuotaType.NORMAL,
    )

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


def test_QA6(published):
    """Sub-quotas associated with the same main quota must have the same relation type"""

    existing = factories.QuotaAssociationFactory(
        sub_quota_relation_type=SubQuotaType.NORMAL, workbasket=published
    )
    assoc = factories.QuotaAssociationFactory(
        coefficient=Decimal("1.20000"),
        main_quota=existing.main_quota,
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
    )

    with pytest.raises(ValidationError):
        assoc.workbasket.submit_for_approval()


def test_blocking_of_fcfs_quotas_only(published):
    """Blocking periods are only applicable to FCFS quotas."""

    order_number = factories.QuotaOrderNumberFactory(
        mechanism=AdministrationMechanism.LICENSED, workbasket=published
    )
    definition = factories.QuotaDefinitionFactory(
        workbasket=published,
        order_number=order_number,
    )
    blocking = factories.QuotaBlockingFactory(
        quota_definition=definition,
    )

    with pytest.raises(ValidationError):
        blocking.workbasket.submit_for_approval()


def test_QBP2(date_ranges, published):
    """The start date of the quota blocking period must be later than or equal to the
    start date of the quota validity period.
    """

    definition = factories.QuotaDefinitionFactory(
        valid_between=date_ranges.normal, workbasket=published
    )
    block = factories.QuotaBlockingFactory(
        quota_definition=definition, valid_between=date_ranges.overlap_normal_earlier
    )

    with pytest.raises(ValidationError):
        block.workbasket.submit_for_approval()


def test_QBP3(date_ranges, published):
    """The end date of the quota blocking period must be later than the start date of
    the quota blocking period.
    """

    with pytest.raises(DataError):
        factories.QuotaBlockingFactory(valid_between=date_ranges.backwards)


def test_suspension_of_fcfs_quotas_only(published):
    """Quota suspensions are only applicable to First Come First Served quotas"""

    order_number = factories.QuotaOrderNumberFactory(
        mechanism=AdministrationMechanism.LICENSED, workbasket=published
    )
    definition = factories.QuotaDefinitionFactory(
        workbasket=published,
        order_number=order_number,
    )
    suspension = factories.QuotaSuspensionFactory(
        quota_definition=definition,
    )

    with pytest.raises(ValidationError):
        suspension.workbasket.submit_for_approval()


def test_QSP2(date_ranges, published):
    """The validity period of the quota must span the quota suspension period."""

    definition = factories.QuotaDefinitionFactory(
        workbasket=published, valid_between=date_ranges.starts_with_normal
    )
    suspension = factories.QuotaSuspensionFactory(
        quota_definition=definition,
        update_type=UpdateType.CREATE,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(ValidationError):
        suspension.workbasket.submit_for_approval()
