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
def proofs_of_origin_objects():
    factories.MeasureConditionCodeFactory(code="Q")
    factories.MeasureActionFactory(code="27")
    factories.MeasureActionFactory(code="07")


@pytest.fixture
def proofs_of_origin_measure_data(measure_data: Dict, proofs_of_origin_objects) -> Dict:
    return {
        "proofs_of_origin": [
            factories.CertificateFactory(sid="123", certificate_type__sid="U"),
        ],
        **measure_data,
    }


def test_sid_is_next_highest(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure = factories.MeasureFactory()
    models = list(measure_creation_pattern.create(**measure_data))
    assert models[0].sid == measure.sid + 1


def test_condition_sid_is_next_highest(
    authorised_use_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    condition = factories.MeasureConditionFactory()
    models = list(measure_creation_pattern.create(**authorised_use_measure_data))
    assert models[0].conditions.first().sid == condition.sid + 1
    assert models[0].conditions.last().sid == condition.sid + 2


def test_all_records_in_same_transaction(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    models = list(measure_creation_pattern.create(**measure_data))
    assert len(set(m.transaction for m in models)) == 1


def test_ends_on_nomenclature_end(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=date_ranges.starts_with_normal,
    )
    models = list(measure_creation_pattern.create(**measure_data))
    assert models[0].valid_between.upper == date_ranges.starts_with_normal.upper


def test_starts_on_nomenclature_start(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=date_ranges.adjacent_later,
    )
    models = list(measure_creation_pattern.create(**measure_data))
    assert models[0].valid_between.lower == date_ranges.adjacent_later.lower


def test_starts_on_minimum_date(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["validity_start"] = date_ranges.no_end_before(date_ranges.now).lower
    measure_data["goods_nomenclature"] = factories.GoodsNomenclatureFactory(
        valid_between=TaricDateRange(date_ranges.now, None),
    )

    models = list(measure_creation_pattern.create(**measure_data))
    assert models[0].valid_between.lower == date_ranges.now


def test_adds_terminating_regulation_with_end_date(
    measure_data,
    date_ranges: Dates,
    measure_creation_pattern: MeasureCreationPattern,
):
    measure_data["validity_end"] = None
    models = list(measure_creation_pattern.create(**measure_data))
    assert not models[0].valid_between.upper
    assert not models[0].terminating_regulation

    measure_data["validity_end"] = date_ranges.normal.upper
    models = list(measure_creation_pattern.create(**measure_data))
    assert models[0].valid_between.upper
    assert models[0].terminating_regulation


def test_excludes_countries_and_regions(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    membership = factories.GeographicalMembershipFactory()
    measure_data["geographical_area"] = membership.geo_group
    measure_data["exclusions"] = [membership.member]

    models = list(measure_creation_pattern.create(**measure_data))
    exclusion = models[0].exclusions.get()
    assert exclusion.excluded_geographical_area == membership.member


def test_excludes_area_groups(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    membership = factories.GeographicalMembershipFactory()
    measure_data["geographical_area"] = membership.geo_group
    measure_data["exclusions"] = [membership.geo_group]

    models = list(measure_creation_pattern.create(**measure_data))
    exclusion = models[0].exclusions.get()
    assert exclusion.excluded_geographical_area == membership.member


def test_associates_footnotes(
    measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    footnote = factories.FootnoteFactory()
    measure_data["footnotes"] = [footnote]

    models = list(measure_creation_pattern.create(**measure_data))
    linked_footnote = models[0].footnotes.get()
    assert footnote == linked_footnote


def test_attaches_authorised_use_conditions(
    authorised_use_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    models = list(measure_creation_pattern.create(**authorised_use_measure_data))
    conditions = models[0].conditions.all()
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


def test_attaches_proof_of_origin_conditions(
    proofs_of_origin_measure_data,
    measure_creation_pattern: MeasureCreationPattern,
):
    models = list(measure_creation_pattern.create(**proofs_of_origin_measure_data))
    conditions = models[0].conditions.all()
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
    models = list(measure_creation_pattern.create(**condition_measure_data))
    conditions = models[0].conditions.all()
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

    models = list(measure_creation_pattern.create(**measure_data))
    components = models[0].components.all()
    assert components[0].duty_amount == Decimal("0.000")
    assert components[0].duty_expression.sid == 1
    assert components[1].duty_amount == Decimal("1.230")
    assert components[1].duty_expression.sid == 4
