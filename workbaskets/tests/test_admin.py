import pytest
from unittest import mock 

from common.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

class TestWorkBasketUpload:
    @classmethod
    def setup_class(cls):
        cls.url = "/admin/workbaskets/workbasket/upload/"

    def test_upload_returns_302_for_valid_user(self, valid_user, client):
        valid_user.is_superuser = True
        valid_user.save()
        client.force_login(valid_user)
        response = client.get(self.url)

        assert response.status_code == 302
        assert response.url == "../"

    def test_upload_returns_error_for_non_superuser(self, client):
        non_superuser = UserFactory.create(is_superuser=False)
        client.force_login(non_superuser)
        response = client.get(self.url)

        assert response.status_code == 403

    def test_upload_calls_task(self, valid_user, client):
        with mock.patch(
            "exporter.tasks.upload_workbaskets.delay",
        ) as mock_task:
            valid_user.is_superuser = True
            valid_user.save()
            client.force_login(valid_user)
            client.get(self.url)

            mock_task.assert_called_once_with()
            