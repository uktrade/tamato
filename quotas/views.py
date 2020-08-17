from rest_framework import permissions
from rest_framework import viewsets

from quotas import models
from quotas import serializers


class QuotaOrderNumberViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumber.objects.approved()
    serializer_class = serializers.QuotaOrderNumberSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number", "mechanism", "category"]


class QuotaOrderNumberOriginViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOrigin.objects.approved()
    serializer_class = serializers.QuotaOrderNumberOriginSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberOriginExclusionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOriginExclusion.objects.approved()
    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaDefinitionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaDefinition.objects.approved()
    serializer_class = serializers.QuotaDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number__order_number", "description"]


class QuotaAssociationViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaAssociation.objects.approved()
    serializer_class = serializers.QuotaAssociationSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaSuspensionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaSuspension.objects.approved()
    serializer_class = serializers.QuotaSuspensionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaBlockingViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaBlocking.objects.approved()
    serializer_class = serializers.QuotaBlockingSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaEventViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaEvent.objects.approved()
    serializer_class = serializers.QuotaEventSerializer
    permission_classes = [permissions.IsAuthenticated]
