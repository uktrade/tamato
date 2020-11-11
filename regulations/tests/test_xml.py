import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.RegulationFactory)
def test_regulation_xml(api_client, taric_schema, xml):
    element = xml.find(".//base.regulation", xml.nsmap)
    assert element is not None
