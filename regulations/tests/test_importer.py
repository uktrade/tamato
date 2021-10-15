from datetime import date

import pytest

from common.tests import factories
from regulations import serializers

pytestmark = pytest.mark.django_db


def test_regulation_group_importer(imported_fields_match):
    assert imported_fields_match(
        factories.RegulationGroupFactory,
        serializers.GroupSerializer,
    )


def test_regulation_importer(imported_fields_match):
    assert imported_fields_match(
        factories.RegulationFactory,
        serializers.BaseRegulationSerializer,
        dependencies={"regulation_group": factories.RegulationGroupFactory},
    )


def test_amendment_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AmendmentFactory,
        serializers.AmendmentSerializer,
        dependencies={"target_regulation": factories.RegulationFactory},
    )


def test_suspension_importer(imported_fields_match):
    assert imported_fields_match(
        factories.SuspensionFactory,
        serializers.SuspensionSerializer,
        dependencies={
            "target_regulation": factories.RegulationFactory,
            "effective_end_date": date(2021, 2, 1),
        },
    )


def test_replacement_importer(imported_fields_match):
    assert imported_fields_match(
        factories.ReplacementFactory,
        serializers.ReplacementSerializer,
        dependencies={
            "target_regulation": factories.RegulationFactory,
            "enacting_regulation": factories.RegulationFactory,
        },
    )
