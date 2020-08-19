from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.ModelSerializer):
    approver_id = serializers.IntegerField(required=False, allow_null=True)
    approver = UserSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    transaction_id = serializers.SerializerMethodField(read_only=True)

    tracked_models = TrackedModelSerializer(many=True)

    def get_transaction_id(self, object: models.WorkBasket):
        if hasattr(object, "transaction"):
            return object.transaction.id
        return None

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
            "tracked_models",
            "transaction_id",
            "created_at",
            "updated_at",
        ]
