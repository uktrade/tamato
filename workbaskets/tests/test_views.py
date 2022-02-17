from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse

from common.tests import factories
from common.tests.util import validity_period_post_data
from common.validators import UpdateType
from exporter.tasks import upload_workbaskets
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPOGATES=True)
@patch("exporter.tasks.upload_workbaskets")
def test_submit_workbasket(
    mock_upload,
    unapproved_transaction,
    valid_user,
    client,
):
    workbasket = unapproved_transaction.workbasket

    url = reverse(
        "workbaskets:workbasket-ui-submit",
        kwargs={"pk": workbasket.pk},
    )

    client.force_login(valid_user)
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("index")

    workbasket = WorkBasket.objects.get(pk=workbasket.pk)

    assert workbasket.approver is not None
    assert "workbasket" not in client.session
    mock_upload.delay.assert_called_once_with()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPOGATES=True)
@patch("exporter.tasks.upload_workbaskets")
def test_edit_after_submit(upload, valid_user, client, date_ranges):
    client.force_login(valid_user)

    # submit a workbasket containing a newly created footnote
    workbasket = factories.WorkBasketFactory.create()
    with workbasket.new_transaction():
        footnote = factories.FootnoteFactory.create(
            update_type=UpdateType.CREATE,
        )
    assert footnote.transaction.workbasket == workbasket

    response = client.get(
        reverse(
            "workbaskets:workbasket-ui-submit",
            kwargs={"pk": workbasket.pk},
        ),
    )
    assert response.status_code == 302

    # edit the footnote
    response = client.post(
        footnote.get_url("edit"),
        validity_period_post_data(
            date_ranges.later.lower,
            date_ranges.later.upper,
        ),
    )
    assert response.status_code == 302

    # check that the session workbasket has been replaced by a new one
    session_workbasket = WorkBasket.load_from_session(client.session)
    assert session_workbasket.id != workbasket.id
    assert session_workbasket.status == WorkflowStatus.EDITING

    # check that the footnote edit is in the new session workbasket
    assert session_workbasket.transactions.count() == 1
    tx = session_workbasket.transactions.first()
    assert tx.tracked_models.count() == 1
    new_footnote_version = tx.tracked_models.first()
    assert new_footnote_version.pk != footnote.pk
    assert new_footnote_version.version_group == footnote.version_group


def test_download(
    approved_workbasket,
    client,
    valid_user,
    hmrc_storage,
    s3_resource,
    s3_object_names,
    settings,
):
    client.force_login(valid_user)
    bucket = "hmrc"
    settings.HMRC_STORAGE_BUCKET_NAME = bucket
    s3_resource.create_bucket(Bucket="hmrc")
    with patch(
        "exporter.storages.HMRCStorage.save",
        wraps=MagicMock(side_effect=hmrc_storage.save),
    ):
        upload_workbaskets.apply()
        url = reverse("workbaskets:workbasket-download")

        response = client.get(url)

        # the url signature will always be unique, so we can only compare the first part of the url
        expected_url, _ = s3_resource.meta.client.generate_presigned_url(
            ClientMethod="get_object",
            ExpiresIn=3600,
            Params={
                "Bucket": settings.HMRC_STORAGE_BUCKET_NAME,
                "Key": s3_object_names("hmrc")[0],
            },
        ).split("?", 1)

        assert response.status_code == 302
        assert expected_url in response.url
