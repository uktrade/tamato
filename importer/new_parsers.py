from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import List
from typing import get_type_hints

import bs4
from bs4 import NavigableString

from common.util import TaricDateRange
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
        self.transaction_id = self.message.find("oub:transaction.id").text
        self.record_code = self.message.find("oub:record.code").text
        self.subrecord_code = self.message.find("oub:subrecord.code").text
        self.sequence_number = self.message.find("oub:record.sequence.number").text
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
        parser_cls = ParserHelper.get_parser_by_tag(self.object_type)
        parser = parser_cls()

        parser.populate(
            self.transaction_id,
            self.record_code,
            self.subrecord_code,
            self.sequence_number,
            self.data,
        )

        return parser

    def _parse_tag_name(self, tag_name, object_type):
        parsed_tag_name = tag_name

        # anything left will be full stop seperated, this needs to change to underscores
        parsed_tag_name = parsed_tag_name.replace(".", "_")

        return parsed_tag_name


class ModelLinkField:
    def __init__(self, parser_field_name, object_field_name):
        self.parser_field_name = parser_field_name
        self.object_field_name = object_field_name


class ModelLink:
    def __init__(
        self,
        model,
        fields: List[ModelLinkField],
        xml_tag_name: str,
        optional=False,
    ):
        self.model = model
        self.fields = fields
        self.xml_tag_name = xml_tag_name
        self.optional = optional


class NewElementParser:
    transaction_id: int
    record_code: str
    subrecord_code: str
    xml_object_tag: str
    update_type: int = None
    update_type_name: str = None
    links_valid: bool = None
    value_mapping = {}
    model_links = None
    issues = []
    parent_handler = None
    excluded_fields = ["language_id"]

    def __init__(self):
        self.issues = []
        self.sequence_number = None

    def links(self):
        if self.model_links is None:
            raise Exception(
                f"No parser defined for {self.__class__.__name__}, is this correct?",
            )

        return self.model_links

    def populate(
        self,
        transaction_id: int,
        record_code: str,
        subrecord_code: str,
        sequence_number: int,
        data: dict,
    ):
        # standard data
        self.transaction_id = transaction_id
        if self.record_code != record_code:
            raise Exception(
                f"Record code mismatch : expected : {self.record_code}, got : {record_code}",
            )
        if self.subrecord_code != subrecord_code:
            raise Exception(
                f"Sub-record code mismatch : expected : {self.subrecord_code}, got : {subrecord_code}",
            )

        self.sequence_number = sequence_number

        # model specific data
        for data_item_key in data.keys():
            # some fields like language_id need to be skipped - we only care about en
            if data_item_key in self.excluded_fields:
                continue

            mapped_data_item_key = data_item_key
            if data_item_key in self.value_mapping:
                mapped_data_item_key = self.value_mapping[data_item_key]

            if hasattr(self, mapped_data_item_key):
                field_data_raw = data[data_item_key]

                if mapped_data_item_key == "update_type":
                    field_data_type = int
                elif mapped_data_item_key == "update_type_name":
                    field_data_type = str
                else:
                    field_data_type = get_type_hints(self)[mapped_data_item_key]

                field_data_typed = None

                # convert string objects to the correct types, based on parser class annotations

                if field_data_type == str:
                    field_data_typed = str(field_data_raw)
                elif field_data_type == date:
                    if field_data_raw is not None:
                        field_data_typed = datetime.strptime(
                            field_data_raw,
                            "%Y-%m-%d",
                        ).date()
                elif field_data_type == int:
                    field_data_typed = int(field_data_raw)
                elif field_data_type == float:
                    field_data_typed = float(field_data_raw)
                else:
                    raise Exception(
                        f"data type {field_data_type} not handled, please fix",
                    )

                setattr(self, mapped_data_item_key, field_data_typed)
            else:
                raise Exception(
                    f"{self.xml_object_tag} {self} does not have a {mapped_data_item_key} attribute, and "
                    f"can't assign value {data[data_item_key]}",
                )

        if hasattr(self, "valid_between_lower") and hasattr(
            self,
            "valid_between_upper",
        ):
            if self.valid_between_upper:
                self.valid_between = TaricDateRange(
                    self.valid_between_lower,
                    self.valid_between_upper,
                )
            else:
                self.valid_between = TaricDateRange(self.valid_between_lower)


class TaricObjectLink:
    pass


class ParserHelper:
    @staticmethod
    def get_parser_by_model(model):
        # get all classes that can represent an imported taric object
        classes = ParserHelper.__parser_classes()

        # iterate through classes and find the one that matches the tag or error
        for cls in classes:
            if cls.model == model and cls.append_to_parent == False:
                return cls

        raise Exception(f"No parser class matching {model}")

    @staticmethod
    def get_parser_by_tag(object_type: str):
        # get all classes that can represent an imported taric object
        classes = ParserHelper.__parser_classes()

        # iterate through classes and find the one that matches the tag or error
        for cls in classes:
            if cls.xml_object_tag == object_type:
                return cls

        raise Exception(f"No parser class matching {object_type}")

    @staticmethod
    def __parser_classes():
        return ParserHelper.__get_subclasses(NewElementParser)

    @staticmethod
    def __get_subclasses(cls):
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(ParserHelper.__get_subclasses(subclass))

        return all_subclasses
