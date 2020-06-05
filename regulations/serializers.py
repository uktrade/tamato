from rest_framework import serializers

from common.serializers import ValiditySerializerMixin
from regulations import models
from regulations import validators


class GroupSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.Group
        fields = [
            "group_id",
            "description",
        ]


class NestedRegulationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Regulation
        fields = ["url", "regulation_id"]


class AmendmentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Amendment
        fields = ["regulation", "amended"]


class NestedAmendmentSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Amendment
        fields = ["regulation"]


class ReplacementSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Replacement
        fields = ["regulation", "replaced"]


class NestedReplacementSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Replacement
        fields = ["regulation"]


class ExtensionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Extension
        fields = ["regulation", "extended", "effective_end_date"]


class NestedExtensionSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Extension
        fields = ["regulation", "effective_end_date"]


class SuspensionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Suspension
        fields = ["regulation", "suspended", "effective_end_date"]


class NestedSuspensionSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Suspension
        fields = ["regulation", "effective_end_date"]


class TerminationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Termination
        fields = ["regulation", "terminated", "effective_date"]


class NestedTerminationSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Termination
        fields = ["regulation", "effective_date"]


class RoleTypeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Convert integer to RoleType"""
        return {
            "value": instance,
            "label": dict(models.RoleType.choices)[instance],
        }


class RegulationSerializer(
    serializers.HyperlinkedModelSerializer, ValiditySerializerMixin
):
    regulation_group = GroupSerializer()
    role_type = RoleTypeSerializer()
    amends = NestedRegulationSerializer(many=True)
    amendments = NestedAmendmentSerializer(many=True)
    extends = NestedRegulationSerializer(many=True)
    extensions = NestedExtensionSerializer(many=True)
    suspends = NestedRegulationSerializer(many=True)
    suspensions = NestedSuspensionSerializer(many=True)
    terminates = NestedRegulationSerializer(many=True)
    terminations = NestedTerminationSerializer(many=True)
    replaces = NestedRegulationSerializer(many=True)
    replacements = NestedReplacementSerializer(many=True)

    class Meta:
        model = models.Regulation
        fields = "__all__"
