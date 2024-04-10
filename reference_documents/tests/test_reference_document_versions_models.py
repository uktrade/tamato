import pytest
from django_fsm import TransitionNotAllowed

from common.tests.factories import UserFactory
from reference_documents.models import ReferenceDocumentVersionStatus as RDVStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestReferenceDocumentVersion:
    def test_create_with_defaults(self):
        target = factories.ReferenceDocumentVersionFactory()

        assert target.created_at is not None
        assert target.updated_at is not None
        assert target.version is not None
        assert target.published_date is not None
        assert target.entry_into_force_date is not None
        assert target.reference_document is not None
        assert target.status is not None

    def test_preferential_quotas(self):
        target = factories.ReferenceDocumentVersionFactory.create()
        # add a pref quota
        factories.PreferentialQuotaFactory.create(
            preferential_quota_order_number__reference_document_version=target,
        )

        assert len(target.preferential_quotas()) == 1

    # FSM tests
    @pytest.mark.parametrize(
        "initial_state, method, allowed, expected_status",
        [
            # valid
            (RDVStatus.EDITING, 'in_review', True, RDVStatus.IN_REVIEW),
            (RDVStatus.IN_REVIEW, 'published', True, RDVStatus.PUBLISHED),
            (RDVStatus.PUBLISHED, 'editing_from_published', True, RDVStatus.EDITING),
            (RDVStatus.IN_REVIEW, 'editing_from_in_review', True, RDVStatus.EDITING),
            # invalid
            (RDVStatus.IN_REVIEW, 'in_review', False, RDVStatus.IN_REVIEW),
            (RDVStatus.PUBLISHED, 'in_review', False, RDVStatus.PUBLISHED),
            (RDVStatus.PUBLISHED, 'published', False, RDVStatus.PUBLISHED),
            (RDVStatus.EDITING, 'published', False, RDVStatus.EDITING),
            (RDVStatus.EDITING, 'editing_from_published', False, RDVStatus.EDITING),
            (RDVStatus.IN_REVIEW, 'editing_from_published', False, RDVStatus.IN_REVIEW),
            (RDVStatus.EDITING, 'editing_from_in_review', False, RDVStatus.EDITING),
            (RDVStatus.PUBLISHED, 'editing_from_in_review', False, RDVStatus.PUBLISHED),
        ],
    )
    def test_transitions(self, initial_state, method, allowed, expected_status):
        target = factories.ReferenceDocumentVersionFactory.create(status=initial_state)

        if not allowed:
            with pytest.raises(TransitionNotAllowed):
                getattr(target, method)()
        else:
            getattr(target, method)()
            assert target.status == expected_status
