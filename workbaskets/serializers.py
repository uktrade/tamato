from django.contrib import auth
from rest_framework import serializers

from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.ModelSerializer):
    approver_id = serializers.IntegerField(required=False, allow_null=True)
    approver = UserSerializer(read_only=True)
    author = UserSerializer(read_only=True)
    transaction_id = serializers.IntegerField(read_only=True)

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
            "transaction_id",
            "created_at",
            "updated_at",
        ]
