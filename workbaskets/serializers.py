from django.contrib import auth
from rest_framework import serializers

from common.serializers import UserSerializer
from workbaskets import models


class WorkBasketSerializer(serializers.ModelSerializer):
    approver = UserSerializer()
    author = UserSerializer()

    class Meta:
        model = models.WorkBasket
        fields = ["id", "title", "reason", "author", "approver", "status"]
