from unittest.mock import patch

import pytest

from common.auth_backend import CustomAuthbrokerBackend


@pytest.fixture
def staff_sso_profile():
    return {
        "user_id": "6fa3b542-9a6f-4fc3-a248-168596572999",
        "email_user_id": "john.smith-6fa3b542@id.trade.gov.uk",  # /PS-IGNORE
        "email": "john.smith@someplace.gov.uk",  # /PS-IGNORE
        "contact_email": "john.smith@someemail.com",  # /PS-IGNORE
        "related_emails": [
            "jsmith@someotherplace.com",  # /PS-IGNORE
            "me@johnsmith.com",  # /PS-IGNORE
        ],
        "first_name": "John",
        "last_name": "Smith",
    }


def test_user_create_mapping(staff_sso_profile):
    """Test that the user_create_mapping method correctly returns user data to
    be used when creating a user."""
    custom_authbroker_backend = CustomAuthbrokerBackend()
    expected_user_mapping = {
        "is_active": True,
        "email": "john.smith@someplace.gov.uk",  # /PS-IGNORE
        "first_name": "John",
        "last_name": "Smith",
        "sso_uuid": "6fa3b542-9a6f-4fc3-a248-168596572999",
    }
    user_mapping = custom_authbroker_backend.user_create_mapping(staff_sso_profile)
    assert user_mapping == expected_user_mapping


@patch("authbroker_client.backends.AuthbrokerBackend.get_or_create_user")
def test_get_or_create_user(
    mock_get_or_create_user,
    valid_user,
    staff_sso_profile,
):
    """Test that the overridden get_or_create_user method correctly calls super
    and then sets the valid_user's sso_uuid if they don't have one."""
    assert not valid_user.sso_uuid
    mock_get_or_create_user.return_value = valid_user

    custom_authbroker_backend = CustomAuthbrokerBackend()
    custom_authbroker_backend.get_or_create_user(staff_sso_profile)
    assert valid_user.sso_uuid == "6fa3b542-9a6f-4fc3-a248-168596572999"
