from django.urls import path
from rest_framework import routers

from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberCreate,
)
from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberDelete,
)
from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberEdit,
)
from reference_documents.views.preferential_quota_views import (
    PreferentialQuotaBulkCreate,
)
from reference_documents.views.preferential_quota_views import PreferentialQuotaCreate
from reference_documents.views.preferential_quota_views import PreferentialQuotaDelete
from reference_documents.views.preferential_quota_views import PreferentialQuotaEdit
from reference_documents.views.preferential_rate_views import PreferentialRateCreate
from reference_documents.views.preferential_rate_views import PreferentialRateDelete
from reference_documents.views.preferential_rate_views import PreferentialRateEdit
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmCreate, ReferenceDocumentVersionChangeStateToInReviewConfirm,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmDelete,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmUpdate,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionCreate,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionDelete,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionDetails,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionEdit,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmCreate,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmDelete,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmUpdate,
)
from reference_documents.views.reference_document_views import ReferenceDocumentCreate
from reference_documents.views.reference_document_views import ReferenceDocumentDelete
from reference_documents.views.reference_document_views import ReferenceDocumentDetails
from reference_documents.views.reference_document_views import ReferenceDocumentEdit
from reference_documents.views.reference_document_views import ReferenceDocumentList

app_name = "reference_documents"

api_router = routers.DefaultRouter()

detail = "<sid:sid>"
urlpatterns = [
    # Reference document views
    path(
        "reference_documents/",
        ReferenceDocumentList.as_view(),
        name="index",
    ),
    path(
        "reference_documents/create/",
        ReferenceDocumentCreate.as_view(),
        name="create",
    ),
    path(
        "reference_documents/<pk>/",
        ReferenceDocumentDetails.as_view(),
        name="details",
    ),
    path(
        "reference_documents/<pk>/edit/",
        ReferenceDocumentEdit.as_view(),
        name="edit",
    ),
    path(
        f"<pk>/confirm-create/",
        ReferenceDocumentConfirmCreate.as_view(),
        name="confirm-create",
    ),
    path(
        f"reference_documents/<pk>/confirm-update/",
        ReferenceDocumentConfirmUpdate.as_view(),
        name="confirm-update",
    ),
    path(
        f"reference_documents/<pk>/delete/",
        ReferenceDocumentDelete.as_view(),
        name="delete",
    ),
    path(
        f"reference_documents/<deleted_pk>/confirm-delete/",
        ReferenceDocumentConfirmDelete.as_view(),
        name="confirm-delete",
    ),
    # reference document version views
    path(
        "reference_documents_versions/<pk>/",
        ReferenceDocumentVersionDetails.as_view(),
        name="version-details",
    ),
    path(
        "reference_documents_versions/<pk>/create",
        ReferenceDocumentVersionCreate.as_view(),
        name="version-create",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/edit/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-edit",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_in_review/",
        ReferenceDocumentVersionChangeStateToInReviewConfirm.as_view(),
        name="version-status-change-to-in-review",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_in_review/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-status-change-to-in-review",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_published/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-status-change-to-published",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_published/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-status-change-to-published-confirm",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_editable/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-status-change-to-editing",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_editable/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-status-change-to-editing-confirm",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/version-delete/",
        ReferenceDocumentVersionDelete.as_view(),
        name="version-delete",
    ),
    path(
        "reference_document_versions/<pk>/confirm-update/",
        ReferenceDocumentVersionConfirmUpdate.as_view(),
        name="version-confirm-update",
    ),
    path(
        "reference_document_versions/<pk>/confirm-create/",
        ReferenceDocumentVersionConfirmCreate.as_view(),
        name="version-confirm-create",
    ),
    path(
        "reference_document_versions/<deleted_pk>/confirm-delete/",
        ReferenceDocumentVersionConfirmDelete.as_view(),
        name="version-confirm-delete",
    ),
    # Preferential Quotas
    path(
        "preferential_quotas/delete/<pk>/<version_pk>/",
        PreferentialQuotaDelete.as_view(),
        name="preferential_quotas_delete",
    ),
    path(
        "preferential_quotas/edit/<pk>/",
        PreferentialQuotaEdit.as_view(),
        name="preferential_quotas_edit",
    ),
    path(
        "preferential_quota_order_numbers/<version_pk>/create_preferential_quotas/",
        PreferentialQuotaCreate.as_view(),
        name="preferential_quotas_create",
    ),
    path(
        "preferential_quota_order_numbers/<version_pk>/create_preferential_quotas_for_order/<order_pk>/",
        PreferentialQuotaCreate.as_view(),
        name="preferential_quotas_create_for_order",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_preferential_quotas/",
        PreferentialQuotaBulkCreate.as_view(),
        name="preferential_quotas_bulk_create",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_preferential_quotas/<order_pk>/",
        PreferentialQuotaBulkCreate.as_view(),
        name="preferential_quotas_bulk_create_for_order",
    ),
    # Preferential Rates
    path(
        "preferential_rates/delete/<pk>/",
        PreferentialRateDelete.as_view(),
        name="preferential_rates_delete",
    ),
    path(
        "preferential_rates/edit/<pk>/",
        PreferentialRateEdit.as_view(),
        name="preferential_rates_edit",
    ),
    path(
        "reference_document_versions/<version_pk>/create_preferential_rates/",
        PreferentialRateCreate.as_view(),
        name="preferential_rates_create",
    ),
    # Preferential rate Quota order number
    path(
        "preferential_quota_order_numbers/delete/<pk>/<version_pk>/",
        PreferentialQuotaOrderNumberDelete.as_view(),
        name="preferential_quota_order_number_delete",
    ),
    path(
        "preferential_quota_order_numbers/edit/<pk>/",
        PreferentialQuotaOrderNumberEdit.as_view(),
        name="preferential_quota_order_number_edit",
    ),
    path(
        "reference_document_versions/<pk>/create_preferential_quota_order_number/",
        PreferentialQuotaOrderNumberCreate.as_view(),
        name="preferential_quota_order_number_create",
    ),
]
