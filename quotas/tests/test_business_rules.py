from collections import defaultdict
from decimal import Decimal

import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from quotas import business_rules
from quotas.validators import AdministrationMechanism
from quotas.validators import SubQuotaType

pytestmark = pytest.mark.django_db


def test_ON1(make_duplicate_record):
    """Quota order number id + start date must be unique."""

    duplicate = make_duplicate_record(
        factories.QuotaOrderNumberFactory,
        identifying_fields=business_rules.ON1.identifying_fields,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON1(duplicate.transaction).validate(duplicate)


def test_ON2(date_ranges, approved_transaction, unapproved_transaction):
    """There may be no overlap in time of two quota order numbers with the same
    quota order number id."""

    existing = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
    )

    order_number = factories.QuotaOrderNumberFactory.create(
        order_number=existing.order_number,
        valid_between=date_ranges.overlap_normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON2(order_number.transaction).validate(order_number)


def test_ON5(date_ranges, approved_transaction, unapproved_transaction):
    """There may be no overlap in time of two quota order number origins with
    the same quota order number SID and geographical area id."""

    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
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
        business_rules.ON5(origin.transaction).validate(origin)


@only_applicable_after("2006-12-31")
def test_ON6(date_ranges):
    """
    The validity period of the geographical area must span the validity period
    of the quota order number origin.

    Only applies to quota order numbers with a validity start date after
    2006-12-31.
    """

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON6(origin.transaction).validate(origin)


def test_ON7(date_ranges, approved_transaction, unapproved_transaction):
    """The validity period of the quota order number must span the validity
    period of the quota order number origin."""

    order_number = factories.QuotaOrderNumberFactory.create(
        transaction=approved_transaction,
        valid_between=date_ranges.starts_with_normal,
    )
    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON7(origin.transaction).validate(origin)


def test_ON8(date_ranges, approved_transaction, unapproved_transaction):
    """The validity period of the quota order number must span the validity
    period of the referencing quota definition."""

    order_number = factories.QuotaOrderNumberFactory.create(
        transaction=approved_transaction,
        valid_between=date_ranges.starts_with_normal,
    )
    quota_def = factories.QuotaDefinitionFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON8(quota_def.transaction).validate(quota_def)


@only_applicable_after("2007-12-31")
def test_ON9(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
    )
    measure = factories.MeasureFactory.create(
        order_number=order_number,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON9(measure.transaction).validate(order_number)


@only_applicable_after("2007-12-31")
def test_ON10(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON10(measure.transaction).validate(
            measure.order_number.quotaordernumberorigin_set.first(),
        )


@only_applicable_after("2007-12-31")
def test_ON11(delete_record):
    """
    The quota order number cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create()
    deleted = delete_record(measure.order_number)
    with pytest.raises(BusinessRuleViolation):
        business_rules.ON11(deleted.transaction).validate(deleted)


@only_applicable_after("2007-12-31")
def test_ON12(delete_record):
    """
    The quota order number origin cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create()
    deleted = delete_record(measure.order_number.quotaordernumberorigin_set.first())

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON12(deleted.transaction).validate(deleted)


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
        geographical_area__area_code=area_code,
    )
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(origin=origin)

    try:
        business_rules.ON13(exclusion.transaction).validate(exclusion)
    except BusinessRuleViolation as e:
        if not expect_error:
            raise e
    else:
        if expect_error:
            pytest.fail(msg="Did not raise BusinessRuleViolation")


def test_ON14():
    """The excluded geographical area must be a member of the geographical area
    group."""

    membership = factories.GeographicalMembershipFactory.create()
    non_member = factories.GeographicalAreaFactory.create()
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(
        origin__geographical_area=membership.geo_group,
        excluded_geographical_area=non_member,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON14(exclusion.transaction).validate(exclusion)

    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(
        origin__geographical_area=membership.geo_group,
        excluded_geographical_area=membership.member,
    )

    business_rules.ON14(exclusion.transaction).validate(exclusion)


def test_CertificatesMustExist():
    """The referenced certificates must exist."""
    quota_order_number = factories.QuotaOrderNumberFactory.create(
        required_certificates=[factories.CertificateFactory.create()],
    )

    certificate = quota_order_number.required_certificates.first()
    certificate.delete()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CertificatesMustExist(certificate.transaction).validate(
            certificate,
        )


def test_CertificateValidityPeriodMustSpanQuotaOrderNumber(date_ranges):
    """The validity period of the required certificates must span the validity
    period of the quota order number."""

    quota_order_number = factories.QuotaOrderNumberFactory.create(
        valid_between=date_ranges.normal,
        required_certificates=[
            factories.CertificateFactory.create(valid_between=date_ranges.earlier),
        ],
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CertificateValidityPeriodMustSpanQuotaOrderNumber(
            quota_order_number.transaction,
        ).validate(quota_order_number)


def test_QD1(make_duplicate_record):
    """Quota order number id + start date must be unique."""

    duplicate = make_duplicate_record(
        factories.QuotaDefinitionFactory,
        identifying_fields=business_rules.QD1.identifying_fields,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD1(duplicate.transaction).validate(duplicate)


def test_QD2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.QuotaDefinitionFactory.create(valid_between=date_ranges.backwards)


def test_QD7(date_ranges):
    """The validity period of the quota definition must be spanned by one of the
    validity periods of the referenced quota order number."""
    # "one of the validity periods" suggests an order number can have more than one
    # validity period, but this is not true. QD7 mirrors ON8, to check the same
    # constraint whether adding a quota definition or an order number.
    definition = factories.QuotaDefinitionFactory.create(
        order_number__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.QD7(definition.transaction).validate(definition)


def test_QD8(date_ranges):
    """The validity period of the monetary unit code must span the validity
    period of the quota definition."""
    definition = factories.QuotaDefinitionFactory.create(
        monetary_unit__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD8(definition.transaction).validate(definition)


@pytest.mark.skip(reason="Using GBP, not EUR")
def test_QD9():
    """The monetary unit code must always be the Euro ISO code (or Ecu for quota
    defined prior to the Euro Definition)."""

    assert False


def test_QD10(date_ranges):
    """The validity period of the measurement unit code must span the validity
    period of the quota definition."""
    definition = factories.QuotaDefinitionFactory.create(
        measurement_unit__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QD10(definition.transaction).validate(definition)


def test_QD11(date_ranges):
    """The validity period of the measurement unit qualifier code must span the
    validity period of the quota definition."""
    definition = factories.QuotaDefinitionWithQualifierFactory.create(
        measurement_unit_qualifier__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.QD11(definition.transaction).validate(definition)


@pytest.mark.skip("Quota events are not supported")
def test_QD12():
    """If quota events exist for a quota definition, the start date of the quota
    definition cannot be brought forward."""


@pytest.mark.skip("Quota events are not supported")
def test_QD13():
    """If quota events exist for a quota definition, the start date can only be
    postponed up to the date of the first quota event."""


@pytest.mark.skip("Quota events are not supported")
def test_QD14():
    """If quota events exist for a quota definition, the end date of the quota
    definition can be postponed."""


@pytest.mark.skip("Quota events are not supported")
def test_QD15():
    """If quota events exist for a quota definition, the end date can only be
    brought forward up to the date of the last quota event on that quota
    definition."""


def test_prevent_quota_definition_deletion(unapproved_transaction, date_ranges):
    """
    QAM does not like handling deletions of active Quota Definitions.

    Ensure an active Quota Definition cannot be deleted.
    """
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=date_ranges.future,
    )
    deleted = quota_definition.new_draft(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.PreventQuotaDefinitionDeletion(deleted.transaction).validate(
            deleted,
        )

    quota_definition.valid_between = date_ranges.earlier
    deleted = quota_definition.new_draft(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )

    business_rules.PreventQuotaDefinitionDeletion(deleted.transaction).validate(deleted)


@pytest.mark.parametrize(
    "factory,business_rule,quota_attr",
    [
        (
            factories.QuotaAssociationFactory,
            business_rules.QuotaAssociationMustReferToANonDeletedSubQuota,
            "sub_quota",
        ),
        (
            factories.QuotaSuspensionFactory,
            business_rules.QuotaSuspensionMustReferToANonDeletedQuotaDefinition,
            "quota_definition",
        ),
        (
            factories.QuotaBlockingFactory,
            business_rules.QuotaBlockingPeriodMustReferToANonDeletedQuotaDefinition,
            "quota_definition",
        ),
    ],
)
def test_linking_models_must_refer_to_a_non_deleted_sub_quota(
    unapproved_transaction,
    factory,
    business_rule,
    quota_attr,
):
    """Ensure a Quota Definition cannot be deleted if referred to by another
    linking quota model."""

    linking_model = factory.create()
    quota_definition = getattr(linking_model, quota_attr)

    deleted = quota_definition.new_draft(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rule(deleted.transaction).validate(deleted)

    linking_model.update_type = UpdateType.DELETE
    linking_model.save(force_write=True)
    deleted = quota_definition.new_draft(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )
    business_rule(deleted.transaction).validate(deleted)


def test_QA1(make_duplicate_record):
    """The association between two quota definitions must be unique."""

    duplicate = make_duplicate_record(factories.QuotaAssociationFactory)

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA1(duplicate.transaction).validate(duplicate)


def test_QA2(date_ranges):
    """The sub-quota’s validity period must be entirely enclosed within the
    validity period of the main quota."""
    association = factories.QuotaAssociationFactory.create(
        main_quota__valid_between=date_ranges.normal,
        sub_quota__valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA2(association.transaction).validate(association)


@pytest.mark.parametrize(
    "main_volume, main_unit, sub_volume, sub_unit, expect_error",
    [
        (1.0, "KGM", 1.0, "KGM", False),
        (1.0, "KGM", 0.0, "KGM", False),
        (2.0, "KGM", 1.0, "KGM", False),
        (1.0, "KGM", 2.0, "KGM", True),
        (1.0, "KGM", 1.0, "DTN", True),
        (1.0, "DTN", 1.0, "DTN", False),
    ],
)
def test_QA3(main_volume, main_unit, sub_volume, sub_unit, expect_error):
    """When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main
    quota."""

    units = defaultdict(factories.MeasurementUnitFactory)

    try:
        assoc = factories.QuotaAssociationFactory(
            main_quota__volume=main_volume,
            main_quota__measurement_unit=units[main_unit],
            sub_quota__volume=sub_volume,
            sub_quota__measurement_unit=units[sub_unit],
        )
        business_rules.QA3(assoc.transaction).validate(assoc)

    except BusinessRuleViolation:
        if not expect_error:
            raise

    else:
        if expect_error:
            pytest.fail("Did not raise BusinessRuleViolation")


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
    """
    Whenever a sub-quota receives a coefficient, this has to be a strictly
    positive decimal number.

    When it is not specified a value of 1 is always assumed
    """

    kwargs = {}
    if coefficient is not None:
        kwargs["coefficient"] = coefficient

    assoc = factories.QuotaAssociationFactory.create(**kwargs)

    try:
        business_rules.QA4(assoc.transaction).validate(assoc)

    except BusinessRuleViolation:
        if not expect_error:
            raise

    else:
        if expect_error:
            pytest.fail("Did not raise BusinessRuleViolation")


def test_QA5():
    """
    Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the
    same volume as the ones associated with the parent quota.

    Moreover it must be defined with a coefficient not equal to 1
    """

    existing = factories.EquivalentQuotaAssociationFactory.create(
        sub_quota__volume=Decimal("1000.0"),
    )
    assoc = factories.EquivalentQuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota__volume=Decimal("2000.0"),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5(assoc.transaction).validate(assoc)


def test_QA5_pt2():
    """
    Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the
    same volume as the ones associated with the parent quota.

    Moreover it must be defined with a coefficient not equal to 1
    """
    assoc = factories.EquivalentQuotaAssociationFactory.create(
        coefficient=Decimal("1.00000"),
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5(assoc.transaction).validate(assoc)


def test_QA5_pt3(unapproved_transaction):
    """A sub-quota defined with the 'normal' type must have a coefficient of
    1."""
    assoc = factories.QuotaAssociationFactory.create(
        coefficient=Decimal("1.20000"),
        sub_quota_relation_type=SubQuotaType.NORMAL,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA5(assoc.transaction).validate(assoc)


def test_QA6(unapproved_transaction):
    """Sub-quotas associated with the same main quota must have the same
    relation type."""

    existing = factories.QuotaAssociationFactory.create(
        sub_quota_relation_type=SubQuotaType.NORMAL,
    )
    assoc = factories.QuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
        transaction=unapproved_transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA6(assoc.transaction).validate(assoc)


def test_blocking_of_fcfs_quotas_only():
    """Blocking periods are only applicable to FCFS quotas."""
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition__order_number__mechanism=AdministrationMechanism.LICENSED,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.BlockingOnlyOfFCFSQuotas(blocking.transaction).validate(blocking)


def test_QBP2(date_ranges):
    """The start date of the quota blocking period must be later than or equal
    to the start date of the quota validity period."""
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal_earlier,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QBP2(blocking.transaction).validate(blocking)


def test_QBP3(date_ranges):
    """The end date of the quota blocking period must be later than the start
    date of the quota blocking period."""

    with pytest.raises(DataError):
        factories.QuotaBlockingFactory.create(valid_between=date_ranges.backwards)


def test_suspension_of_fcfs_quotas_only():
    """Quota suspensions are only applicable to First Come First Served
    quotas."""
    suspension = factories.QuotaSuspensionFactory.create(
        quota_definition__order_number__mechanism=AdministrationMechanism.LICENSED,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.SuspensionsOnlyToFCFSQuotas(suspension.transaction).validate(
            suspension,
        )


def test_QSP2(date_ranges):
    """The validity period of the quota must span the quota suspension
    period."""
    suspension = factories.QuotaSuspensionFactory.create(
        quota_definition__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QSP2(suspension.transaction).validate(suspension)
