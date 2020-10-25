import pytest
from lxml import etree

from common.tests import factories
from common.tests.util import validate_taric_xml
from quotas.validators import QuotaEventType

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.QuotaOrderNumberFactory, factory_kwargs={"origin": None})
def test_quota_order_number_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//quota.order.number", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaOrderNumberOriginFactory)
def test_quota_order_number_origin_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//quota.order.number.origin", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaOrderNumberOriginExclusionFactory)
def test_quota_order_number_origin_exclusion_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//quota.order.number.origin.exclusions", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaDefinitionFactory)
def test_quota_definition_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//quota.definition", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaAssociationFactory)
def test_quota_association_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//quota.association", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaSuspensionFactory)
def test_quota_suspension_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//quota.suspension.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.QuotaBlockingFactory)
def test_quota_blocking_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//quota.blocking.period", xml.nsmap)
    assert element is not None


@pytest.mark.parametrize(
    "subrecord_code, event_type_name", zip(QuotaEventType.values, QuotaEventType.names)
)
def test_quota_event_xml(
    api_client, taric_schema, approved_workbasket, subrecord_code, event_type_name
):
    event_type_name = event_type_name.lower()
    if event_type_name == "closed":
        event_type_name = "closed.and.transferred"
    tag = f"quota.{event_type_name}.event"

    @validate_taric_xml(
        instance=factories.QuotaEventFactory(
            subrecord_code=subrecord_code, workbasket=approved_workbasket
        )
    )
    def test_event_type(api_client, taric_schema, approved_workbasket, xml):
        element = xml.find(f".//{tag}", xml.nsmap)
        assert element is not None

    test_event_type(api_client, taric_schema, approved_workbasket)
