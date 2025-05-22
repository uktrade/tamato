from rest_framework import serializers

from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="workbaskets:workbasket-detail",
        read_only=True,
    )
    author = UserSerializer(read_only=True)
    approver = UserSerializer(read_only=True)

    class Meta:
        model = models.WorkBasket
        fields = [
            "id",
            "url",
            "title",
            "reason",
            "author",
            "approver",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]
