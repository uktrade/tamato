import xml.etree.ElementTree as ET

from importer.namespaces import Tag
from importer.namespaces import TTags

quota_event = Tag("quota.event")
quota_balance_event = Tag("quota.balance.event")


def get_snippet_transaction(
    xml: str,
    Tags: TTags,
) -> ET.Element:
    envelope = ET.fromstring(xml)
    return Tags.ENV_TRANSACTION.first(envelope)


def test_element_tag_finder(taric_schema_tags, envelope_commodity):
    transaction = get_snippet_transaction
    assert transaction is not None


def test_tag_pattern(tag_name):
    assert tag_name.is_pattern == False
    assert tag_name == quota_event
    assert tag_name != quota_balance_event


def test_regex_tag_pattern(tag_regex):
    assert tag_regex.is_pattern == True
    assert tag_regex != quota_event
    assert tag_regex == quota_balance_event
