import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap
from quotas.validators import QuotaEventType

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.QuotaOrderNumberFactory, factory_kwargs={"origin": None})
def test_quota_order_number_xml(xml):
    element = xml.find(".//oub:quota.order.number", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaOrderNumberOriginFactory)
def test_quota_order_number_origin_xml(xml):
    element = xml.find(".//oub:quota.order.number.origin", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaOrderNumberOriginExclusionFactory)
def test_quota_order_number_origin_exclusion_xml(xml):
    element = xml.find(".//oub:quota.order.number.origin.exclusions", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaDefinitionWithQualifierFactory)
def test_quota_definition_xml(xml):
    element = xml.find(".//oub:quota.definition", nsmap)
    assert element is not None
    element = xml.find(".//oub:monetary.unit.code", nsmap)
    assert element is not None
    element = xml.find(".//oub:measurement.unit.code", nsmap)
    assert element is not None
    element = xml.find(".//oub:measurement.unit.qualifier.code", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaAssociationFactory)
def test_quota_association_xml(xml):
    element = xml.find(".//oub:quota.association", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaSuspensionFactory)
def test_quota_suspension_xml(xml):
    element = xml.find(".//oub:quota.suspension.period", nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaBlockingFactory)
def test_quota_blocking_xml(xml):
    element = xml.find(".//oub:quota.blocking.period", nsmap)
    assert element is not None


@pytest.mark.parametrize(
    "subrecord_code, event_type_name",
    zip(QuotaEventType.values, QuotaEventType.names),
)
def test_quota_event_xml(
    api_client,
    taric_schema,
    approved_transaction,
    valid_user,
    subrecord_code,
    event_type_name,
):
    """
    Ensure Quota Events of all types output appropriate XML.

    Quota Events are a bit special and very dynamic. As a result this test
    allows all the various event types to be tested individually.
    """
    event_type_name = event_type_name.lower()
    if event_type_name == "closed":
        event_type_name = "closed.and.transferred"
    tag = f"quota.{event_type_name}.event"

    @validate_taric_xml(
        instance=factories.QuotaEventFactory.create(
            subrecord_code=subrecord_code,
            transaction=approved_transaction,
        ),
    )
    def test_event_type(xml):
        element = xml.find(f".//{tag}", xml.nsmap)
        assert element is not None

    test_event_type(api_client, taric_schema, approved_transaction, valid_user)
