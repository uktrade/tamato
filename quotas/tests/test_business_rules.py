from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from common.tests.util import raises_if
from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from quotas import business_rules
from quotas.validators import AdministrationMechanism
from quotas.validators import SubQuotaType

pytestmark = pytest.mark.django_db


@pytest.mark.business_rules
def test_ON1(assert_handles_duplicates):
    """Quota order number id + start date must be unique."""

    assert_handles_duplicates(
        factories.QuotaOrderNumberFactory,
        business_rules.ON1,
        identifying_fields=business_rules.ON1.identifying_fields,
    )


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("existing_range", "new_range", "ranges_overlap"),
    (
        ("normal", "overlap_normal", True),
        ("big", "normal", True),
        ("normal", "later", False),
    ),
)
def test_ON2(date_ranges, existing_range, new_range, ranges_overlap):
    """There may be no overlap in time of two quota order numbers with the same
    quota order number id."""

    existing = factories.QuotaOrderNumberFactory.create(
        valid_between=getattr(date_ranges, existing_range),
    )

    order_number = factories.QuotaOrderNumberFactory.create(
        order_number=existing.order_number,
        valid_between=getattr(date_ranges, new_range),
    )

    with raises_if(BusinessRuleViolation, ranges_overlap):
        business_rules.ON2(order_number.transaction).validate(order_number)


@pytest.mark.business_rules
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


@pytest.mark.business_rules
@only_applicable_after("2006-12-31")
def test_ON6(date_ranges):
    """
    The validity period of the geographical area must span the validity period
    of the quota order number origin.

    Only applies to quota order numbers with a validity start date after
    2006-12-31.
    """

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__valid_between=date_ranges.normal,
        valid_between=date_ranges.normal,
    )

    business_rules.ON6(origin.transaction).validate(origin)

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON6(origin.transaction).validate(origin)


@pytest.mark.business_rules
def test_ON7(assert_spanning_enforced):
    """The validity period of the quota order number must span the validity
    period of the quota order number origin."""

    assert_spanning_enforced(
        factories.QuotaOrderNumberOriginFactory,
        business_rules.ON7,
    )


@pytest.mark.business_rules
def test_ON8(assert_spanning_enforced):
    """The validity period of the quota order number must span the validity
    period of the referencing quota definition."""

    assert_spanning_enforced(
        factories.QuotaDefinitionFactory,
        business_rules.ON8,
    )


@pytest.mark.business_rules
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


@pytest.mark.business_rules
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


@pytest.mark.business_rules
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


@pytest.mark.business_rules
def test_ON12_does_not_raise(delete_record):
    """
    The quota order number origin cannot be deleted if it is used in a measure.

    This rule is only applicable for measure with start date after 31/12/2007.
    """

    # create measure, and quota order and origin
    measure = factories.MeasureWithQuotaFactory.create()

    # add another origin
    origin_without_measure = factories.QuotaOrderNumberOriginFactory.create(
        order_number=measure.order_number,
    )

    # delete record
    deleted = delete_record(origin_without_measure)

    business_rules.ON12(deleted.transaction).validate(deleted)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "area_code, expect_error",
    [
        (AreaCode.COUNTRY, True),
        (AreaCode.GROUP, False),
        (AreaCode.REGION, True),
    ],
)
def test_ON13(area_code, expect_error):
    """An exclusion can only be entered if the order number origin is a
    geographical area group (area code = 1)."""

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area__area_code=area_code,
    )
    exclusion = factories.QuotaOrderNumberOriginExclusionFactory.create(origin=origin)

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ON13(exclusion.transaction).validate(exclusion)


