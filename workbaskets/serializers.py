from rest_framework import serializers

from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="workbaskets:workbasket-detail",
    )
    approver = UserSerializer()
    author = UserSerializer()

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
            "url",
            "approver",
            "created_at",
            "updated_at",
        ]
