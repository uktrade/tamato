import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.FootnoteTypeFactory)
def test_footnote_type_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//footnote.type", xml.nsmap)
    assert element is not None
    element = xml.find(".//footnote.type.description", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteFactory)
def test_footnote_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//footnote", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteDescriptionFactory)
def test_footnote_description_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//footnote.description", xml.nsmap)
    assert element is not None