@pytest.mark.business_rules
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

    deleted = factories.GeographicalMembershipFactory.create(
        geo_group=membership.geo_group,
        member=membership.member,
        version_group=membership.version_group,
        update_type=UpdateType.DELETE,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ON14(deleted.transaction).validate(exclusion)


@pytest.mark.business_rules
def test_CertificatesMustExist():
    """The referenced certificates must exist."""
    quota_order_number = factories.QuotaOrderNumberFactory.create(
        required_certificates__description=None,
    )

    certificate = quota_order_number.required_certificates.first()
    certificate.delete()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CertificatesMustExist(certificate.transaction).validate(
            certificate,
        )


@pytest.mark.business_rules
def test_CertificateValidityPeriodMustSpanQuotaOrderNumber(assert_spanning_enforced):
    """The validity period of the required certificates must span the validity
    period of the quota order number."""

    assert_spanning_enforced(
        factories.QuotaOrderNumberFactory,
        business_rules.CertificateValidityPeriodMustSpanQuotaOrderNumber,
    )


@pytest.mark.business_rules
def test_QD1(assert_handles_duplicates):
    """Quota order number id + start date must be unique."""

    assert_handles_duplicates(
        factories.QuotaDefinitionFactory,
        business_rules.QD1,
        identifying_fields=business_rules.QD1.identifying_fields,
    )


@pytest.mark.business_rules
def test_QD2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.QuotaDefinitionFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.business_rules
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


@pytest.mark.business_rules
def test_QD8(assert_spanning_enforced):
    """The validity period of the monetary unit code must span the validity
    period of the quota definition."""

    assert_spanning_enforced(
        factories.QuotaDefinitionFactory,
        business_rules.QD8,
        is_monetary=True,
        is_physical=False,
    )


@pytest.mark.business_rules
@pytest.mark.skip(reason="Using GBP, not EUR")
def test_QD9():
    """The monetary unit code must always be the Euro ISO code (or Ecu for quota
    defined prior to the Euro Definition)."""

    assert False


@pytest.mark.business_rules
def test_QD10(assert_spanning_enforced):
    """The validity period of the measurement unit code must span the validity
    period of the quota definition."""

    assert_spanning_enforced(
        factories.QuotaDefinitionFactory,
        business_rules.QD10,
    )


@pytest.mark.business_rules
def test_QD11(assert_spanning_enforced):
    """The validity period of the measurement unit qualifier code must span the
    validity period of the quota definition."""

    assert_spanning_enforced(
        factories.QuotaDefinitionWithQualifierFactory,
        business_rules.QD11,
    )


@pytest.mark.business_rules
@pytest.mark.skip("Quota events are not supported")
def test_QD12():
    """If quota events exist for a quota definition, the start date of the quota
    definition cannot be brought forward."""


@pytest.mark.business_rules
@pytest.mark.skip("Quota events are not supported")
def test_QD13():
    """If quota events exist for a quota definition, the start date can only be
    postponed up to the date of the first quota event."""


@pytest.mark.business_rules
@pytest.mark.skip("Quota events are not supported")
def test_QD14():
    """If quota events exist for a quota definition, the end date of the quota
    definition can be postponed."""


@pytest.mark.business_rules
@pytest.mark.skip("Quota events are not supported")
def test_QD15():
    """If quota events exist for a quota definition, the end date can only be
    brought forward up to the date of the last quota event on that quota
    definition."""


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("date_range", "error_expected"),
    (
        ("future", False),
        ("earlier", True),
    ),
)
@pytest.mark.parametrize(
    ("update_type"),
    (
        UpdateType.UPDATE,
        UpdateType.DELETE,
    ),
)
def test_prevent_quota_definition_deletion(
    unapproved_transaction,
    date_ranges,
    date_range,
    update_type,
    error_expected,
):
    """
    QAM does not like handling deletions of active Quota Definitions.

    Ensure an active Quota Definition cannot be deleted.
    """
    quota_definition = factories.QuotaDefinitionFactory.create(
        valid_between=getattr(date_ranges, date_range),
    )

    deleted = quota_definition.new_version(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=update_type,
    )

    error_expected = error_expected and (update_type == UpdateType.DELETE)
    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.PreventQuotaDefinitionDeletion(deleted.transaction).validate(
            deleted,
        )


@pytest.mark.business_rules
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

    deleted = quota_definition.new_version(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rule(deleted.transaction).validate(deleted)

    linking_model.update_type = UpdateType.DELETE
    linking_model.save(force_write=True)
    deleted = quota_definition.new_version(
        workbasket=unapproved_transaction.workbasket,
        transaction=unapproved_transaction,
        update_type=UpdateType.DELETE,
    )
    business_rule(deleted.transaction).validate(deleted)


@pytest.mark.business_rules
def test_overlapping_quota_definition(date_ranges):
    order_number = factories.QuotaOrderNumberFactory.create()
    factories.QuotaDefinitionFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
    )
    overlapping_definition = factories.QuotaDefinitionFactory.create(
        order_number=order_number,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.OverlappingQuotaDefinition(
            overlapping_definition.transaction,
        ).validate(overlapping_definition)


@pytest.mark.business_rules
def test_overlapping_quota_definition_on_deleted_records(
    date_ranges,
    delete_record,
    approved_transaction,
):
    order_number = factories.QuotaOrderNumberFactory.create()

    old_quota_definition = factories.QuotaDefinitionFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
    )

    old_quota_definition.new_version(
        update_type=UpdateType.DELETE,
        transaction=approved_transaction,
        workbasket=approved_transaction.workbasket,
    )

    overlapping_definition = factories.QuotaDefinitionFactory.create(
        sid=5,
        order_number=order_number,
        valid_between=date_ranges.normal,
    )

    assert (
        business_rules.OverlappingQuotaDefinition(
            overlapping_definition.transaction,
        ).validate(
            overlapping_definition,
        )
        is None
    )


