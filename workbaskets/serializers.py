from rest_framework import serializers

from common.serializers import TransactionSerializer
from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.ModelSerializer):
    approver_id = serializers.IntegerField(required=False, allow_null=True)
    approver = UserSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    envelope_id = serializers.SerializerMethodField(read_only=True)
    transactions = TransactionSerializer(read_only=True, many=True)

    def get_envelope_id(self, object: models.WorkBasket):
        return str(object.pk).zfill(6)

    class Meta:
        model = models.WorkBasket
        fields = [
            "id",
            "title",
            "reason",
            "author",
            "approver_id",
            "approver",
            "status",
            "transactions",
            "envelope_id",
            "created_at",
            "updated_at",
        ]
