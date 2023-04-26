from __future__ import annotations

import bs4
from bs4 import NavigableString

from common.validators import UpdateType
from importer.namespaces import Tag


class MessageInfo:
    transaction_id: int
    record_code: str
    subrecord_code: str
    sequence_number: int
    update_type: int
    update_type_name: str
    object_type: str
    message: Tag
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
            elif isinstance(tag, Tag):
                self.data[tag.name] = tag.text

        return


class NewElementParser:
    record_code: str
    subrecord_code: str
    xml_object_tag: str
    parsers: {}

    def __init__(self, message_info: MessageInfo):
        pass
