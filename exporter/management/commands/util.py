import sys

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from lxml import etree

from common.tests.util import validate_taric_xml_record_order


class TransactionsBaseCommand(BaseCommand):
    def validate_envelope(self, envelope_data):
        """Exit with error if envelope does not validate"""
        with open(settings.TARIC_XSD) as xsd_file:
            schema = etree.XMLSchema(etree.parse(xsd_file))
            xml = etree.XML(envelope_data)

            try:
                schema.assertValid(xml)
            except etree.DocumentInvalid as err:
                error_log = err.error_log
                raise CommandError(
                    f"Envelope did not validate against XSD:\n{error_log}"
                )
            try:
                validate_taric_xml_record_order(xml)
            except AssertionError as e:
                sys.exit(e.args[0])
