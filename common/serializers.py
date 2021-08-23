import io
import logging
import os
from functools import cached_property
from typing import IO
from typing import List
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from drf_extra_fields.fields import DateRangeField
from lxml import etree
from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from common.models import TrackedModel
from common.models import Transaction
from common.renderers import Counter
from common.renderers import counter_generator
from common.util import TaricDateRange
from common.xml.namespaces import nsmap

logger = logging.getLogger(__name__)


class TARIC3DateRangeField(DateRangeField):
    child = serializers.DateField(
        input_formats=[
            "iso-8601",
            "%Y-%m-%d",
        ],  # default  # TARIC3 date format
    )
    range_type = TaricDateRange


class TrackedModelSerializerMixin(FlexFieldsModelSerializer):
    taric_template = serializers.SerializerMethodField()

    formats_with_template = {"xml"}

    def get_taric_template(self, object):
        return object.get_taric_template()

    def get_format(self):
        """
        Find the format of the request.

        This first checks the immediate serializer context, if not found it
        checks the request for query params. If that fails it checks the Accept
        header to see if any of the `self.formats_with_template` are within the
        header.
        """
        if self.context.get("format"):
            return self.context["format"]

        if self.context["request"].query_params.get("format"):
            return self.context["request"].query_params.get("format")

        for data_format in self.formats_with_template:
            if data_format in self.context["request"].accepted_media_type.lower():
                return data_format

    def to_representation(self, *args, **kwargs):
        """
        Removes the taric template field from formats that don't require it.

        By default the only format which keeps the taric_tempalte field is XML.
        """
        data = super().to_representation(*args, **kwargs)
        data_format = self.get_format()

        if data_format not in self.formats_with_template:
            if "taric_template" in data:
                data.pop("taric_template")

        return data


class ValiditySerializerMixin(serializers.ModelSerializer):
    date_format_string = "{:%Y-%m-%d}"
    valid_between = TARIC3DateRangeField()
    end_date = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()

    def get_start_date(self, obj):
        if obj.valid_between and obj.valid_between.lower:
            return self.date_format_string.format(obj.valid_between.lower)

    def get_end_date(self, obj):
        if obj.valid_between and obj.valid_between.upper:
            return self.date_format_string.format(obj.valid_between.upper)


class ValidityStartSerializerMixin(serializers.ModelSerializer):
    date_format_string = "{:%Y-%m-%d}"

    validity_start = serializers.DateField(
        input_formats=[
            "iso-8601",
            "%Y-%m-%d",
        ],  # default  # TARIC3 date format
    )
    start_date = serializers.SerializerMethodField()

    def get_start_date(self, obj):
        if obj.validity_start:
            return self.date_format_string.format(obj.validity_start)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "groups"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class TrackedModelSerializer(PolymorphicSerializer):
    model_serializer_mapping = {}

    @classmethod
    def register_polymorphic_model(cls, serializer):
        cls.model_serializer_mapping[serializer.Meta.model] = serializer
        return serializer

    def __init__(self, *args, child_kwargs=None, **kwargs):
        """
        This is a near direct copy from the base class - however it adds in
        the `child_kwargs` argument, allowing the serializer to pass certain
        kwargs to the child serializers and not use them itself.

        This is important for more custom serializers - such as using
        the `omit` keyword from rest_flex_fields.
        """
        super(PolymorphicSerializer, self).__init__(*args, **kwargs)

        model_serializer_mapping = self.model_serializer_mapping
        self.model_serializer_mapping = {}
        self.resource_type_model_mapping = {}

        kwargs.update(**(child_kwargs or {}))

        for model, serializer in model_serializer_mapping.items():
            resource_type = self.to_resource_type(model)
            if callable(serializer):
                serializer = serializer(*args, **kwargs)
                serializer.parent = self

            self.resource_type_model_mapping[resource_type] = model
            self.model_serializer_mapping[model] = serializer


class TransactionSerializer(serializers.ModelSerializer):
    tracked_models = serializers.SerializerMethodField()

    def get_tracked_models(self, obj):
        return TrackedModelSerializer(
            obj.tracked_models.annotate_record_codes().order_by(
                "record_code",
                "subrecord_code",
            ),
            many=True,
            read_only=True,
            context=self.context,
        ).data

    class Meta:
        model = Transaction
        fields = [
            "import_transaction_id",
            "tracked_models",
            "order",
        ]


