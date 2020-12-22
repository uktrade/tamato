"""Parsers for TARIC envelope entities."""
import logging
import os
import time
import xml.etree.ElementTree as etree
from typing import Any
from typing import Mapping
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.transaction import atomic
from lxml import etree

from common import models
from common.validators import UpdateType
from importer.namespaces import ENVELOPE
from importer.namespaces import nsmap
from importer.namespaces import Tag
from importer.nursery import get_nursery
from importer.parsers import ElementParser
from importer.parsers import ParserError
from importer.parsers import TextElement
from taric.models import Envelope
from taric.models import EnvelopeTransaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

now = time.time()

START_TRANSACTION = int(os.getenv("STARTING_TRANSACTION", 0))


class RecordParser(ElementParser):
    """Parser for TARIC3 `record` element."""

    tag = Tag("record")
    transaction_id = TextElement(Tag("transaction.id"))
    record_code = TextElement(Tag("record.code"))
    subrecord_code = TextElement(Tag("subrecord.code"))
    sequence_number = TextElement(Tag("record.sequence.number"))
    update_type = TextElement(Tag("update.type"))

    def save(self, data: Mapping[str, Any], transaction_id: int):
        """
        Save the Record to the database.

        :param data: A dict of the parsed element, mapping field names to values
        :param transaction_id: The primary key of the transaction to add the record to
        """
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
        """
        Save the contained records to the database.

        :param data: A dict of parsed element, mapping field names to values
        :param transaction_id: The primary key of the transaction to add records to
        """
        for record_data in data["record"]:
            self.record.save(record_data, transaction_id)


class TransactionParser(ElementParser):
    """Parser for TARIC3 `transaction` element."""

    tag = Tag("transaction", prefix=ENVELOPE)
    message = MessageParser(many=True)

    workbasket_status = None
    tamato_username = None

    def save(
        self,
        data: Mapping[str, Any],
        envelope: Envelope,
    ):
        """
        Save the transaction and the contained records to the database.

        :param data: A dict of the parsed element, containing at least an "id" and list
            of "message" dicts
        :param envelope_id: The ID of the containing Envelope
        :param workbasket_id: The primary key of the workbasket to add transactions to
        """
        logging.debug(f"Saving transaction {self.data['id']}")

        composite_key = str(envelope.envelope_id) + self.data["id"]
        try:
            transaction = models.Transaction.objects.create(
                composite_key=composite_key,
                workbasket=self.parent.workbasket,
                order=int(self.data["id"]),
                import_transaction_id=int(self.data["id"]),
            )

        except IntegrityError:
            return

        EnvelopeTransaction.objects.create(
            envelope=envelope,
            transaction=transaction,
            order=int(self.data["id"]),
        )

        for message_data in data["message"]:
            self.message.save(message_data, transaction.id)
        self.parent.workbasket.clean()

    def end(self, element: etree.Element):
        super().end(element)
        if element.tag == self.tag:
            logging.debug(f"Saving import {self.data['id']}")
            if int(self.data["id"]) % 1000 == 0:
                logger.info(
                    "%s transactions done in %d seconds",
                    self.data["id"],
                    int(time.time() - now),
                )
            if int(self.data["id"]) < START_TRANSACTION:
                return True
            with atomic():
                self.save(
                    self.data,
                    envelope=self.parent.envelope,
                )
            return True


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
        self.workbasket_status = workbasket_status or WorkflowStatus.PUBLISHED.value
        self.tamato_username = tamato_username or settings.DATA_IMPORT_USERNAME
        self.save = save
        self.envelope: Optional[Envelope] = None
        self.workbasket: Optional[WorkBasket] = None

    def start(self, element: etree.Element, parent: ElementParser = None):
        super().start(element, parent)

        if element.tag == self.tag:
            self.envelope_id = element.get("id")

            user = get_user_model().objects.get(username=self.tamato_username)
            self.workbasket, _ = WorkBasket.objects.get_or_create(
                title=f"Data Import {self.envelope_id}",
                author=user,
                approver=user,
                status=self.workbasket_status,
            )
            self.envelope, _ = Envelope.objects.get_or_create(
                envelope_id=self.envelope_id,
            )

    def end(self, element):
        super().end(element)

        if element.tag == self.tag:
            nursery = get_nursery()
            logger.info("cache size: %d", len(nursery.cache.keys()))
            nursery.clear_cache()


def process_taric_xml_stream(taric_stream, status, username):
    """
    Parse a TARIC XML stream through the import handlers.

    This will load the data from the stream into the database.
    """
    xmlparser = etree.iterparse(taric_stream, ["start", "end", "start-ns"])
    handler = EnvelopeParser(
        workbasket_status=status,
        tamato_username=username,
    )
    for event, elem in xmlparser:
        if event == "start":
            handler.start(elem)

        if event == "start_ns":
            nsmap.update([elem])

        if event == "end":
            if handler.end(elem):
                elem.clear()
