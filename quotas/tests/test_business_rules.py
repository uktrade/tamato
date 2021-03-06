from decimal import Decimal

import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from geo_areas.validators import AreaCode
from quotas import business_rules
from quotas.validators import AdministrationMechanism
from quotas.validators import SubQuotaType


pytestmark = pytest.mark.django_db


def test_ON1(make_duplicate_record):
    """Quota order number id + start date must be unique"""

    duplicate = make_duplicate_record(
        factories.QuotaOrderNumberFactory,
        identifying_fields=business_rules.ON1.identifying_fields,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON1().validate(duplicate)


def test_ON2(date_ranges, approved_transaction, unapproved_transaction):
    """There may be no overlap in time of two quota order numbers with the same quota
    order number id.
    """

    existing = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal, transaction=approved_transaction
    )

    order_number = factories.QuotaOrderNumberFactory.create(
        order_number=existing.order_number,
        valid_between=date_ranges.overlap_normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON2().validate(order_number)


def test_ON5(date_ranges, approved_transaction, unapproved_transaction):
    """There may be no overlap in time of two quota order number origins with the same
    quota order number SID and geographical area id.
    """

    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal, transaction=approved_transaction
    )
    existing = factories.QuotaOrderNumberOriginFactory.create(
        order_number=order_number,
        valid_between=date_ranges.starts_with_normal,
        transaction=approved_transaction,
    )

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=existing.geographical_area,
        order_number=order_number,
        valid_between=date_ranges.starts_with_normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON5().validate(origin)


@only_applicable_after("2006-12-31")
def test_ON6(date_ranges):
    """The validity period of the geographical area must span the validity period of the
    quota order number origin.

    Only applies to quota order numbers with a validity start date after 2006-12-31.
    """

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON6().validate(origin)


def test_ON7(date_ranges, approved_transaction, unapproved_transaction):
    """The validity period of the quota order number must span the validity period of
    the quota order number origin.
    """

    order_number = factories.QuotaOrderNumberFactory.create(
        transaction=approved_transaction, valid_between=date_ranges.starts_with_normal
    )
    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON7().validate(origin)


def test_ON8(date_ranges, approved_transaction, unapproved_transaction):
    """The validity period of the quota order number must span the validity period of
    the referencing quota definition.
    """

    order_number = factories.QuotaOrderNumberFactory.create(
        transaction=approved_transaction, valid_between=date_ranges.starts_with_normal
    )
    quota_def = factories.QuotaDefinitionFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON8().validate(quota_def)


@only_applicable_after("2007-12-31")
def test_ON9(date_ranges):
    """When a quota order number is used in a measure then the validity period of the
    quota order number must span the validity period of the measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal
    )
    factories.MeasureFactory.create(
        order_number=order_number, valid_between=date_ranges.overlap_normal
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON9().validate(order_number)


@only_applicable_after("2007-12-31")
def test_ON10(date_ranges):
    """When a quota order number is used in a measure then the validity period of the
    quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON10().validate(
            measure.order_number.quotaordernumberorigin_set.first()
        )


@only_applicable_after("2007-12-31")
def test_ON11(delete_record):
    """The quota order number cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON11().validate(delete_record(measure.order_number))


@only_applicable_after("2007-12-31")
def test_ON12(delete_record):
    """The quota order number origin cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON12().validate(
            delete_record(measure.order_number.quotaordernumberorigin_set.first())
        )


@pytest.mark.parametrize(
    "area_code, expect_error",
    [
        (AreaCode.COUNTRY, True),
        (AreaCode.GROUP, False),
        (AreaCode.REGION, True),
    ],
)
def test_ON13(area_code, expect_error):
    """An exclusion can only be entered if the order number origin is a geographical
    area group (area code = 1).
    """

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__area_code=area_code
    )
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(origin=origin)

    try:
        business_rules.ON13().validate(exclusion)
    except BusinessRuleViolation as e:
        if not expect_error:
            raise e
    else:
        if expect_error:
            pytest.fail(msg="Did not raise BusinessRuleViolation")


def test_ON14():
    """The excluded geographical area must be a member of the geographical area group."""

    membership = factories.GeographicalMembershipFactory.create()
    non_member = factories.GeographicalAreaFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON14().validate(
            factories.QuotaOrderNumberOriginExclusionFactory.create(
                origin__geographical_area=membership.geo_group,
                excluded_geographical_area=non_member,
            )
        )

    business_rules.ON14().validate(
        factories.QuotaOrderNumberOriginExclusionFactory.create(
            origin__geographical_area=membership.geo_group,
            excluded_geographical_area=membership.member,
        )
    )


