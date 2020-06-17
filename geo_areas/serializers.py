from common.serializers import ValiditySerializerMixin
from geo_areas import models


class GeographicalMembershipSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.GeographicalMembership
        fields = "__all__"


class GeographicalAreaDescriptionSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.GeographicalAreaDescription
        fields = ["id", "description", "valid_between"]


class GeographicalAreaSerializer(ValiditySerializerMixin):
    descriptions = GeographicalAreaDescriptionSerializer(
        many=True, source="geographicalareadescription_set"
    )

    class Meta:
        model = models.GeographicalArea
        fields = ["id", "sid", "area_code", "descriptions", "valid_between"]
