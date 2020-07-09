from rest_framework import permissions
from rest_framework import viewsets

from certificates.models import Certificate
from certificates.models import CertificateType
from certificates.serializers import CertificateSerializer
from certificates.serializers import CertificateTypeSerializer


class CertificatesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows certificates to be viewed.
    """

    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "code"]


class CertificateTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows certificate types to be viewed.
    """

    queryset = CertificateType.objects.all()
    serializer_class = CertificateTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
