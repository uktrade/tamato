import xml.etree.ElementTree as ET

import pytest

from common.util import xml_fromstring
from importer.namespaces import Tag
from importer.namespaces import TTags

quota_event = Tag("quota.event")
quota_balance_event = Tag("quota.balance.event")

pytestmark = pytest.mark.django_db


def get_snippet_transaction(
    xml: str,
    Tags: TTags,
) -> ET.Element:
    """Returns the first transaction element in a Taric envelope."""
    envelope = xml_fromstring(xml)
    return Tags.ENV_TRANSACTION.first(envelope)


def test_tag_first(taric_schema_tags, envelope_commodity):
    """Asserts that Tag.first locates the appropriate child in the parent
    element."""
    transaction = get_snippet_transaction(envelope_commodity, taric_schema_tags)
    assert transaction is not None


def test_tag_equals_with_name(tag_name):
    """Asserts that Tag comparisons work when the tag name is not a patern."""
    assert tag_name.is_pattern is False
    assert tag_name == quota_event
    assert tag_name != quota_balance_event


def test_tag_equals_with_pattern(tag_regex):
    """Asserts that Tag comparisons work when the tag name is a patern."""
    assert tag_regex.is_pattern is True
    assert tag_regex != quota_event
    assert tag_regex == quota_balance_event
