from datetime import date

import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_regulation_group_importer(imported_fields_match):
    assert imported_fields_match(
        factories.RegulationGroupFactory,
    )


def test_regulation_importer(imported_fields_match):
    assert imported_fields_match(
        factories.RegulationFactory,
        dependencies={"regulation_group": factories.RegulationGroupFactory},
    )


def test_amendment_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AmendmentFactory,
        dependencies={"target_regulation": factories.RegulationFactory},
    )


def test_suspension_importer(imported_fields_match):
    assert imported_fields_match(
        factories.SuspensionFactory,
        dependencies={
            "target_regulation": factories.RegulationFactory,
            "effective_end_date": date(2021, 2, 1),
        },
    )


def test_replacement_importer(imported_fields_match):
    assert imported_fields_match(
        factories.ReplacementFactory,
        dependencies={
            "target_regulation": factories.RegulationFactory,
            "enacting_regulation": factories.RegulationFactory,
        },
    )