@pytest.mark.business_rules
def test_volume_and_initial_volume_must_match(date_ranges):
    """Unless it is the main quota in a quota association, a definition's volume
    and initial_volume values should always be the same."""

    definition = factories.QuotaDefinitionFactory.create(
        volume=1.000,
        initial_volume=2.000,
        valid_between=getattr(date_ranges, "starts_1_month_ahead_to_2_months_ahead"),
    )

    with pytest.raises(BusinessRuleViolation) as violation:
        business_rules.VolumeAndInitialVolumeMustMatch(definition.transaction).validate(
            definition,
        )

    assert (
        "Unless it is the main quota in a quota association, a definition's volume and initial_volume values should always be the same."
        in str(violation)
    )


@pytest.mark.business_rules
def test_volume_and_initial_volume_can_differ_if_in_current_or_historical_period(
    date_ranges,
):
    """Unless it is the main quota in a quota association, a definition's volume
    and initial_volume values should always be the same."""

    definition_historical = factories.QuotaDefinitionFactory.create(
        volume=1.000,
        initial_volume=2.000,
        valid_between=getattr(date_ranges, "starts_2_months_ago_to_1_month_ago"),
    )

    definition_current = factories.QuotaDefinitionFactory.create(
        volume=1.000,
        initial_volume=2.000,
        valid_between=getattr(date_ranges, "starts_1_month_ago_to_1_month_ahead"),
    )

    result_historical = business_rules.VolumeAndInitialVolumeMustMatch(
        definition_historical.transaction,
    ).validate(
        definition_historical,
    )
    result_current = business_rules.VolumeAndInitialVolumeMustMatch(
        definition_current.transaction,
    ).validate(
        definition_current,
    )

    assert result_historical
    assert result_current


@pytest.mark.business_rules
def test_volume_and_initial_volume_must_match_main_quota():
    """Test that VolumeAndInitialVolumeMustMatch does not raise a violation when
    definition with different volume and initial_volume values is used as parent
    quota in an association."""

    definition = factories.QuotaDefinitionFactory.create(
        volume=1.000,
        initial_volume=2.000,
    )
    association = factories.QuotaAssociationFactory.create(
        transaction=definition.transaction,
        main_quota=definition,
        sub_quota__transaction=definition.transaction,
    )

    business_rules.VolumeAndInitialVolumeMustMatch(association.transaction).validate(
        definition,
    )


@pytest.mark.business_rules
def test_volume_and_initial_volume_must_match_sub_quota():
    """Test that VolumeAndInitialVolumeMustMatch raises a violation when
    definition with different volume and initial_volume values is used as child
    quota in an association."""

    definition = factories.QuotaDefinitionFactory.create(
        volume=1.000,
        initial_volume=2.000,
    )
    association = factories.QuotaAssociationFactory.create(
        transaction=definition.transaction,
        sub_quota=definition,
        main_quota__transaction=definition.transaction,
    )

    with pytest.raises(BusinessRuleViolation) as violation:
        business_rules.VolumeAndInitialVolumeMustMatch(
            association.transaction,
        ).validate(
            definition,
        )

    assert (
        "Unless it is the main quota in a quota association, a definition's volume and initial_volume values should always be the same."
        in str(violation)
    )


@pytest.mark.business_rules
def test_QA1(assert_handles_duplicates):
    """The association between two quota definitions must be unique."""

    assert_handles_duplicates(
        factories.QuotaAssociationFactory,
        business_rules.QA1,
    )


