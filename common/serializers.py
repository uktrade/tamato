from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from drf_extra_fields.fields import DateTimeRangeField
from rest_framework import serializers


class ValiditySerializerMixin(serializers.ModelSerializer):
    valid_between = DateTimeRangeField()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]
