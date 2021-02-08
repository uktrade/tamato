from rest_framework import permissions
from rest_framework import viewsets

from certificates.filters import CertificateFilter
from certificates.models import Certificate
from certificates.models import CertificateType
from certificates.serializers import CertificateSerializer
from certificates.serializers import CertificateTypeSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailView


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


class CertificatesList(TamatoListView):
    """
    UI endpoint for viewing and filtering Certificates
    """

    queryset = (
        Certificate.objects.current()
        .select_related("certificate_type")
        .prefetch_related("descriptions")
    )
    template_name = "certificates/list.jinja"
    filterset_class = CertificateFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class CertificateDetail(TrackedModelDetailView):
    model = Certificate
    template_name = "certificates/detail.jinja"
    queryset = (
        Certificate.objects.current()
        .select_related("certificate_type")
        .prefetch_related("descriptions")
    )