@pytest.mark.business_rules
def test_QA2(date_ranges):
    """The sub-quota’s validity period must be entirely enclosed within the
    validity period of the main quota."""
    association = factories.QuotaAssociationFactory.create(
        main_quota__valid_between=date_ranges.normal,
        sub_quota__valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QA2(association.transaction).validate(association)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "sub_definition_valid_between, main_definition_valid_between, expected_response",
    [
        (
            TaricDateRange(date(2019, 1, 1), date(2020, 2, 2)),
            TaricDateRange(date(2021, 1, 1), date(2021, 12, 1)),
            False,
        ),
        (
            TaricDateRange(date(2021, 1, 1), date(2050, 2, 2)),
            TaricDateRange(date(2021, 1, 1), date(2021, 12, 1)),
            False,
        ),
        (
            TaricDateRange(date(2021, 1, 1), date(2021, 12, 1)),
            TaricDateRange(date(2020, 1, 1), date(2023, 12, 1)),
            True,
        ),
    ],
)
def test_QA2_dict(
    sub_definition_valid_between,
    main_definition_valid_between,
    expected_response,
):
    """As above, but checking between a definition and a dict with date
    ranges."""
    assert (
        business_rules.check_QA2_dict(
            sub_definition_valid_between,
            main_definition_valid_between,
        )
        == expected_response
    )


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "main_volume, main_unit, sub_volume, sub_unit, main_init_volume, sub_init_volume, expect_error",
    [
        (1.0, "KGM", 1.0, "KGM", 1.0, 1.0, False),
        (1.0, "KGM", 0.0, "KGM", 1.0, 1.0, False),
        (2.0, "KGM", 1.0, "KGM", 1.0, 1.0, False),
        (1.0, "KGM", 2.0, "KGM", 1.0, 1.0, True),
        (1.0, "KGM", 1.0, "DTN", 1.0, 1.0, True),
        (1.0, "DTN", 1.0, "DTN", 1.0, 1.0, False),
        (1.0, "DTN", 1.0, "DTN", 1.0, 2.0, True),
        (1.0, "DTN", 1.0, "DTN", 1.0, 1.0, False),
    ],
)
def test_QA3(
    main_volume,
    main_unit,
    sub_volume,
    sub_unit,
    main_init_volume,
    sub_init_volume,
    expect_error,
):
    """When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main
    quota."""

    units = defaultdict(factories.MeasurementUnitFactory)

    assoc = factories.QuotaAssociationFactory(
        main_quota__volume=main_volume,
        main_quota__initial_volume=main_init_volume,
        main_quota__measurement_unit=units[main_unit],
        sub_quota__volume=sub_volume,
        sub_quota__measurement_unit=units[sub_unit],
        sub_quota__initial_volume=sub_init_volume,
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.QA3(assoc.transaction).validate(assoc)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "main_volume, main_unit, sub_volume, sub_unit, main_init_volume, sub_init_volume, expected_response",
    [
        (1.0, "KGM", 1.0, "KGM", 1.0, 1.0, True),
        (1.0, "KGM", 0.0, "KGM", 1.0, 1.0, True),
        (2.0, "KGM", 1.0, "KGM", 1.0, 1.0, True),
        (1.0, "KGM", 2.0, "KGM", 1.0, 1.0, False),
        (1.0, "KGM", 1.0, "DTN", 1.0, 1.0, False),
        (1.0, "DTN", 1.0, "DTN", 1.0, 1.0, True),
        (1.0, "DTN", 1.0, "DTN", 1.0, 2.0, False),
        (1.0, "DTN", 1.0, "DTN", 1.0, 1.0, True),
    ],
)
def test_QA3_dict(
    main_volume,
    main_unit,
    sub_volume,
    sub_unit,
    main_init_volume,
    sub_init_volume,
    expected_response,
):
    """As above, but checking between a definition and a dict."""

    assert (
        business_rules.check_QA3_dict(
            main_definition_volume=main_volume,
            main_definition_unit=main_unit,
            sub_definition_volume=sub_volume,
            sub_definition_unit=sub_unit,
            sub_initial_volume=sub_init_volume,
            main_initial_volume=main_init_volume,
        )
        == expected_response
    )


@pytest.mark.business_rules
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

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.QA4(assoc.transaction).validate(assoc)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "coefficient, expected_response",
    [
        (1.0, True),
        (2.0, True),
        (0.0, False),
        (-1.0, False),
    ],
)
def test_QA4_dict(coefficient, expected_response):
    """As above, but checking between a definition and a dict."""
    assert business_rules.check_QA4_dict(coefficient) == expected_response


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("existing_volume", "new_volume", "coeff", "type", "error_expected"),
    (
        ("1000.0", "1000.0", "1.200", SubQuotaType.EQUIVALENT, False),
        ("1000.0", "1000.0", "1.000", SubQuotaType.EQUIVALENT, True),
        ("1000.0", "2000.0", "1.200", SubQuotaType.EQUIVALENT, True),
        ("2000.0", "1000.0", "1.000", SubQuotaType.NORMAL, False),
        ("1000.0", "1000.0", "1.000", SubQuotaType.NORMAL, False),
        ("2000.0", "1000.0", "1.200", SubQuotaType.NORMAL, True),
    ),
)
def test_QA5(existing_volume, new_volume, coeff, type, error_expected):
    """
    Whenever a sub-quota is defined with the ‘equivalent’ type, it must have the
    same volume as the other sub-quotas associated with the parent quota.

    Moreover it must be defined with a coefficient not equal to 1. When a sub-
    quota relationship type is defined as 'equivalent' it must have the same
    volume as the ones associated with the parent quota

    A sub-quota defined with the 'normal' type must have a coefficient of 1.
    """

    existing = factories.QuotaAssociationFactory.create(
        sub_quota__volume=Decimal(existing_volume),
        sub_quota_relation_type=type,
    )
    assoc = factories.QuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota__volume=Decimal(new_volume),
        sub_quota_relation_type=type,
        coefficient=Decimal(coeff),
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.QA5(assoc.transaction).validate(assoc)


