import datetime
from typing import Dict

import pytest
import requests
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from measures.constants import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.forms import MeasureForm
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureConditionCode


@pytest.fixture
def component_applicability():
    def check(field_name, value, factory=None, applicability_field=None):
        if applicability_field is None:
            applicability_field = f"duty_expression__{field_name}_applicability_code"

        if factory is None:
            factory = factories.MeasureComponentFactory

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.MANDATORY,
                    field_name: None,
                },
            )

        with pytest.raises(ValidationError):
            factory.create(
                **{
                    applicability_field: ApplicabilityCode.NOT_PERMITTED,
                    field_name: value,
                },
            )

        return True

    return check


@pytest.fixture
def existing_goods_nomenclature(date_ranges):
    return factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.big,
    )


@pytest.fixture()
def seed_database_with_indented_goods():
    transaction = factories.TransactionFactory.create()

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=0,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=1,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903690000",
        suffix=10,
        indent__indent=2,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=10,
        indent__indent=3,
    )

    child_good_1 = factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=80,
        indent__indent=4,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691900",
        suffix=80,
        indent__indent=4,
    )

    # duplicate indent for child_good_1, with indent of 3
    child_good_1.indents.first().copy(indent=3, transaction=transaction)


@pytest.fixture(
    params=(
        (None, {"valid_between": factories.date_ranges("normal")}, True),
        (
            None,
            {
                "valid_between": factories.date_ranges("no_end"),
                "generating_regulation__valid_between": factories.date_ranges("normal"),
                "generating_regulation__effective_end_date": factories.end_date(
                    "normal",
                ),
            },
            True,
        ),
        (
            {"valid_between": factories.date_ranges("no_end")},
            {"update_type": UpdateType.DELETE},
            False,
        ),
    ),
    ids=[
        "explicit",
        "implicit",
        "draft:previously",
    ],
)
def existing_measure(request, existing_goods_nomenclature):
    """
    Returns a measure that with an attached quota and a flag indicating whether
    the date range of the measure overlaps with the "normal" date range.

    The measure will either be a new measure or a draft UPDATE to an existing
    measure. If it is an UPDATE, the measure will be in an unapproved
    workbasket.
    """
    data = {
        "goods_nomenclature": existing_goods_nomenclature,
        "additional_code": factories.AdditionalCodeFactory.create(),
    }

    previous, now, overlaps_normal = request.param
    if previous:
        old_version = factories.MeasureWithQuotaFactory.create(**data, **previous)
        return (
            factories.MeasureWithQuotaFactory.create(
                version_group=old_version.version_group,
                transaction=factories.UnapprovedTransactionFactory(),
                **data,
                **now,
            ),
            overlaps_normal,
        )
    else:
        return factories.MeasureWithQuotaFactory.create(**data, **now), overlaps_normal


@pytest.fixture
def condition_codes() -> Dict[str, MeasureConditionCode]:
    return {
        mcc.code: mcc
        for mcc in [
            factories.MeasureConditionCodeFactory(code="A"),
            factories.MeasureConditionCodeFactory(code="B"),
            factories.MeasureConditionCodeFactory(code="Y"),
        ]
    }


@pytest.fixture
def action_codes() -> Dict[str, MeasureAction]:
    return {
        a.code: a
        for a in [
            factories.MeasureActionFactory(code="01"),
            factories.MeasureActionFactory(code="09"),
            factories.MeasureActionFactory(code="24"),
            factories.MeasureActionFactory(code="299"),
        ]
    }


@pytest.fixture
def certificates():
    d_type = factories.CertificateTypeFactory(sid="D")
    nine_type = factories.CertificateTypeFactory(sid="9")
    return {
        "D017": factories.CertificateFactory(sid="017", certificate_type=d_type),
        "D018": factories.CertificateFactory(sid="018", certificate_type=d_type),
        "9100": factories.CertificateFactory(sid="100", certificate_type=nine_type),
    }


@pytest.fixture
def erga_omnes():
    return factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        area_id="1011",
    )


@pytest.fixture
def measure_form_data():
    measure = factories.MeasureFactory.create()
    data = model_to_dict(measure)
    data["geo_area"] = "COUNTRY"
    data["country_region-geographical_area_country_or_region"] = data[
        "geographical_area"
    ]
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )

    return data


@pytest.fixture
def measure_edit_conditions_data(measure_form_data):
    condition_code = factories.MeasureConditionCodeFactory.create(
        accepts_certificate=True,
    )
    certificate = factories.CertificateFactory.create()
    action = factories.MeasureActionFactory.create()
    edit_data = {k: v for k, v in measure_form_data.items() if v is not None}
    edit_data["update_type"] = 1
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-TOTAL_FORMS"] = 1
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-INITIAL_FORMS"] = 1
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-MIN_NUM_FORMS"] = 0
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-MAX_NUM_FORMS"] = 1000
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code"] = (
        condition_code.pk
    )
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-required_certificate"] = (
        certificate.pk
    )
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action"] = action.pk
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-applicable_duty"] = (
        "3.5% + 11 GBP / 100 kg"
    )

    return edit_data


@pytest.fixture
def measure_edit_conditions_and_negative_action_data(measure_edit_conditions_data):
    # set up second condition with negative action
    negative_action = factories.MeasureActionFactory.create()
    positive_action = MeasureAction.objects.get(
        pk=measure_edit_conditions_data[
            f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action"
        ],
    )
    factories.MeasureActionPairFactory(
        positive_action=positive_action,
        negative_action=negative_action,
    )

    edit_data = {k: v for k, v in measure_edit_conditions_data.items() if v is not None}
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-condition_code"] = (
        measure_edit_conditions_data[
            f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code"
        ]
    )
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-action"] = negative_action.pk
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-TOTAL_FORMS"] = 2
    edit_data[f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-INITIAL_FORMS"] = 2

    return edit_data


@pytest.fixture
def measure_form(measure_form_data, session_request_with_workbasket, erga_omnes):
    with override_current_transaction(Transaction.objects.last()):
        return MeasureForm(
            data=measure_form_data,
            instance=Measure.objects.first(),
            request=session_request_with_workbasket,
            initial={},
        )


@pytest.fixture()
def additional_code():
    return factories.AdditionalCodeFactory.create()


@pytest.fixture()
def measure_type():
    return factories.MeasureTypeFactory.create(
        valid_between=TaricDateRange(datetime.date(2020, 1, 1), None, "[)"),
    )


@pytest.fixture()
def regulation():
    return factories.RegulationFactory.create()


@pytest.fixture()
def commodity1():
    return factories.GoodsNomenclatureFactory.create()


@pytest.fixture()
def commodity2():
    return factories.GoodsNomenclatureFactory.create()


@pytest.fixture()
def mock_request(rf, valid_user, valid_user_client):
    request = rf.get("/")
    request.user = valid_user
    request.session = valid_user_client.session
    request.requests_session = requests.Session()
    return request
