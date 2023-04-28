from __future__ import annotations

from typing import List

import bs4
from bs4 import NavigableString

from common.validators import UpdateType


class TransactionParser:
    """
    A transmission contains multiple messages.

    Parsing a transmission will result in an ordered list of parsed messages
    (taric objects we need to try and import)
    """

    def __init__(self, transaction: bs4.Tag):
        self.parsed_messages: List[MessageParser] = []
        self.taric_objects = []

        self.messages_xml_tags = transaction.find_all("env:app.message")

        for message_xml in self.messages_xml_tags:
            self.parsed_messages.append(MessageParser(message_xml))

        for message in self.parsed_messages:
            self.taric_objects.append(message.taric_object)


class MessageParser:
    """A message contains create / update / delete to a single taric object."""

    def __init__(self, message: bs4.Tag):
        self.data = {}
        self.message = message
        self.transaction_id = self.message.find("oub:transaction.id").value
        self.record_code = self.message.find("oub:record.code").value
        self.subrecord_code = self.message.find("oub:subrecord.code").value
        self.sequence_number = self.message.find("oub:record.sequence.number").value
        self.update_type = int(self.message.find("oub:update.type").text)
        self.object_type = ""
        sibling = self.message.find("oub:update.type").next_sibling

        # get object type
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

        self._populate_data_dict(self.update_type, self.update_type_name)
        self.taric_object = self._construct_taric_object()

    def _populate_data_dict(self, update_type, update_type_name):
        """Iterates through properties in the object tag and returns a
        dictionary of those properties."""

        # also set update type and string representation

        self.data = {
            "update_type": update_type,
            "update_type_name": update_type_name,
        }

        for tag in self.message.find(self.object_type).children:
            if isinstance(tag, NavigableString):
                continue
            elif isinstance(tag, bs4.Tag):
                data_property_name = self._parse_tag_name(tag.name, self.object_type)
                self.data[data_property_name] = tag.text

        return

    def _construct_taric_object(self):
        parser_cls = self.get_parser(self.object_type)
        parser = parser_cls()

        for data_item_key in self.data.keys():
            mapped_data_item_key = data_item_key
            if data_item_key in parser.value_mapping:
                mapped_data_item_key = parser.value_mapping[data_item_key]

            if hasattr(parser, mapped_data_item_key):
                setattr(parser, mapped_data_item_key, self.data[data_item_key])
            else:
                raise Exception(
                    f"{parser.xml_object_tag} {parser} does not have a {data_item_key} attribute, and "
                    f"can't assign value {self.data[data_item_key]}",
                )

        return parser

    def _parse_tag_name(self, tag_name, object_type):
        parsed_tag_name = tag_name

        # some fields start with the full tag name e.g. quota.order.number.sid, this will be replaced with simply sid
        parsed_tag_name = parsed_tag_name.replace(object_type + ".", "")

        # anything left will be full stop seperated, this needs to change to underscores
        parsed_tag_name = parsed_tag_name.replace(".", "_")

        return parsed_tag_name

    def get_parser(self, object_type: str):
        # get all classes that can represent an imported taric object
        classes = self._get_parser_classes()

        # iterate through classes and find the one that matches the tag or error
        for cls in classes:
            if cls.xml_object_tag == object_type:
                return cls

        raise Exception(f"No parser class matching {object_type}")

    def _get_parser_classes(self):
        return self._get_all_subclasses(NewElementParser)

    def _get_all_subclasses(self, cls):
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(self._get_all_subclasses(subclass))

        return all_subclasses


class NewElementParser:
    handler = None

    record_code: str
    subrecord_code: str
    xml_object_tag: str
    update_type: int = None
    update_type_name: str = None

    value_mapping = {}


class TaricObjectLink:
    pass
