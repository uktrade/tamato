from django.contrib import auth
from rest_framework import serializers

from common.serializers import UserSerializer
from workbaskets import models


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    approver = UserSerializer()

    class Meta:
        model = models.ApprovalDecision
        fields = ["approver", "decision", "created_at"]


class WorkBasketItemSerializer(serializers.ModelSerializer):
    approval = ApprovalDecisionSerializer()
    author = UserSerializer()

    class Meta:
        model = models.WorkBasketItem
        fields = [
            "id",
            "content_type",
            "object_id",
            "diff",
            "draft",
            "errors",
            "author",
            "approval",
        ]


class WorkBasketSerializer(serializers.ModelSerializer):
    approval = ApprovalDecisionSerializer()
    author = UserSerializer()
    items = WorkBasketItemSerializer(many=True, read_only=True)

    class Meta:
        model = models.WorkBasket
        fields = ["id", "title", "reason", "author", "approval", "status", "items"]
