from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from drf_extra_fields.fields import DateTimeRangeField
from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer


class TARIC3DateTimeRangeField(DateTimeRangeField):
    child = serializers.DateTimeField(
        input_formats=["iso-8601", "%Y-%m-%d",]  # default  # TARIC3 date format
    )


class TrackedModelSerializerMixin(serializers.ModelSerializer):
    taric_template = serializers.SerializerMethodField()

    formats_with_template = {"xml"}

    def get_taric_template(self, object):
        return object.get_taric_template()

    def get_format(self):
        """
        Find the format of the request.

        This first checks the immediate serializer context, if not found it checks the
        request for query params. If that fails it checks the Accept header to see if
        any of the `self.formats_with_template` are within the header.
        """
        if self.context.get("format"):
            return self.context["format"]

        if self.context["request"].query_params.get("format"):
            return self.context["request"].query_params.get("format")

        for data_format in self.formats_with_template:
            if data_format in self.context["request"].accepted_media_type.lower():
                return data_format

    def to_representation(self, *args, **kwargs):
        """
        Removes the taric template field from formats that don't require it.

        By default the only format which keeps the taric_tempalte field is XML.
        """
        data = super().to_representation(*args, **kwargs)
        data_format = self.get_format()

        if data_format not in self.formats_with_template:
            if "taric_template" in data:
                data.pop("taric_template")

        return data


class ValiditySerializerMixin(serializers.ModelSerializer):
    date_format_string = "{:%Y-%m-%d}"
    valid_between = TARIC3DateTimeRangeField()
    end_date = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()

    def get_start_date(self, obj):
        if obj.valid_between and obj.valid_between.lower:
            return self.date_format_string.format(obj.valid_between.lower)

    def get_end_date(self, obj):
        if obj.valid_between and obj.valid_between.upper:
            return self.date_format_string.format(obj.valid_between.upper)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "groups"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class TrackedModelSerializer(PolymorphicSerializer):
    model_serializer_mapping = {}

    @classmethod
    def register_polymorphic_model(cls, serializer):
        cls.model_serializer_mapping[serializer.Meta.model] = serializer
        return serializer
