from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from taric.models import EnvelopeTransaction
from workbaskets import models


class EnvelopeTransactionSerializer(serializers.ModelSerializer):
    tracked_models = serializers.SerializerMethodField()

    def get_tracked_models(self, obj):
        return TrackedModelSerializer(
            obj.tracked_models.annotate_record_codes().order_by(
                "record_code", "subrecord_code"
            ),
            many=True,
            read_only=True,
            context=self.context,
        ).data

    class Meta:
        model = EnvelopeTransaction
        fields = [
            "tracked_models",
            "order",
        ]


class EnvelopeSerializer(serializers.ModelSerializer):
    envelope_id = serializers.SerializerMethodField(read_only=True)
    transactions = EnvelopeTransactionSerializer(read_only=True, many=True)

    def get_envelope_id(self, object: models.Envelope):
        return str(object.pk).zfill(6)

    class Meta:
        model = models.Envelope
        fields = [
            "id",
            "transactions",
            "envelope_id",
        ]