@pytest.mark.business_rules
def test_QA5_deleted_association():

    existing = factories.QuotaAssociationFactory.create(
        sub_quota__volume=Decimal("1000"),
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
    )

    assoc = factories.QuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota__volume=Decimal("2000"),
        sub_quota_relation_type=SubQuotaType.EQUIVALENT,
        coefficient=Decimal("1.200"),
        update_type=UpdateType.DELETE.value,
    )

    with raises_if(BusinessRuleViolation, False):
        business_rules.QA5(assoc.transaction).validate(assoc)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("existing_relation", "new_relation", "error_expected"),
    (
        (SubQuotaType.NORMAL, SubQuotaType.NORMAL, False),
        (SubQuotaType.EQUIVALENT, SubQuotaType.EQUIVALENT, False),
        (SubQuotaType.NORMAL, SubQuotaType.EQUIVALENT, True),
        (SubQuotaType.EQUIVALENT, SubQuotaType.NORMAL, True),
    ),
)
def test_QA6(existing_relation, new_relation, error_expected):
    """Sub-quotas associated with the same main quota must have the same
    relation type."""

    existing = factories.QuotaAssociationFactory.create(
        sub_quota_relation_type=existing_relation,
    )
    assoc = factories.QuotaAssociationFactory.create(
        main_quota=existing.main_quota,
        sub_quota_relation_type=new_relation,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.QA6(assoc.transaction).validate(assoc)


# https://uktrade.atlassian.net/browse/TP2000-434
@pytest.mark.business_rules
def test_QA6_new_association_version():
    """Tests that previous versions of an association are not compared when
    looking for sub-quotas associated with the same main quota."""

    original_version = factories.QuotaAssociationFactory.create(
        sub_quota_relation_type="EQ",
    )
    later_version = original_version.new_version(
        original_version.transaction.workbasket,
        sub_quota_relation_type="NM",
    )

    business_rules.QA6(later_version.transaction).validate(later_version)


@pytest.mark.business_rules
def test_same_main_and_sub_quota():
    """A quota association may only exist between two distinct quota
    definitions."""

    definition = factories.QuotaDefinitionFactory.create()
    association = factories.QuotaAssociationFactory.create(
        main_quota=definition,
        sub_quota=definition,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.SameMainAndSubQuota(association.transaction).validate(
            association,
        )


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("mechanism", "error_expected"),
    (
        (AdministrationMechanism.LICENSED, True),
        (AdministrationMechanism.FCFS, False),
    ),
)
def test_blocking_of_fcfs_quotas_only(mechanism, error_expected):
    """Blocking periods are only applicable to FCFS quotas."""
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition__order_number__mechanism=mechanism,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.BlockingOnlyOfFCFSQuotas(blocking.transaction).validate(blocking)


@pytest.mark.business_rules
def test_QBP2(date_ranges):
    """The start date of the quota blocking period must be later than or equal
    to the start date of the quota validity period."""
    blocking = factories.QuotaBlockingFactory.create(
        quota_definition__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal_earlier,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.QBP2(blocking.transaction).validate(blocking)


@pytest.mark.business_rules
def test_QBP3(date_ranges):
    """The end date of the quota blocking period must be later than the start
    date of the quota blocking period."""

    with pytest.raises(DataError):
        factories.QuotaBlockingFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("mechanism", "error_expected"),
    (
        (AdministrationMechanism.LICENSED, True),
        (AdministrationMechanism.FCFS, False),
    ),
)
def test_suspension_of_fcfs_quotas_only(mechanism, error_expected):
    """Quota suspensions are only applicable to First Come First Served
    quotas."""
    suspension = factories.QuotaSuspensionFactory.create(
        quota_definition__order_number__mechanism=mechanism,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.SuspensionsOnlyToFCFSQuotas(suspension.transaction).validate(
            suspension,
        )


@pytest.mark.business_rules
def test_QSP2(assert_spanning_enforced):
    """The validity period of the quota must span the quota suspension
    period."""

    assert_spanning_enforced(
        factories.QuotaSuspensionFactory,
        business_rules.QSP2,
    )
