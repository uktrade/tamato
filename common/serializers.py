from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from drf_extra_fields.fields import DateTimeRangeField
from rest_framework import serializers


class TARIC3DateTimeRangeField(DateTimeRangeField):
    child = serializers.DateTimeField(
        input_formats=["iso-8601", "%Y-%m-%d",]  # default  # TARIC3 date format
    )


class ValiditySerializerMixin(serializers.ModelSerializer):
    valid_between = TARIC3DateTimeRangeField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "groups"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]
