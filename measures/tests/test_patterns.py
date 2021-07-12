from decimal import Decimal
from typing import Dict

import pytest

from common.tests import factories
from common.tests.util import Dates
from common.util import TaricDateRange
from measures.patterns import MeasureCreationPattern
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


@pytest.fixture
def measure_creation_pattern(
    workbasket: WorkBasket,
    date_ranges: Dates,
    duty_sentence_parser,
) -> MeasureCreationPattern:
    return MeasureCreationPattern(
        workbasket,
        date_ranges.now,
        defaults={
            "generating_regulation": factories.RegulationFactory(),
        },
        duty_sentence_parser=duty_sentence_parser,
    )


@pytest.fixture
def measure_data(date_ranges) -> Dict:
    return {
        "duty_sentence": "0.00 %",
        "geographical_area": factories.GeographicalAreaFactory(),
        "goods_nomenclature": factories.GoodsNomenclatureFactory(),
        "measure_type": factories.MeasureTypeFactory(),
        "validity_start": date_ranges.no_end.lower,
        "validity_end": date_ranges.no_end.upper,
    }


@pytest.fixture
def condition_measure_objects():
    factories.MeasureConditionCodeFactory(code="B")
    factories.MeasureActionFactory(code="29")
    factories.MeasureActionFactory(code="09")
    factories.CertificateFactory(sid="001", certificate_type__sid="C")


@pytest.fixture
def condition_measure_data(measure_data: Dict, condition_measure_objects) -> Dict:
    return {
        "condition_sentence": "Cond: B cert: C-001 (29):; B (09):",
        **measure_data,
    }


@pytest.fixture
def authorised_use_objects():
    factories.MeasureConditionCodeFactory(code="B")
    factories.MeasureActionFactory(code="27")
    factories.MeasureActionFactory(code="08")
    factories.CertificateFactory(sid="990", certificate_type__sid="N")


@pytest.fixture
def authorised_use_measure_data(measure_data: Dict, authorised_use_objects) -> Dict:
    return {"authorised_use": True, **measure_data}


@pytest.fixture
def order_number_objects():
    factories.MeasureConditionCodeFactory(code="Q")
    factories.MeasureActionFactory(code="27")
    factories.MeasureActionFactory(code="07")


@pytest.fixture
def required_certificates_data(measure_data: Dict, order_number_objects) -> Dict:
    return {
        "order_number": factories.QuotaOrderNumberFactory.create(
            required_certificates=[
                factories.CertificateFactory(
                    sid="123",
                    certificate_type__sid="U",
                ),
            ],
        ),
        **measure_data,
    }


