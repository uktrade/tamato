from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from drf_extra_fields.fields import DateTimeRangeField
from rest_framework import serializers


class ValiditySerializerMixin(serializers.ModelSerializer):
    valid_between = DateTimeRangeField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "groups"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]
