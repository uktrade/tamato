import pytest

from common.tests import factories
from common.validators import UpdateType
from measures.helpers import create_conditions
from measures.helpers import update_measure

pytestmark = pytest.mark.django_db


def test_create_conditions(
    condition_codes,
    certificates,
    action_codes,
    duty_sentence_parser,
):
    measure = factories.MeasureFactory.create()
    workbasket = factories.WorkBasketFactory.create()
    transaction = workbasket.new_transaction()
    conditions_data = [
        {
            "condition_code": condition_codes["A"],
            "duty_amount": 1.0,
            "monetary_unit": None,
            "condition_measurement": None,
            "required_certificate": certificates["D017"],
            "action": action_codes["01"],
            "applicable_duty": "2%",
            "condition_sid": "",
            "reference_price": "1%",
            "DELETE": False,
            "update_type": UpdateType.CREATE,
        },
    ]

    measure_data = {}

    assert not workbasket.measures.all()

    defaults = {"generating_regulation": measure.generating_regulation}
    update_measure(measure, transaction, workbasket, measure_data, defaults)
    create_conditions(measure, transaction, workbasket, conditions_data)

    assert workbasket.measures.count() == 1
    # measure, measure condition and measure component
    assert workbasket.tracked_models.count() == 3
    assert workbasket.measures.first().transaction.workbasket == workbasket

    for mcondition in workbasket.measures.first().conditions.all():
        assert mcondition.transaction == transaction
        assert mcondition.transaction.workbasket == workbasket
