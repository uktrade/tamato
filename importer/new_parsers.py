from __future__ import annotations

import bs4
from bs4 import NavigableString

from common.validators import UpdateType


class TransmissionParser:
    """
    A transmission contains multiple messages.

    Parsing a transmission will result in an ordered list of parsed messages
    """

    def __init__(self, transmission: bs4.Tag):
        pass


class MessageParser:
    """A message contains updates to a single TARIC3 object."""

    transaction_id: int
    record_code: str
    subrecord_code: str
    sequence_number: int
    update_type: int
    update_type_name: str
    object_type: str
    message: bs4.Tag
    data: dict

    def __init__(self, message: bs4.Tag):
        # get transaction_id, record_code, subrecord_code, sequence.number, update.type and object type
        self.message = message
        self.transaction_id = self.message.find("oub:transaction.id").value
        self.record_code = self.message.find("oub:record.code").value
        self.subrecord_code = self.message.find("oub:subrecord.code").value
        self.sequence_number = self.message.find("oub:record.sequence.number").value
        self.update_type = int(self.message.find("oub:update.type").text)
        self.object_type = ""
        # get object type
        sibling = self.message.find("oub:update.type").next_sibling

        while self.object_type == "":
            if sibling is None:
                break
            elif isinstance(sibling, NavigableString):
                sibling = sibling.next_sibling
                continue
            elif isinstance(sibling, bs4.Tag):
                self.object_type = sibling.name
                break

        for update_type in UpdateType:
            if update_type.value == self.update_type:
                self.update_type_name = update_type.name.lower()

        self._populate_data_dict()

    def _populate_data_dict(self):
        """Iterates through properties in the object tag and returns a
        dictionary of those properties."""
        self.data = dict()
        for tag in self.message.find(self.object_type).children:
            if isinstance(tag, NavigableString):
                continue
            elif isinstance(tag, bs4.Tag):
                data_property_name = self._parse_tag_name(tag.name, self.object_type)
                self.data[data_property_name] = tag.text

        return

    def _parse_tag_name(self, tag_name, object_type):
        parsed_tag_name = tag_name

        # some fields start with the full tag name e.g. quota.order.number.sid, this will be replaced with simply sid
        parsed_tag_name = parsed_tag_name.replace(object_type + ".", "")

        # anything left will be full stop seperated, this needs to change to underscores
        parsed_tag_name = parsed_tag_name.replace(".", "_")

        return parsed_tag_name


class NewElementParser:
    record_code: str
    subrecord_code: str
    xml_object_tag: str

    value_mapping = {}
