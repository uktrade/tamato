import django_fsm
import pytest

from reference_documents.models import AlignmentReport
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.models import AlignmentReportStatus
from reference_documents.tests import factories
from reference_documents.tests.factories import AlignmentReportCheckFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestAlignmentReport:
    def test_init(self):

        # ref_doc_ver = factories.ReferenceDocumentVersionFactory.create()
        target = AlignmentReport()

        assert target.status is AlignmentReportStatus.PENDING
        assert target.reference_document_version_id is None

    def test_state_transition_from_pending(self):
        target = AlignmentReport()
        assert target.status is AlignmentReportStatus.PENDING

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.complete()
            assert (
                "Can't switch from state 'PENDING' using method 'complete'" in e.value
            )

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.errored()
            assert "Can't switch from state 'PENDING' using method 'errored'" in e.value

        # allowed
        target.in_processing()
        assert target.status is AlignmentReportStatus.PROCESSING

    def test_state_transition_from_errored(self):
        target = AlignmentReport(status=AlignmentReportStatus.ERRORED)
        assert target.status is AlignmentReportStatus.ERRORED

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.in_processing()
            assert (
                "Can't switch from state 'ERRORED' using method 'in_processing'"
                in e.value
            )

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.complete()
            assert (
                "Can't switch from state 'ERRORED' using method 'complete'" in e.value
            )

    def test_state_transition_from_complete(self):
        target = AlignmentReport(status=AlignmentReportStatus.COMPLETE)
        assert target.status is AlignmentReportStatus.COMPLETE

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.in_processing()
            assert (
                "Can't switch from state 'COMPLETE' using method 'in_processing'"
                in e.value
            )

        # not allowed
        with pytest.raises(django_fsm.TransitionNotAllowed) as e:
            target.errored()
            assert (
                "Can't switch from state 'COMPLETE' using method 'errored'" in e.value
            )

    def test_state_transition_from_processing(self):
        # allowed
        target = AlignmentReport(status=AlignmentReportStatus.PROCESSING)
        target.complete()
        assert target.status is AlignmentReportStatus.COMPLETE

        # allowed
        target = AlignmentReport(status=AlignmentReportStatus.PROCESSING)
        target.errored()
        assert target.status is AlignmentReportStatus.ERRORED

    def test_unique_check_names_default(self):
        target = factories.AlignmentReportFactory()
        assert list(target.unique_check_names()) == []

    def test_unique_check_names_populated(self):
        target = factories.AlignmentReportFactory()
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.PASS,
        )
        AlignmentReportCheckFactory(check_name="test2", alignment_report=target)
        AlignmentReportCheckFactory(check_name="test3", alignment_report=target)
        assert list(target.unique_check_names()) == ["test1", "test2", "test3"]

    def test_check_stats_default(self):
        target = factories.AlignmentReportFactory()
        assert target.check_stats() == {}

    def test_check_stats_populated(self):
        target = factories.AlignmentReportFactory()
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.PASS,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.FAIL,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.WARNING,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.SKIPPED,
        )
        AlignmentReportCheckFactory(check_name="test2", alignment_report=target)
        AlignmentReportCheckFactory(check_name="test3", alignment_report=target)
        stats = target.check_stats()
        assert stats["test1"]["total"] == 4
        assert stats["test1"]["failed"] == 1
        assert stats["test1"]["passed"] == 1
        assert stats["test1"]["warning"] == 1
        assert stats["test1"]["skipped"] == 1
        assert stats["test2"]["total"] == 1
        assert stats["test3"]["total"] == 1

    def test_error_count(self):
        target = factories.AlignmentReportFactory()
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.PASS,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.FAIL,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.WARNING,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.SKIPPED,
        )
        AlignmentReportCheckFactory(check_name="test2", alignment_report=target)
        AlignmentReportCheckFactory(check_name="test3", alignment_report=target)
        assert target.error_count() == 1

    def test_warning_count(self):
        target = factories.AlignmentReportFactory()
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.PASS,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.FAIL,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.WARNING,
        )
        AlignmentReportCheckFactory(
            check_name="test1",
            alignment_report=target,
            status=AlignmentReportCheckStatus.SKIPPED,
        )
        AlignmentReportCheckFactory(check_name="test2", alignment_report=target)
        AlignmentReportCheckFactory(check_name="test3", alignment_report=target)
        assert target.warning_count() == 1
