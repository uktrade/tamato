from unittest import mock

import pytest

from common.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestWorkBasketUpload:
    @classmethod
    def setup_class(cls):
        cls.url = "/admin/workbaskets/workbasket/upload/"

    def test_upload_returns_302_for_valid_superuser(self, valid_user, client):
        valid_user.is_superuser = True
        valid_user.save()
        client.force_login(valid_user)
        response = client.post(self.url)

        assert response.status_code == 302
        assert response.url == "../"

    def test_upload_returns_403_error_for_non_superuser(self, client):
        non_superuser = UserFactory.create(is_superuser=False)
        client.force_login(non_superuser)
        response = client.post(self.url)

        assert response.status_code == 403

    def test_upload_calls_task(self, valid_user, client):
        with mock.patch(
            "exporter.tasks.upload_workbaskets.delay",
        ) as mock_task:
            valid_user.is_superuser = True
            valid_user.save()
            client.force_login(valid_user)
            client.post(self.url)

            mock_task.assert_called_once_with()