def test_QD1(make_duplicate_record):
    """Quota order number id + start date must be unique"""

    duplicate = make_duplicate_record(
        factories.QuotaDefinitionFactory,
        identifying_fields=business_rules.QD1.identifying_fields,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD1().validate(duplicate)


def test_QD2(date_ranges):
    """The start date must be less than or equal to the end date"""

    with pytest.raises(DataError):
        factories.QuotaDefinitionFactory.create(valid_between=date_ranges.backwards)


def test_QD7(date_ranges):
    """The validity period of the quota definition must be spanned by one of the
    validity periods of the referenced quota order number.
    """
    # "one of the validity periods" suggests an order number can have more than one
    # validity period, but this is not true. QD7 mirrors ON8, to check the same
    # constraint whether adding a quota definition or an order number.

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD7().validate(
            factories.QuotaDefinitionFactory.create(
                order_number__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )


def test_QD8(date_ranges):
    """The validity period of the monetary unit code must span the validity period of
    the quota definition.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD8().validate(
            factories.QuotaDefinitionFactory.create(
                monetary_unit__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )


@pytest.mark.skip(reason="Using GBP, not EUR")
def test_QD9():
    """The monetary unit code must always be the Euro ISO code (or Ecu for quota defined
    prior to the Euro Definition).
    """

    assert False


def test_QD10(date_ranges):
    """The validity period of the measurement unit code must span the validity period of
    the quota definition.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD10().validate(
            factories.QuotaDefinitionFactory.create(
                measurement_unit__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )


def test_QD11(date_ranges):
    """The validity period of the measurement unit qualifier code must span the validity
    period of the quota definition.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD11().validate(
            factories.QuotaDefinitionWithQualifierFactory.create(
                measurement_unit_qualifier__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )


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


def test_QA1(make_duplicate_record):
    """The association between two quota definitions must be unique."""

    duplicate = make_duplicate_record(factories.QuotaAssociationFactory)

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA1().validate(duplicate)


def test_QA2(date_ranges):
    """The sub-quota’s validity period must be entirely enclosed within the validity
    period of the main quota
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA2().validate(
            factories.QuotaAssociationFactory.create(
                main_quota__valid_between=date_ranges.normal,
                sub_quota__valid_between=date_ranges.overlap_normal,
            )
        )


@pytest.mark.skip(reason="Needs clarification")
def test_QA3():
    """When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main quota.
    """

    assert False


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
        business_rules.QA4().validate(
            factories.QuotaAssociationFactory.create(**kwargs)
        )

    except BusinessRuleViolation:
        if not expect_error:
            raise

    else:
        if expect_error:
            pytest.fail("Did not raise BusinessRuleViolation")


def test_QA5():
    """Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the same
    volume as the ones associated with the parent quota. Moreover it must be defined
    with a coefficient not equal to 1
    """

    existing = factories.EquivalentQuotaAssociationFactory.create(
        sub_quota__volume=Decimal("1000.0")
    )
    assoc = factories.EquivalentQuotaAssociationFactory.create(
        main_quota=existing.main_quota, sub_quota__volume=Decimal("2000.0")
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5().validate(assoc)


def test_QA5_pt2():
    """Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the same
    volume as the ones associated with the parent quota. Moreover it must be defined
    with a coefficient not equal to 1
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5().validate(
            factories.EquivalentQuotaAssociationFactory.create(
                coefficient=Decimal("1.00000")
            )
        )


def test_QA5_pt3(unapproved_transaction):
    """A sub-quota defined with the 'normal' type must have a coefficient of 1"""

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5().validate(
            factories.QuotaAssociationFactory.create(
                coefficient=Decimal("1.20000"),
                sub_quota_relation_type=SubQuotaType.NORMAL,
                transaction=unapproved_transaction,
            )
        )


def test_QA6(unapproved_transaction):
    """Sub-quotas associated with the same main quota must have the same relation type"""

    existing = factories.QuotaAssociationFactory.create(
        sub_quota_relation_type=SubQuotaType.NORMAL
    )
    assoc = factories.QuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA6().validate(assoc)


def test_blocking_of_fcfs_quotas_only():
    """Blocking periods are only applicable to FCFS quotas."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.BlockingOnlyOfFCFSQuotas().validate(
            factories.QuotaBlockingFactory.create(
                quota_definition__order_number__mechanism=AdministrationMechanism.LICENSED
            )
        )


def test_QBP2(date_ranges):
    """The start date of the quota blocking period must be later than or equal to the
    start date of the quota validity period.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.QBP2().validate(
            factories.QuotaBlockingFactory.create(
                quota_definition__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal_earlier,
            )
        )


def test_QBP3(date_ranges):
    """The end date of the quota blocking period must be later than the start date of
    the quota blocking period.
    """

    with pytest.raises(DataError):
        factories.QuotaBlockingFactory.create(valid_between=date_ranges.backwards)


def test_suspension_of_fcfs_quotas_only():
    """Quota suspensions are only applicable to First Come First Served quotas"""

    with pytest.raises(BusinessRuleViolation):
        business_rules.SuspensionsOnlyToFCFSQuotas().validate(
            factories.QuotaSuspensionFactory.create(
                quota_definition__order_number__mechanism=AdministrationMechanism.LICENSED,
            )
        )


def test_QSP2(date_ranges):
    """The validity period of the quota must span the quota suspension period."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.QSP2().validate(
            factories.QuotaSuspensionFactory.create(
                quota_definition__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )
