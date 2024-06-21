import pytest
from django_fsm import TransitionNotAllowed

from common.tests.factories import UserFactory
from reference_documents.models import ReferenceDocumentVersionStatus as RDVStatus, ReferenceDocumentVersionStatus
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
        factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=target,
        )

        assert len(target.ref_quota_definitions()) == 1

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

    def test_state_not_editable_prevents_save(self):
        target = factories.ReferenceDocumentVersionFactory()
        target_version = target.version

        assert target.status == ReferenceDocumentVersionStatus.EDITING
        assert target.editable()

        target.in_review()
        target.save(force_save=True)

        target.version = '33.33'
        target.save()

        target.refresh_from_db()

        assert target.status == ReferenceDocumentVersionStatus.IN_REVIEW
        assert float(target.version) == float(target_version)
        assert not target.editable()

        target.published()
        target.save(force_save=True)

        target.version = '33.33'
        target.save()

        target.refresh_from_db()

        assert target.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not target.editable()
        assert float(target.version) == float(target_version)


