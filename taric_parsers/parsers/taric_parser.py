from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import List
from typing import get_type_hints

import bs4
from bs4 import NavigableString

from common import validators
from common.models import Transaction
from common.util import TaricDateRange
from common.validators import UpdateType
from quotas.models import QuotaEvent
from taric_parsers.importer_issue import ImportIssueReportItem
from taric_parsers.parser_model_link import ModelLink

# import all parsers
EXCLUDED_PARSER_PROPERTIES = [
    "__annotations__",
    "__doc__",
    "__module__",
    "issues",
    "model",
    "model_links",
    "parent_parser",
    "value_mapping",
    "xml_object_tag",
    "valid_between_lower",
    "valid_between_upper",
    "sequence_number",
    "update_type_name",
    "links_valid",
    "transaction_id",
]

EXCLUDED_FIELDS_FOR_POPULATION = [
    "language_id",
    "antidumping_regulation_role",
    "related_antidumping_regulation_id",
    "complete_abrogation_regulation_role",
    "complete_abrogation_regulation_id",
    "explicit_abrogation_regulation_role",
    "explicit_abrogation_regulation_id",
    "export_refund_nomenclature_sid",
    "meursing_table_plan_id",
]


class TransactionParser:
    """
    Responsible for representing a parsed TARIC transaciton.

    A transmission contains multiple messages.

    Parsing a transmission will result in an ordered list of parsed messages
    (taric objects we need to try and import)
    """

    def __init__(self, transaction: bs4.Tag, index):
        """
        Responsible for representing a parsed TARIC transaction.

        Args:
            transaction: (required) bs4.Tag, The containing XML tag that contains the transaction data
            index: (required)
        """
        self.parsed_messages: List[MessageParser] = []
        self.taric_objects = []
        self.index = index

        self.messages_xml_tags = transaction.find_all("env:app.message")

        for message_xml in self.messages_xml_tags:
            self.parsed_messages.append(MessageParser(message_xml))

        for message in self.parsed_messages:
            self.taric_objects.append(message.taric_object)


class MessageParser:
    """Responsible for representing a parsed TARIC message."""

    def __init__(self, message: bs4.Tag):
        """
        Initialise a message parser instance.

        This object represents a parsed TARIC3 message - the container for all object types, e.g. goods nomenclature

        Args:
            message: (required) bs4.Tag, The containing XML tag that contains the message data
        """

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

    def can_populate_child_attrs_from_history(self):
        """
        Determines if an object can be updated without all child parsers
        present.

        Returns:
            bool, indicates if the parsed object can be updated without all children present
        """

        if self.update_type != validators.UpdateType.CREATE:
            # child objects allowed to be populated from history on updates
            return self.taric_object.__class__.allow_update_without_children

        return False

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


