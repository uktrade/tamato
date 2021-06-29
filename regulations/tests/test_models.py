import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    [
        factories.RegulationGroupFactory,
        factories.RegulationFactory,
        factories.AmendmentFactory,
        factories.ExtensionFactory,
        factories.SuspensionFactory,
        factories.TerminationFactory,
        factories.ReplacementFactory,
    ],
)
def test_regulation_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
    )
