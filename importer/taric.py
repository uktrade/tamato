import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from common.validators import UpdateType
from importer.namespaces import ENVELOPE
from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import ParserError
from importer.parsers import TextElement
from workbaskets import models


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

    def save(self, data, envelope_id, workbasket_status=None, tamato_username=None):
        logging.debug(f"Saving transaction {self.data['id']}")
        if workbasket_status is None:
            workbasket_status = models.WorkflowStatus.AWAITING_APPROVAL.value

        username = tamato_username or settings.DATA_IMPORT_USERNAME

        workbasket, _ = models.WorkBasket.objects.get_or_create(
            title=f"Data Import {envelope_id}",
            author=User.objects.get(username=username),
            status=workbasket_status,
        )

        transaction, _ = models.Transaction.objects.get_or_create(
            pk=int(self.data["id"]), workbasket=workbasket
        )
        logging.debug(f"WorkBasket {workbasket.pk}: {workbasket.title}")

        for message_data in self.data["message"]:
            self.message.save(message_data, workbasket.pk)


class EnvelopeError(ParserError):
    pass


class Envelope(ElementParser):
    tag = Tag("envelope", prefix=ENVELOPE)
    transaction = Transaction(many=True)

    def __init__(self, workbasket_status=None, tamato_username=None, save: bool = True, **kwargs):
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
            logging.debug(f"Saving import {self.data['id']}")
            with transaction.atomic():
                for transaction_data in self.data["transaction"]:
                    self.transaction.save(
                        transaction_data,
                        envelope_id=self.data["id"],
                        workbasket_status=self.workbasket_status,
                        tamato_username=self.tamato_username,
                    )