class BaseTaricParser:
    """
    This object represents a TARIC3 parsed model, this is the object that does a
    lot of the work, connecting the TARIC3 data and makes ORM models. There are
    a few key concepts worth documenting below.

    value_mapping :
        This dictionary (that may change to an array of models at some point) has key : value pairs that are used to
        map TARIC3 is values from the XML to a subclass of this model and at the same time, change the name of the
        field if needed. Values that don't need mapping to a new name just import with that name (but replacing full
        stops with underscores)

        the value mapping allows at processing time, for values to be renamed in preparation to
        represent the ORM fields. The structure is:

        {
            taric3_xml_field_name: parser_field_name
        }

        Where the left side (key) is the name of the field in XML, and the right side (value) is the
        destination field on the parser.

        Additional Note:
        Some values represent a foreign key, for example : additional_code__sid

        note the double underscore - like filtering in django ORM, this represents a relationship

        If a field name has double underscore, firstly the property e.g. 'additional_code' must exist on the destination
        model in the django ORM, it will be checked. and secondly, the field after the first double underscore must
        exist on the related model, if not it will not import.
    """

    transaction_id: int = None
    record_code: str = None
    subrecord_code: str = None
    xml_object_tag: str = None
    update_type: int = None
    update_type_name: str = None
    links_valid: bool = None
    value_mapping = {}
    model_links = []
    parent_parser = None
    data_fields = []
    issues = []
    parent_handler = None
    non_taric_additional_fields = []
    model = None
    identity_fields = []
    import_changes = True

    # Properties to explicitly define behaviour
    allow_update_without_children = False
    updates_allowed = True
    deletes_allowed = True
    skip_identity_check = False

    def __init__(self):
        """Initialises a blank instance of BaseTaricParser, with default
        values."""
        self.issues = []
        self.sequence_number = None
        self.model = None

    def links(self) -> list[ModelLink]:
        """
        Get defined links to other models.

        Returns:
            list[ModelLink], A list of model link objects defined on the mdoel
        """
        if self.model_links is None:
            raise Exception(
                f"No model defined for {self.__class__.__name__}, is this correct?",
            )

        return self.model_links

    def model_query_parameters(self) -> dict:
        """
        Get the models query parameters, to search for it, and parent objects in
        the import data and in the database.

        Returns:
            dict, a dictionary of the parsers identity fields, and the corresponding values.
        """
        query_args = {}
        for identity_field in self.identity_fields:
            query_arg_value = getattr(self, identity_field)

            if query_arg_value is None or query_arg_value == "":
                raise Exception(
                    f"No value for identity field {query_arg_value} for object : {self.__class__.__name__}",
                )

            query_args[identity_field] = query_arg_value

        if len(query_args.keys()) == 0:
            raise Exception(
                f"No arguments present for object : {self.__class__.__name__}",
            )

        return query_args

    def missing_child_attributes(self):
        """
        When a parent object that has children for example a description that
        also contains description period properties is not fully populated, for
        example the period is not present in the import, and the description is
        being created (not updated) there is no way to populate the period.

        This method is designed to highlight this issue
        """

        # check if the object has children, if not - return false
        child_parsers = ParserHelper.get_child_parsers(self)
        if len(child_parsers) == 0:
            return None

        # if it does, get the fields that should be populated by a child relationship and return true, and add a import
        # issue to the object.
        result = {}

        for child_parser in child_parsers:
            field_sets = child_parser.identity_fields_for_parent()
            for child_field in field_sets.keys():
                parent_field = field_sets[child_field]

                if not hasattr(self, parent_field):
                    # Guard clause
                    raise Exception(
                        f"Field referenced by child {child_parser.__name__} : {child_field} "
                        f"does not exist on parent {self.__class__.__name__} : {parent_field}",
                    )

                # Include attribute in response if empty
                if getattr(self, parent_field) is None:
                    if str(child_parser.__name__) in result.keys():
                        result[str(child_parser.__name__)].append(child_field)
                    else:
                        result[str(child_parser.__name__)] = [child_field]

        return result

    def is_child_for(self, potential_parent) -> bool:
        """
        Returns a boolean to indicate of the current is associated with the
        potential parent.

        Args:
            potential_parent: (required) BaseTaricParser, A parsed object that needs to be checked against.

        Returns:
            bool, indicating if the potential_parent matches the identity keys the child has.
        """
        if (
            potential_parent.is_child_object()
            or potential_parent.__class__.model != self.__class__.model
        ):
            return False

        identity_fields = self.get_identity_fields_and_values_for_parent()

        # guard clause
        if len(identity_fields.keys()) == 0:
            raise Exception("No parent identity fields presented")

        match = True
        for identity_field in identity_fields.keys():
            if (
                getattr(potential_parent, identity_field)
                != identity_fields[identity_field]
            ):
                match = False

        return match

    def get_identity_fields_and_values_for_parent(self):
        """Return a dict of values to be used to query the parent, using the
        child values."""
        result = {}

        for field in self.identity_fields_for_parent():
            result[self.identity_fields_for_parent()[field]] = getattr(self, field)

        return result

    @classmethod
    def identity_fields_for_parent(cls, include_optional=False) -> dict:
        """
        Returns a dictionary of identity keys and values that will link the
        child to the parent.

        Args:
            include_optional: bool, if the relationship is optional it will not be included if include_optional is false

        Returns:
            dict, a dictionary of field mappings between child and parent parser objects
        """

        # guard clauses
        if cls.parent_parser is None:
            raise Exception(f"Model {cls.__name__} has no parent parser")

        if cls.model_links is None or cls.model_links == []:
            raise Exception(
                f"Model {cls.__name__} appears to have a parent parser but no model links",
            )

        matched_parent_class = False
        for link in cls.model_links:
            if link.model == cls.parent_parser.model:
                matched_parent_class = True
        if not matched_parent_class:
            raise Exception(
                f"Model {cls.__name__} appears to not have a model links to the parent model",
            )

        key_fields = {}
        for model_link in cls.model_links:
            # match link to target model for parser - then we can extract the key fields we need to match for the object
            if model_link.model == cls.model:
                for model_link_field in model_link.fields:
                    if not model_link.optional or (
                        model_link.optional and include_optional
                    ):
                        key_fields[
                            model_link_field.parser_field_name
                        ] = model_link_field.object_field_name

        return key_fields

    def populate(
        self,
        transaction_id: int,
        record_code: str,
        subrecord_code: str,
        sequence_number: int,
        data: dict,
    ):
        """
        Populate the parser from the defined properties and data.

        Args:
            transaction_id: (required) int, The transaction ID from TARIC XML
            record_code: (required) str,  record code from TARIC XML
            subrecord_code: (required) str, subrecord code from TARIC XML
            sequence_number: (required) int, sequence number from TARIC XML
            data: (required) dict, data from TARIC XML

        Returns:
            None, all actions are performed on the current object
        """
        # standard data
        self.transaction_id = transaction_id
        if self.record_code != record_code:
            raise Exception(
                f"Record code mismatch : expected : {self.record_code}, got : {record_code} - data: {data}, Type: {self.__class__.__name__}",
            )
        if self.subrecord_code != subrecord_code:
            raise Exception(
                f"Sub-record code mismatch : expected : {self.subrecord_code}, got : {subrecord_code} - data: {data}, Type: {self.__class__.__name__}",
            )

        self.sequence_number = sequence_number

        # model specific data
        for data_item_key in data.keys():
            # some fields like language_id need to be skipped - we only care about en
            if data_item_key in EXCLUDED_FIELDS_FOR_POPULATION:
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
                elif field_data_type == datetime:
                    if field_data_raw is not None:
                        field_data_typed = datetime.fromisoformat(field_data_raw)
                elif field_data_type == int:
                    field_data_typed = int(field_data_raw)
                elif field_data_type == float:
                    field_data_typed = float(field_data_raw)
                elif field_data_type == bool:
                    if field_data_raw in ["1", "Y"]:
                        field_data_typed = True
                    elif field_data_raw in ["0", "N"]:
                        field_data_typed = False
                    else:
                        raise Exception(
                            f"data value for bool : {field_data_raw} not handled, should only be 1 or 0, {mapped_data_item_key}",
                        )
                else:
                    raise Exception(
                        f"data type {field_data_type.__name__} not handled, does the handler have the correct data type?",
                    )

                setattr(self, mapped_data_item_key, field_data_typed)
            else:
                raise Exception(
                    f"{self.xml_object_tag} {self.__class__.__name__} does not have a {mapped_data_item_key} attribute, and "
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

    def get_linked_model(
        self,
        fields_and_values: dict,
        related_model,
        transaction: Transaction,
    ):
        """
        Get the linked model from the existing database records.

        Args:
            fields_and_values: dict, dictionary of fields and properties that are used to query the database
            related_model: TrackedModel class, The tracked model that is to be queried
            transaction: Transaction, The transaction (in the database) that the query can perform up to.

        Returns:
            TrackedModel, when matched
            None, When not matched

        Exception:
            When multiple models are matched which is invalid and should not happen normally
        """
        models = related_model.objects.approved_up_to_transaction(transaction).filter(
            **fields_and_values
        )

        if models.count() == 1:
            return models.first()
        elif models.count() > 1:
            filtered_models = []
            for model in models:
                if hasattr(model, "valid_between"):
                    # Check if this record is current
                    if date.today() in model.valid_between:
                        filtered_models.append(model)

                elif hasattr(model, "validity_start"):
                    # check for latest
                    if (
                        len(filtered_models) > 0
                        and model.validity_start > filtered_models[0].validity_start
                    ):
                        filtered_models = [model]
                    elif len(filtered_models) == 0:
                        filtered_models = [model]

            if len(filtered_models) == 1:
                return filtered_models[0]

            raise Exception(
                f"multiple models matched query for {related_model.__name__} using {fields_and_values}, please check data and query",
            )
        else:
            return None

    def model_attributes(
        self,
        transaction: Transaction,
        raise_error_if_no_match=True,
        include_non_taric_attributes=False,
    ) -> dict:
        """
        Returns a dictionary of model attributes, for use iun populating
        database models, and other uses.

        Args:
            transaction: (required) Transaction, The transaction used to search the database up to for models
            raise_error_if_no_match: (optional) bool, Flag to indicate if an exception should be raised if a related model cant be matched.
            include_non_taric_attributes: (optional) bool, flag to indicate if output should include non TARIC attributes. There are some edge cases where this is needed.

        Returns:
            dict, Dictionary of populated attributes for the mdoel
        """
        additional_excluded_variable_names = []

        model_attributes = {}

        # resolve links to other models
        for link in self.model_links:
            # check all fields link to the same property / linked model
            property_list = []
            for field in link.fields:
                additional_excluded_variable_names.append(field.parser_field_name)
                property_list.append(field.parser_field_name.split("__")[0])

            property_list = list(dict.fromkeys(property_list))

            # if an exception raises from the two checks below, it indicates that there is an issue with the parser
            # in some way, these circumstances should not occur if the parsers are good and well-formed .
            if len(property_list) > 1:
                raise Exception(
                    f"multiple properties for link : {self.__class__.__name__} : {property_list}",
                )
            elif len(property_list) == 0:
                raise Exception(f"no properties for link : {self.__class__.__name__}")

            fields_and_values = {}
            for field in link.fields:
                fields_and_values[field.object_field_name] = getattr(
                    self,
                    field.parser_field_name,
                )

            linked_model = self.get_linked_model(
                fields_and_values,
                link.model,
                transaction,
            )

            if linked_model:
                # There are cases where this will not return a value, which is fine when the linked
                # model is also in the same transaction

                model_attributes[property_list[0]] = linked_model
            elif raise_error_if_no_match and not link.optional:
                report_item = ImportIssueReportItem(
                    self.xml_object_tag,
                    ParserHelper.get_parser_by_model(link.model).xml_object_tag,
                    fields_and_values,
                    f"Missing expected linked object {ParserHelper.get_parser_by_model(link.model).__name__}",
                    taric_change_type=self.update_type_name,
                    object_details=str(self),
                    transaction_id=self.transaction_id,
                )

                self.issues.append(report_item)

        for model_field in vars(self).keys():
            if (
                model_field
                in EXCLUDED_PARSER_PROPERTIES + additional_excluded_variable_names
            ):
                continue

            # Only append non data fields to the model, data fields are used to collect and attach via a defined
            # column in json format - mainly used for quota events
            if model_field not in self.data_fields:
                if hasattr(self.__class__.model, model_field):
                    model_attributes[model_field] = getattr(self, model_field)
                else:
                    raise Exception(
                        f"Error creating model {self.__class__.model.__name__}, model does not have an attribute {model_field}",
                    )

        # QuotaEvents have the subrecord code recorded in the database table to distinguish the type
        if self.__class__.model == QuotaEvent:
            model_attributes["subrecord_code"] = self.subrecord_code

        # there are instances where no taric fields have defaults, and if not populated will cause an exception when
        # data is written to the database. non_taric_attribute is a property available in each of the parsers and can be
        # populated with these values, and will receive a default value from the parser model on creation
        if include_non_taric_attributes:
            for non_taric_attribute in self.non_taric_additional_fields:
                model_attributes[non_taric_attribute] = getattr(
                    self,
                    non_taric_attribute,
                )

        # finally, if this model; has a parent, remove sid, code and group_id which will be linked to the model it should be updating
        if self.parent_parser:
            for field in ["sid", "code", "group_id"]:
                if field in model_attributes.keys() and field in self.identity_fields:
                    del model_attributes[field]

        return model_attributes

    def can_save_to_model(self) -> bool:
        """
        Can the model be saved to the database.

        This method checks that the parser that represents a TARIC object can be saved to a TAP model by checking associated issues recorded during validation

        Returns:
            bool, value indicating if the model can be saved
        """
        # This method checks that the parser represents an object that can be saved to a TAP model, and not a child
        # object that simply holds attributes.
        # This is determined by the lack of a parent_parser, if a parent parser is present that means the model will be
        # appended to a parent and should not be saved directly
        if self.parent_parser:
            if self.update_type == validators.UpdateType.UPDATE:  # update
                return True
            return False
        return True

    def is_child_object(self):
        """
        Is the object a child object, meaning does it have a parent it needs to
        append attributes to.

        Returns:
            bool, boolean indicating it is or is not a child object in the TAP database model
        """
        return self.parent_parser is not None


class ParserHelper:
    @staticmethod
    def get_parser_by_model(model):
        """
        Gets the corresponding parser for the presented model.

        Args:
            model: TrackedModel Class, The class to get the parser class for

        Returns:
            BaseTaricParser, The parser class used to represent the presented model

        Exception:
            If no matching parser class is found.
        """
        # get all classes that can represent an imported taric object
        classes = ParserHelper.get_parser_classes()

        # iterate through classes and find the one that matches the tag or error
        for cls in classes:
            if cls.model == model and cls.parent_parser is None:
                return cls

        raise Exception(
            f"No parser class found for parsing {model.__name__}. Have you imported all required parser models? ",
        )

    @staticmethod
    def get_child_parsers(parser: BaseTaricParser):
        """
        Returns a list of child parsers associated with the presented parser.

        Args:
            parser: (required) BaseTaricParser, The parent parser class, to get the children for.

        Returns:
            list, list containing all child parsers associated with the provided model
        """
        result = []

        parser_classes = ParserHelper.get_parser_classes()
        for parser_class in parser_classes:
            if parser_class.parent_parser and parser_class.parent_parser == type(
                parser,
            ):
                result.append(parser_class)

        return result

    @staticmethod
    def get_parser_by_tag(object_type: str):
        """
        Returns the child parsers associated with the presented XML tag, from
        the TARIC spec.

        Args:
            object_type: (required) str, string representing the XML tag

        Returns:
            BaseTaricParser Class, class matching the provided tag

        Exception:
            raises if there is no match
        """
        # get all classes that can represent an imported taric object
        classes = ParserHelper.get_parser_classes()

        # iterate through classes and find the one that matches the tag or error
        for cls in classes:
            if cls.xml_object_tag == object_type:
                return cls

        raise Exception(f"No parser class matching {object_type}")

    @staticmethod
    def get_parser_classes() -> list[BaseTaricParser]:
        """
        List of parser classes.

        Returns:
            list[BaseTaricParser], list of all classes that parse TARIC objects
        """
        return ParserHelper.subclasses_for(BaseTaricParser)

    @staticmethod
    def subclasses_for(cls) -> list:
        """
        Recursive, Returns all subclasses of the provided class.

        Args:
            cls: class, Any class, that you need all the subclasses for.

        Returns:
            list, list of classes
        """
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(ParserHelper.subclasses_for(subclass))

        return all_subclasses
