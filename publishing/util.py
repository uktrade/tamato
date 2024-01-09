import logging
import os

from django.conf import settings
from lxml import etree

from common.util import parse_xml
from common.xml.namespaces import nsmap

logger = logging.getLogger(__name__)

model_taric_record_count = dict(
    {
        "AdditionalCodeDescription": 2,
        "AdditionalCodeType": 2,
        "AdditionalCode": 1,
        "CertificateDescription": 2,
        "CertificateType": 2,
        "Certificate": 1,
        "FootnoteAssociationGoodsNomenclature": 1,
        "GoodsNomenclatureDescription": 2,
        "GoodsNomenclatureIndent": 1,
        "GoodsNomenclatureOrigin": 1,
        "GoodsNomenclatureSuccessor": 1,
        "GoodsNomenclature": 1,
        "FootnoteDescription": 2,
        "FootnoteType": 2,
        "Footnote": 1,
        "GeographicalAreaDescription": 2,
        "GeographicalMembership": 1,
        "GeographicalArea": 1,
        "DutyExpression": 2,
        "AdditionalCodeTypeMeasureType": 1,
        "FootnoteAssociationMeasure": 1,
        "MeasureAction": 2,
        "MeasureComponent": 1,
        "MeasureConditionCode": 2,
        "MeasureConditionComponent": 1,
        "MeasureCondition": 1,
        "MeasureExcludedGeographicalArea": 1,
        "MeasureTypeSeries": 2,
        "MeasureType": 2,
        "Measure": 1,
        "MeasurementUnitQualifier": 2,
        "MeasurementUnit": 2,  # correct, has dependent
        "Measurement": 1,
        "MonetaryUnit": 2,
        "QuotaAssociation": 1,
        "QuotaBlocking": 1,
        "QuotaDefinition": 1,
        "QuotaEvent": 1,
        "QuotaOrderNumberOriginExclusion": 1,
        "QuotaOrderNumberOrigin": 1,
        "QuotaOrderNumber": 1,
        "QuotaSuspension": 1,
        "Amendment": 1,
        "Group": 2,
        "Regulation": 1,
        "Replacement": 1,
        "Suspension": 2,
        "Termination": 1,
    },
)
"""TrackedModel types make up the keys of the dictionary and they map to the
TARIC record count they represent These records can be found in each of the
models under /jinja2/taric/*.xml."""


class TaricDataAssertionError(AssertionError):
    pass


# These validate functions are extracted from exporter/serializers.py
# This is due to the fact the serializer is set up to support multiple enevelope renders
# and the workbaskets checks break such an implementation
# without a refeactor of the serializer.

# To support multiple envelopes the functions would have to return the envelope metadata
# extract the workbaskets check into the function that loops over the list of envelopes
# and compare the workbaskets expected results with the multiple envelope results returned.
# This will enable support for multiple envelopes generated from QUEUED workbasketd
# Currently this workbasket check only checks against a single envelope
# and would not support the rendering of multiple envelopes


def validate_envelope(
    envelope_file: bytes,
    workbaskets,
    skip_declaration=False,
) -> None:
    """
    Validate envelope content for XML issues and data missing & order issues.

    Catches and re-raises DocumentInvalid and TaricDataAssertionError
    exceptions, although other exceptions may be possible.
    """

    if not skip_declaration:
        position_before = envelope_file.tell()
        valid_xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>'
        xml_declaration = envelope_file.read(len(valid_xml_declaration))

        if xml_declaration != valid_xml_declaration:
            logger.warning(
                f"Expected XML declaration first line of envelope to be "
                f"XML encoding declaration, but found: {xml_declaration}",
            )

        envelope_file.seek(position_before, os.SEEK_SET)

    with open(settings.PATH_XSD_TARIC) as xsd_file:
        schema = etree.XMLSchema(parse_xml(xsd_file))

    xml = parse_xml(envelope_file)

    try:
        schema.assertValid(xml)
    except etree.DocumentInvalid as e:
        logger.error(f"Envelope did not validate against XSD: {e}")
        raise

    try:
        validate_taric_xml_records(xml, workbaskets)
    except TaricDataAssertionError as e:
        logger.error(e.args[0])
        raise


def get_expected_model_taric_record_count(tracked_model):
    expected_count = model_taric_record_count[tracked_model.__class__.__name__]

    # add clause for possible exclusion of Measurement, based on no measurement qualifier
    if tracked_model.__class__.__name__ == "Measurement":
        if not tracked_model.measurement_unit_qualifier:
            expected_count = 0

    return expected_count


def validate_taric_xml_records(xml, workbaskets):
    """
    Raise AssertionError if:

    - missing transactions (non-empty transactions only)
    - missing tracked_models (record)
    """

    # only validate against workbasket if workbasket available
    expected_record_count = 0
    workbasket_transaction_count = 0
    for transaction in workbaskets.ordered_transactions():
        tracked_models = transaction.tracked_models.record_ordering()
        if tracked_models.count():
            workbasket_transaction_count += 1
            for tracked_model in tracked_models:
                # dictionary that maps the tracked model class to taric record count
                expected_record_count += get_expected_model_taric_record_count(
                    tracked_model,
                )

    envelope_record_count = 0
    envelope_transaction_count = 0

    for transaction in xml.findall(".//env:transaction", namespaces=nsmap):
        # Count the number of records to compare with the workbasket tracked models
        envelope_transaction_count += 1
        envelope_record_count += len(
            transaction.findall(".//oub:record", namespaces=nsmap),
        )

    if not envelope_transaction_count:
        raise TaricDataAssertionError(
            f"Envelope does not have any transactions!",
        )
    elif envelope_record_count != expected_record_count:
        raise TaricDataAssertionError(
            f"Missing records in XML: {envelope_record_count}, while {expected_record_count} expected",
        )
    elif envelope_transaction_count != workbasket_transaction_count:
        raise TaricDataAssertionError(
            f"Envelope transaction count {envelope_transaction_count} don't match the workbasket transaction {workbasket_transaction_count}!",
        )
