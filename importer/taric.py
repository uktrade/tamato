"""Parsers for TARIC envelope entities."""
import logging
from typing import Any
from typing import Mapping

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from common import models
from common.validators import UpdateType
from importer.namespaces import ENVELOPE
from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import ParserError
from importer.parsers import TextElement
from taric.models import Envelope
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class RecordParser(ElementParser):
    """Parser for TARIC3 `record` element."""

    tag = Tag("record")
    transaction_id = TextElement(Tag("transaction.id"))
    record_code = TextElement(Tag("record.code"))
    subrecord_code = TextElement(Tag("subrecord.code"))
    sequence_number = TextElement(Tag("record.sequence.number"))
    update_type = TextElement(Tag("update.type"))

    def save(self, data: Mapping[str, Any], transaction_id: int):
        """Save the Record to the database.

        :param data: A dict of the parsed element, mapping field names to values
        :param transaction_id: The primary key of the transaction to add the record to
        """
        print(f"RecordParser.save({data})")
        method_name = {
            str(UpdateType.UPDATE): "update",
            str(UpdateType.DELETE): "delete",
            str(UpdateType.CREATE): "create",
        }[data["update_type"]]

        for parser, field_name in self._field_lookup.items():
            record_data = data.get(field_name)
            if record_data and hasattr(parser, method_name):
                getattr(parser, method_name)(record_data, transaction_id)


class MessageParser(ElementParser):
    """Parser for TARIC3 `message` element."""

    tag = Tag("app.message", prefix=ENVELOPE)
    record = RecordParser(many=True)

    def save(self, data: Mapping[str, Any], transaction_id: int):
        """Save the contained records to the database.

        :param data: A dict of parsed element, mapping field names to values
        :param transaction_id: The primary key of the transaction to add records to
        """
        for record_data in data["record"]:
            self.record.save(record_data, transaction_id)


class TransactionParser(ElementParser):
    """Parser for TARIC3 `transaction` element."""

    tag = Tag("transaction", prefix=ENVELOPE)
    message = MessageParser(many=True)

    def save(
        self,
        data: Mapping[str, Any],
        envelope: Envelope,
        workbasket: WorkBasket,
    ):
        """Save the transaction and the contained records to the database.

        :param data: A dict of the parsed element, containing at least an "id" and list
        of "message" dicts
        :param envelope_id: The ID of the containing Envelope
        :param workbasket_id: The primary key of the workbasket to add transactions to
        """
        logging.debug(f"Saving transaction {self.data['id']}")
        transaction = workbasket.get_transaction(
            import_transaction_id=int(data["id"]),
        )
        transaction.envelopes.add(envelope, through_defaults={"order": int(data["id"])})

        for message_data in data["message"]:
            self.message.save(message_data, transaction.id)


class EnvelopeError(ParserError):
    pass


class EnvelopeParser(ElementParser):
    tag = Tag("envelope", prefix=ENVELOPE)
    transaction = TransactionParser(many=True)

    def __init__(
        self, workbasket_status=None, tamato_username=None, save: bool = True, **kwargs
    ):
        super().__init__(**kwargs)
        self.last_transaction_id = -1
        self.workbasket_status = workbasket_status
        self.tamato_username = tamato_username
        self.save = save

    def end(self, element):
        super().end(element)

        if element.tag == self.transaction.tag:
            tx_id = int(self.transaction.data["id"])
            if tx_id <= self.last_transaction_id:
                raise EnvelopeError(f"Transaction ID {tx_id} is out of order")
            self.last_transaction_id = tx_id

        if element.tag == self.tag and self.save:
            logging.debug(f"Saving import %d", self.data["id"])
            envelope = Envelope.objects.create(envelope_id=self.data["id"])

            workbasket, _ = WorkBasket.objects.get_or_create(
                title=f"Data Import {self.data['id']}",
                author=get_user_model().objects.get(
                    username=self.tamato_username or settings.DATA_IMPORT_USERNAME
                ),
                status=self.workbasket_status or WorkflowStatus.AWAITING_APPROVAL,
            )
            logging.debug(f"WorkBasket {workbasket.id}: {workbasket.title}")

            for transaction_data in self.data["transaction"]:
                self.transaction.save(
                    transaction_data,
                    envelope=envelope,
                    workbasket=workbasket,
                )