class EnvelopeSerializer:
    """
    Streaming Envelope Serializer.

    This is not a Django Restful Framework Serializer.
    EnvelopeSerializer calls DRF serializers for the TrackedModels
    it needs to output.

    Transaction and message ids are handled and data may be split
    across multiple envelopes based on a size threshold.
    """

    MIN_ENVELOPE_SIZE = 4096  # 4k is arbitrary - the size is chosen for template size + min size of records.

    def __init__(
        self,
        output: IO,
        envelope_id: int,
        transaction_counter: Counter = counter_generator(),
        message_counter: Counter = counter_generator(),
        max_envelope_size: Optional[int] = None,
        format: str = "xml",
        newline: bool = False,
    ) -> None:
        self.output = output
        self.message_counter = message_counter
        self.envelope_id = envelope_id
        self.envelope_size = 0
        self.max_envelope_size = max_envelope_size
        if (
            max_envelope_size is not None
            and self.max_envelope_size < EnvelopeSerializer.MIN_ENVELOPE_SIZE
        ):
            raise ValueError(
                f"Max envelope size {max_envelope_size} is too small, it should be at least {EnvelopeSerializer.MIN_ENVELOPE_SIZE}.",
            )
        self.format = format
        self.newline = newline

    @cached_property
    def envelope_start_size(self):
        """
        Size in bytes of envelope start.

        Used as a padding value when calculating if an envelope is full.
        """
        return len(self.render_envelope_start().encode())

    @cached_property
    def envelope_end_size(self):
        """
        Size in bytes of envelope end.

        Used as a padding value when calculating if an envelope is full.
        """
        return len(self.render_envelope_end().encode())

    def __enter__(self):
        self.write(self.render_file_header())
        self.write(self.render_envelope_start())
        return self

    def __exit__(self, *_) -> None:
        self.write(self.render_envelope_end())

    def render_file_header(self) -> str:
        return render_to_string(
            template_name="common/taric/start_file.xml",
        )

    def render_envelope_start(self) -> str:
        return render_to_string(
            template_name="common/taric/start_envelope.xml",
            context={"envelope_id": self.envelope_id},
        )

    def render_envelope_body(
        self,
        models: List[TrackedModel],
        transaction_id: int,
    ) -> str:
        return render_to_string(
            template_name="workbaskets/taric/transaction.xml",
            context={
                "tracked_models": TrackedModelSerializer(
                    models,
                    many=True,
                    read_only=True,
                    context={"format": self.format},
                ).data,
                "transaction_id": transaction_id,
                "counter_generator": counter_generator,
                "message_counter": self.message_counter,
            },
        )

    def render_envelope_end(self) -> str:
        return render_to_string(template_name="common/taric/end_envelope.xml")

    def start_next_envelope(self) -> None:
        """Update any data ready ready for outputting the next envelope."""
        self.envelope_id += 1
        self.message_counter = counter_generator(start=1)

    def write(self, string_data: str) -> None:
        if isinstance(self.output, io.TextIOBase):
            self.envelope_size += len(string_data.encode())
            self.output.write(string_data)
            if self.newline:
                self.envelope_size += 1
                self.output.write("\n")
        else:
            # Binary mode
            bytes_data = string_data.encode()
            self.envelope_size += len(bytes_data)
            self.output.write(bytes_data)
            if self.newline:
                self.envelope_size += 1
                self.output.write(b"\n")

    def can_fit_one_envelope(self, total_size) -> bool:
        """Return True If total_size bytes would fit inside a single
        Envelope."""
        if self.max_envelope_size is None:
            return True

        return total_size <= self.max_envelope_size

    def is_envelope_full(self, object_size=0) -> bool:
        return not self.can_fit_one_envelope(self.envelope_size + object_size)

    def render_transaction(
        self,
        models: List[TrackedModel],
        transaction_id: int,
    ) -> None:
        """Render TrackedModels, splitting to a new Envelope if over-size."""
        if models:
            envelope_body = self.render_envelope_body(models, transaction_id)

            if self.is_envelope_full(len(envelope_body.encode())):
                self.write(self.render_envelope_end())
                self.start_next_envelope()
                self.write(self.render_envelope_start())

            self.write(envelope_body)


class TaricDataAssertionError(AssertionError):
    pass


def validate_envelope(envelope_file, skip_declaration=False):
    """
    Validate envelope content for XML issues and data order issues.

    raises DocumentInvalid | TaricDataAssertionError
    """
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    with open(settings.PATH_XSD_TARIC) as xsd_file:
        if skip_declaration:
            pos = envelope_file.tell()
            xml_declaration = envelope_file.read(len(xml_declaration))
            if xml_declaration != xml_declaration:
                logger.warning(
                    "Expected XML declaration first line of envelope to be XML encoding declaration, but found: ",
                    xml_declaration,
                )
                envelope_file.seek(pos, os.SEEK_SET)

        schema = etree.XMLSchema(etree.parse(xsd_file))
        xml = etree.parse(envelope_file)

        try:
            schema.assertValid(xml)
        except etree.DocumentInvalid as e:
            logger.error("Envelope did not validate against XSD: %s", str(e.error_log))
            raise
        try:
            validate_taric_xml_record_order(xml)
        except TaricDataAssertionError as e:
            logger.error(e.args[0])
            raise


def validate_taric_xml_record_order(xml):
    """Raise AssertionError if any record codes are not in order."""
    for transaction in xml.findall(".//env:transaction", namespaces=nsmap):
        last_code = "00000"
        for record in transaction.findall(".//oub:record", namespaces=nsmap):
            record_code = record.findtext(".//oub:record.code", namespaces=nsmap)
            subrecord_code = record.findtext(".//oub:subrecord.code", namespaces=nsmap)
            full_code = record_code + subrecord_code
            if full_code < last_code:
                raise TaricDataAssertionError(
                    f"Elements out of order in XML: {last_code}, {full_code}",
                )
            last_code = full_code


class AutoCompleteSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return {
            "value": instance.pk,
            "label": instance.autocomplete_label,
        }
