import logging
import os
import time
import xml.etree.ElementTree as etree

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import reset_queries
from django.db import transaction
from lxml import etree

from common.validators import UpdateType
from importer.namespaces import ENVELOPE
from importer.namespaces import nsmap
from importer.namespaces import Tag
from importer.nursery import get_nursery
from importer.parsers import ElementParser
from importer.parsers import ParserError
from importer.parsers import TextElement
from workbaskets import models


now = time.time()

START_TRANSACTION = int(os.getenv("STARTING_TRANSACTION", 0))


class Record(ElementParser):
    tag = Tag("record")
    transaction_id = TextElement(Tag("transaction.id"))
    record_code = TextElement(Tag("record.code"))
    subrecord_code = TextElement(Tag("subrecord.code"))
    sequence_number = TextElement(Tag("record.sequence.number"))
    update_type = TextElement(Tag("update.type"))

    def save(self, data, workbasket_id):
        method_name = {
            str(UpdateType.UPDATE.value): "update",
            str(UpdateType.DELETE.value): "delete",
            str(UpdateType.CREATE.value): "create",
        }[data["update_type"]]

        for parser, field_name in self._field_lookup.items():
            record_data = data.get(field_name)
            if record_data and hasattr(parser, method_name):
                getattr(parser, method_name)(record_data, workbasket_id)


class Message(ElementParser):
    tag = Tag("app.message", prefix=ENVELOPE)
    record = Record(many=True)

    def save(self, data, workbasket_id):
        for record_data in data["record"]:
            self.record.save(record_data, workbasket_id)


class Transaction(ElementParser):
    tag = Tag("transaction", prefix=ENVELOPE)
    message = Message(many=True)

    workbasket_status = None
    tamato_username = None

    def save(self, envelope_id):
        reset_queries()
        logging.debug(f"Saving transaction {self.data['id']}")

        composite_key = envelope_id + self.data["id"]
        try:
            models.Transaction.objects.create(
                composite_key=composite_key, workbasket=self.parent.workbasket
            )
        except IntegrityError:
            return

        for message_data in self.data["message"]:
            self.message.save(message_data, self.parent.workbasket.pk)
        self.parent.workbasket.clean()

    def end(self, element: etree.Element):
        super().end(element)
        if element.tag == self.tag:
            logging.debug(f"Saving import {self.data['id']}")
            if int(self.data["id"]) % 1000 == 0:
                print(
                    f"{self.data['id']} transactions done in {int(time.time() - now)} seconds"
                )

            if int(self.data["id"]) < START_TRANSACTION:
                return True
            with transaction.atomic():
                self.save(
                    envelope_id=self.parent.envelope_id,
                )
            return True


class EnvelopeError(ParserError):
    pass


class Envelope(ElementParser):
    tag = Tag("envelope", prefix=ENVELOPE)
    transaction = Transaction(many=True)

    def __init__(
        self, workbasket_status=None, tamato_username=None, save: bool = True, **kwargs
    ):
        super().__init__(**kwargs)
        self.last_transaction_id = -1
        self.workbasket_status = (
            workbasket_status or models.WorkflowStatus.PUBLISHED.value
        )
        self.tamato_username = tamato_username or settings.DATA_IMPORT_USERNAME
        self.save = save
        self.envelope_id = None
        self.workbasket = None

    def start(self, element: etree.Element, parent: ElementParser = None):
        super(Envelope, self).start(element, parent)

        if element.tag == self.tag:
            self.envelope_id = element.get("id")

            user = User.objects.get(username=self.tamato_username)
            self.workbasket, _ = models.WorkBasket.objects.get_or_create(
                title=f"Data Import {self.envelope_id}",
                author=user,
                approver=user,
                status=self.workbasket_status,
            )

    def end(self, element):
        super().end(element)

        if element.tag == self.tag:
            nursery = get_nursery()
            print("cache size", len(nursery.cache.keys()))
            nursery.clear_cache()


def process_taric_xml_stream(taric_stream, status, username):
    """
    Parse a TARIC XML stream through the import handlers

    This will load the data from the stream into the database.
    """
    xmlparser = etree.iterparse(taric_stream, ["start", "end", "start-ns"])
    handler = Envelope(
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
