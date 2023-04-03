import pytest

from importer.handlers import ImportIssueReportItem
from importer.models import ImportErrorStatus

pytestmark = pytest.mark.django_db


def test_import_issue_report_item_init():
    target = ImportIssueReportItem(
        "xyz.sss.yyy",
        {},
        "aaa.bbb.ccc",
        {},
        "xxx",
        "some fake import error",
    )

    assert target.description == "some fake import error"
    assert target.object_type == "xyz.sss.yyy"
    assert target.object_identity_keys == {}
    assert target.related_object_type == "aaa.bbb.ccc"
    assert target.related_object_identity_keys == {}
    # check default error status
    assert target.import_error_status == ImportErrorStatus.ERROR


def test_import_issue_report_init_with_different_status():
    target = ImportIssueReportItem(
        "xyz.sss.yyy",
        {},
        "aaa.bbb.ccc",
        {},
        "xxx",
        "some fake import error",
        ImportErrorStatus.WARNING,
    )

    assert target.import_error_status == ImportErrorStatus.WARNING


def test_import_issue_report_init_with_int_status():
    target = ImportIssueReportItem(
        "xyz.sss.yyy",
        {},
        "aaa.bbb.ccc",
        {},
        "xxx",
        "some fake import error",
        1,
    )

    assert target.import_error_status == 1


def test_import_issue_report_init_with_string_status():
    with pytest.raises(ValueError) as e:
        ImportIssueReportItem(
            "xyz.sss.yyy",
            {},
            "aaa.bbb.ccc",
            {},
            "xxx",
            "some fake import error",
            "WARNING",
        )

    assert (
        str(e.value)
        == "The value WARNING for import_error_status is not an option from ImportErrorStatus.values"
    )


def test_import_issue_report_item_to_warning():
    target = ImportIssueReportItem(
        "xyz.sss.yyy",
        {},
        "aaa.bbb.ccc",
        {},
        "xxx",
        "some fake import error",
    )
    target.to_warning()
    assert target.import_error_status == ImportErrorStatus.WARNING