def test_sid_is_next_highest(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure = factories.MeasureFactory()

    expected_sids = [measure.sid, measure.sid + 1, measure.sid + 2]
    actual_sids = [
        measure.sid,
        measure_creation_pattern.create(**measure_data).sid,
        measure_creation_pattern.create(**measure_data).sid,
    ]

    assert expected_sids == actual_sids


def test_condition_sid_is_next_highest(
    authorised_use_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    condition = factories.MeasureConditionFactory()
    measure = measure_creation_pattern.create(**authorised_use_measure_data)
    assert measure.conditions.first().sid == condition.sid + 1
    assert measure.conditions.last().sid == condition.sid + 2


def test_all_records_in_same_transaction(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    tracked_models = measure_creation_pattern.create_measure_tracked_models(
        **measure_data
    )
    assert len(set(m.transaction for m in tracked_models)) == 1


def test_ends_on_nomenclature_end(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=date_ranges.starts_with_normal,
    )
    measure = measure_creation_pattern.create(**measure_data)
    assert measure.valid_between.upper == date_ranges.starts_with_normal.upper


def test_starts_on_nomenclature_start(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=date_ranges.adjacent_later,
    )
    measure = measure_creation_pattern.create(**measure_data)
    assert measure.valid_between.lower == date_ranges.adjacent_later.lower


def test_starts_on_minimum_date(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["validity_start"] = date_ranges.no_end_before(date_ranges.now).lower
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=TaricDateRange(date_ranges.now, None),
    )

    measure = measure_creation_pattern.create(**measure_data)
    assert measure.valid_between.lower == date_ranges.now


def test_adds_terminating_regulation_with_end_date(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["validity_end"] = None
    measure = measure_creation_pattern.create(**measure_data)
    assert not measure.valid_between.upper
    assert not measure.terminating_regulation

    measure_data["validity_end"] = date_ranges.normal.upper
    measure = measure_creation_pattern.create(**measure_data)
    assert measure.valid_between.upper
    assert measure.terminating_regulation


def test_excludes_countries_and_regions(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    membership = factories.GeographicalMembershipFactory()
    measure_data["geographical_area"] = membership.geo_group
    measure_data["exclusions"] = [membership.member]

    measure = measure_creation_pattern.create(**measure_data)
    exclusion = measure.exclusions.get()
    assert exclusion.excluded_geographical_area == membership.member


def test_excludes_area_groups(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    membership = factories.GeographicalMembershipFactory()
    measure_data["geographical_area"] = membership.geo_group
    measure_data["exclusions"] = [membership.geo_group]

    measure = measure_creation_pattern.create(**measure_data)
    exclusion = measure.exclusions.get()
    assert exclusion.excluded_geographical_area == membership.member


def test_associates_footnotes(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    footnote = factories.FootnoteFactory()
    measure_data["footnotes"] = [footnote]

    measure = measure_creation_pattern.create(**measure_data)
    linked_footnote = measure.footnotes.get()
    assert footnote == linked_footnote


def test_attaches_authorised_use_conditions(
    authorised_use_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure = measure_creation_pattern.create(**authorised_use_measure_data)
    conditions = measure.conditions.all()
    assert len(conditions) == 2
    assert conditions[0].condition_code.code == "B"
    assert conditions[0].required_certificate.certificate_type.sid == "N"
    assert conditions[0].required_certificate.sid == "990"
    assert conditions[0].action.code == "27"
    assert conditions[0].component_sequence_number == 1
    assert conditions[1].condition_code.code == "B"
    assert conditions[1].required_certificate is None
    assert conditions[1].action.code == "08"
    assert conditions[1].component_sequence_number == 2


def test_attaches_origin_quota_conditions(
    required_certificates_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure = measure_creation_pattern.create(**required_certificates_data)
    conditions = measure.conditions.all()
    assert len(conditions) == 2
    assert conditions[0].condition_code.code == "Q"
    assert conditions[0].required_certificate.certificate_type.sid == "U"
    assert conditions[0].required_certificate.sid == "123"
    assert conditions[0].action.code == "27"
    assert conditions[0].component_sequence_number == 1
    assert conditions[1].condition_code.code == "Q"
    assert conditions[1].required_certificate is None
    assert conditions[1].action.code == "07"
    assert conditions[1].component_sequence_number == 2


def test_attaches_conditions_from_sentence(
    condition_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure = measure_creation_pattern.create(**condition_measure_data)
    conditions = measure.conditions.all()
    assert len(conditions) == 2
    assert conditions[0].condition_code.code == "B"
    assert conditions[0].required_certificate.certificate_type.sid == "C"
    assert conditions[0].required_certificate.sid == "001"
    assert conditions[0].action.code == "29"
    assert conditions[0].component_sequence_number == 1
    assert conditions[1].condition_code.code == "B"
    assert conditions[1].required_certificate is None
    assert conditions[1].action.code == "09"
    assert conditions[1].component_sequence_number == 2


def test_components_are_sequenced_correctly(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["duty_sentence"] = "0.0% + 1.23 %"

    measure = measure_creation_pattern.create(**measure_data)
    components = measure.components.all()
    assert components[0].duty_amount == Decimal("0.000")
    assert components[0].duty_expression.sid == 1
    assert components[1].duty_amount == Decimal("1.230")
    assert components[1].duty_expression.sid == 4
